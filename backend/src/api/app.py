from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import shutil
import os
import json
import re


from src.loaders.text_loader import load_text_file
from src.loaders.csv_loader import load_csv_file


from src.chains.retrieval_qa import prepare_vectorstore
from src.chains.enhanced_retrieval_qa import EnhancedRAG, prepare_enhanced_rag


from src.evaluation.rag_evaluator import RAGEvaluator, evaluate_rag_performance


from src.analysis.root_cause_analyzer import RootCauseAnalyzer

# Import other components
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from fastapi.middleware.cors import CORSMiddleware
from src.auth.auth_models import get_current_active_user, User
from src.auth.auth_routes import router as auth_router
from src.analysis.log_analyzer import LogAnalyzer
from src.api.root_cause_endpoint import router as root_cause_router

# Import file database functions
from src.auth.file_db import save_file_info, get_file_by_id, get_files_by_user, delete_file

# Initialize FastAPI app
app = FastAPI()

# Allow requests from 'http://localhost:5173'
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(root_cause_router)

# Directory setup
UPLOAD_DIRECTORY = "./uploads"
VISUALIZATIONS_DIR = "./visualizations"
EVALUATION_DIR = "./evaluation_results"

for directory in [UPLOAD_DIRECTORY, VISUALIZATIONS_DIR, EVALUATION_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Mount the static directories
app.mount("/visualizations", StaticFiles(directory=VISUALIZATIONS_DIR), name="visualizations")
app.mount("/evaluation", StaticFiles(directory=EVALUATION_DIR), name="evaluation")

# Cache for RAG components - keyed by file_id
# This avoids having to rebuild the components for every request
rag_cache = {}

# Input models for various requests
class QueryRequest(BaseModel):
    query: str
    file_id: int
    use_enhanced: bool = True  # Default to enhanced RAG

class AnalysisRequest(BaseModel):
    file_id: int
    analysis_type: str
    options: dict = {}

class EvaluationRequest(BaseModel):
    file_id: int
    num_samples: int = 10
    generate_visualization: bool = True

class FilteredQueryRequest(BaseModel):
    query: str
    file_id: int
    filters: dict = {}  # Metadata filters

# Helper function to get or initialize RAG components for a file
def get_rag_components(file_id: int, user_id: int):
    """
    Get or initialize RAG components for a specific file.
    Returns a tuple of (vectorstore, qa_chain, enhanced_rag, log_analyzer, documents)
    """
    global rag_cache
    
    # Check if components are already in cache
    if file_id in rag_cache:
        return rag_cache[file_id]
    
    # Get file information from database
    file_info = get_file_by_id(file_id)
    if not file_info or file_info['user_id'] != user_id:
        raise HTTPException(status_code=404, detail="File not found or access denied.")
    
    file_path = file_info['file_path']
    file_type = file_info['file_type']
    
    # Load documents based on file type
    documents = []
    if file_type in ["txt", "log", "md"]:
        documents = load_text_file(file_path)
    elif file_type == "csv":
        documents = load_csv_file(file_path)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_type}")
    
    # Initialize standard RAG
    vectorstore = prepare_vectorstore(documents)
    
    # Define the standard QA chain
    template = """You are a Level 1 SOC analyst analyzing server logs.
    Use ONLY the context below to answer the question as precisely and concisely as possible.
    If the information requested is not present in the context, respond with "No relevant information found in the logs."
    DO NOT make up or infer information that is not explicitly in the logs.

    {context}
    Question: {question}
    Answer:"""

    QA_CHAIN_PROMPT = PromptTemplate(
        input_variables=["context", "question"],
        template=template,
    )

    # Replace OllamaLLM with ChatGroq
    llm = ChatGroq(model="llama3-8b-8192", groq_api_key="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", temperature=0.1,system="You are a Level 1 SOC analyst analyzing server logs. ONLY report information that is explicitly found in the logs provided. If you cannot find the requested information in the provided context, clearly state 'No relevant information found in the logs.' NEVER generate fictional log entries or make up data, as this could lead to incorrect security analyses.")
    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=vectorstore.as_retriever(),
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
    )

    # Initialize enhanced RAG
    enhanced_rag = prepare_enhanced_rag(documents)
    
    # Initialize the log analyzer
    log_analyzer = LogAnalyzer(documents)
    log_analyzer.process_documents()
    
    # Initialize RAG evaluator
    rag_evaluator = RAGEvaluator(enhanced_rag)
    
    # Store components in cache
    rag_components = {
        "vectorstore": vectorstore,
        "qa_chain": qa_chain,
        "enhanced_rag": enhanced_rag,
        "log_analyzer": log_analyzer,
        "rag_evaluator": rag_evaluator,
        "documents": documents
    }
    
    rag_cache[file_id] = rag_components
    return rag_components

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint to upload a custom file for log analysis.
    Initializes both standard and enhanced RAG systems.
    """
    # Save the uploaded file
    try:
        # Create user-specific directory if it doesn't exist
        user_dir = os.path.join(UPLOAD_DIRECTORY, str(current_user.id))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        
        # Save the file with timestamp to avoid name conflicts
        timestamp = int(datetime.now().timestamp())
        file_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join(user_dir, file_name)
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Get file extension
        file_ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
        
        # Save file info to database
        file_id = save_file_info(
            filename=file.filename,
            file_path=file_path,
            file_type=file_ext,
            user_id=current_user.id,
            file_size=file_size
        )
        
        # Initialize RAG components
        rag_components = get_rag_components(file_id, current_user.id)
        
        # Sample raw data for response
        raw_data_sample = rag_components["documents"][0].page_content[:500] if rag_components["documents"] else "No content"
        
        return JSONResponse(content={
            "message": f"File '{file.filename}' successfully processed.",
            "file_id": file_id,
            "standard_rag": "Initialized",
            "enhanced_rag": "Initialized",
            "log_analyzer": "Initialized",
            "rag_evaluator": "Initialized",
            "sample": raw_data_sample[:200] + "..." if len(raw_data_sample) > 200 else raw_data_sample
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/query")
async def query_logs(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint to query the uploaded file using either standard or enhanced RAG.
    """
    try:
        # Get RAG components for this file
        components = get_rag_components(request.file_id, current_user.id)
        qa_chain = components["qa_chain"]
        enhanced_rag = components["enhanced_rag"]
        
        query = request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        if request.use_enhanced and enhanced_rag is not None:
            # Use enhanced RAG
            result = enhanced_rag.query(query)
            response_text = result.get("response", "No result found.")
            source_docs = result.get("source_documents", [])
            if not source_docs:
                response_text = "No relevant information found in the logs for this query."
            
            # Format source documents for display
            formatted_sources = []
            for doc in source_docs:
                formatted_sources.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"]
                })
            
            return {
                "query": query,
                "response": response_text,
                "sources": formatted_sources,
                "rag_type": "enhanced",
                "file_id": request.file_id
            }
        else:
            # Use standard RAG
            result = qa_chain.invoke({"query": query})
            response_text = result.get("result", "No result found.")
            return {
                "query": query,
                "response": response_text,
                "rag_type": "standard",
                "file_id": request.file_id
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/filtered-query")
async def filtered_query(
    request: FilteredQueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint for querying with metadata filters (enhanced RAG only).
    """
    try:
        # Get RAG components for this file
        components = get_rag_components(request.file_id, current_user.id)
        enhanced_rag = components["enhanced_rag"]
        
        query = request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty.")
            
        # Apply filters and query the enhanced RAG system
        result = enhanced_rag.query(query, filter_metadata=request.filters)
        response_text = result.get("response", "No result found.")
        
        return {
            "query": query,
            "response": response_text,
            "filters": request.filters,
            "sources": result.get("source_documents", []),
            "file_id": request.file_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing filtered query: {str(e)}")

@app.post("/evaluate-rag")
async def evaluate_rag(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate and run evaluation for the RAG system.
    """
    try:
        # Get RAG components for this file
        components = get_rag_components(request.file_id, current_user.id)
        enhanced_rag = components["enhanced_rag"]
        rag_evaluator = components["rag_evaluator"]
        documents = components["documents"]
        
        # Generate evaluation dataset if needed
        dataset = rag_evaluator.create_evaluation_dataset(
            documents, 
            num_samples=request.num_samples,
            save_path=f"{EVALUATION_DIR}/test_dataset_{int(datetime.now().timestamp())}.json"
        )
        
        # Run evaluation
        evaluation_results = evaluate_rag_performance(
            enhanced_rag, 
            test_data=dataset.get("test_queries", []),
            ground_truth=dataset.get("ground_truth", {}),
            generate_viz=request.generate_visualization
        )
        
        # Return results with visualization paths
        return {
            "results": evaluation_results["results"],
            "visualization_paths": [
                f"/evaluation/{os.path.basename(path)}" 
                for path in evaluation_results.get("visualizations", {}).values()
            ],
            "file_id": request.file_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating RAG system: {str(e)}")

@app.get("/initial-analysis/{file_id}")
async def get_initial_analysis(
    file_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Extract basic structured information from logs without complex analysis.
    Returns structured log entries with timestamps, IP addresses, and messages.
    """
    try:
        # Get file information from database
        file_info = get_file_by_id(file_id)
        if not file_info or file_info['user_id'] != current_user.id:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        
        file_path = file_info['file_path']
        
        # Read the first few bytes to check if this looks like a CSV file
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
            is_csv = ',' in first_line and any(field in first_line.lower() for field in ['date', 'time', 'level', 'component'])
        
        # Process file based on detected format
        if is_csv:
            # CSV handling
            import csv
            structured_logs = []
            
            with open(file_path, 'r') as f:
                csv_reader = csv.DictReader(f)
                for row in csv_reader:
                    # Extract fields based on CSV headers
                    try:
                        timestamp = ""
                        if 'Date' in row and 'Time' in row:
                            timestamp = f"{row['Date']} {row['Time']}"
                        
                        severity = "INFO"
                        if 'Level' in row:
                            severity = row['Level']
                        
                        component = ""
                        if 'Component' in row:
                            component = row['Component']
                        
                        message = ""
                        if 'Content' in row:
                            message = row['Content']
                        
                        # Extract IP if present in the message
                        ip_address = "N/A"
                        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
                        ip_match = re.search(ip_pattern, message)
                        if ip_match:
                            ip_address = ip_match.group(0)
                        
                        # Create structured log entry
                        log_entry = {
                            "timestamp": timestamp,
                            "ip_address": ip_address,
                            "severity": severity,
                            "component": component,
                            "message": message,
                            "event_id": row.get('EventId', 'N/A'),
                            "line_id": row.get('LineId', 'N/A')
                        }
                        
                        structured_logs.append(log_entry)
                    except Exception as e:
                        # If there's an error processing a row, include it with an error note
                        structured_logs.append({
                            "timestamp": "N/A",
                            "ip_address": "N/A",
                            "severity": "ERROR",
                            "message": f"Error parsing row: {str(e)}",
                            "content": str(row)
                        })
            
        else:
            # Regular text log handling (existing code)
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Split the content into individual log lines
            log_lines = content.strip().split('\n')
            
            # Process each log line (existing code)
            structured_logs = []
            for line in log_lines:
                if not line.strip():
                    continue  # Skip empty lines
                    
                # Extract timestamp
                timestamp = "N/A"
                timestamp_patterns = [
                    r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Z+-]\d{2}:?\d{2})?',  # ISO format
                    r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'  # Syslog format
                ]
                
                for pattern in timestamp_patterns:
                    match = re.search(pattern, line)
                    if match:
                        timestamp = match.group(0)
                        break
                
                # Extract IP address
                ip_address = "N/A"
                ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
                ip_match = re.search(ip_pattern, line)
                if ip_match:
                    ip_address = ip_match.group(0)
                
                # Extract severity level if present
                severity = "INFO"  # Default
                severity_patterns = {
                    "ERROR": r'\bERROR\b|\bFAIL\b|\bCRITICAL\b|\bFATAL\b',
                    "WARNING": r'\bWARN\b|\bWARNING\b|\bALERT\b',
                    "INFO": r'\bINFO\b|\bNOTICE\b',
                    "DEBUG": r'\bDEBUG\b|\bTRACE\b'
                }
                
                for level, pattern in severity_patterns.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        severity = level
                        break
                
                # Extract message
                message = line
                if timestamp != "N/A":
                    parts = line.split(']', 1)
                    if len(parts) > 1:
                        message = parts[1].strip()
                    else:
                        message = line
                
                # Create structured log entry
                log_entry = {
                    "timestamp": timestamp,
                    "ip_address": ip_address,
                    "severity": severity,
                    "message": message,
                    "content": line
                }
                
                structured_logs.append(log_entry)
        
        # Basic statistics
        total_entries = len(structured_logs)
        unique_ips = len(set([log["ip_address"] for log in structured_logs if log["ip_address"] != "N/A"]))
        
        # Include the structured logs in the response
        response = {
            "log_entries": structured_logs,
            "file_id": file_id,
            "total_entries": total_entries,
            "unique_ips": unique_ips,
            "file_format": "csv" if is_csv else "text"
        }
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error in initial analysis: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error extracting log data: {str(e)}")
    
@app.post("/analyze")
async def analyze_logs(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint to perform advanced analysis on the uploaded logs.
    """
    try:
        # Get RAG components for this file
        components = get_rag_components(request.file_id, current_user.id)
        log_analyzer = components["log_analyzer"]
        
        # Perform the requested analysis
        if request.analysis_type == "summary":
            result = log_analyzer.get_log_summary()
            result["file_id"] = request.file_id
            return result
            
        elif request.analysis_type == "anomalies":
            result = log_analyzer.detect_anomalies()
            result["file_id"] = request.file_id
            return result
            
        elif request.analysis_type == "security_events":
            result = log_analyzer.analyze_security_events()
            result["file_id"] = request.file_id
            return result
            
        elif request.analysis_type == "report":
            result = log_analyzer.generate_report()
            result["file_id"] = request.file_id
            return result
            
        elif request.analysis_type == "visualization":
            viz_type = request.options.get("visualization_type", "severity")
            title = request.options.get("title")
            output_path = os.path.join(VISUALIZATIONS_DIR, f"{viz_type}_{int(datetime.now().timestamp())}.png")
            
            # Generate the visualization
            viz_path = log_analyzer.create_visualization(viz_type, title, output_path)
            
            if viz_path:
                # Return relative path that can be used with the /visualizations endpoint
                return {
                    "visualization_path": os.path.basename(viz_path),
                    "file_id": request.file_id
                }
            else:
                raise HTTPException(status_code=500, detail=f"Failed to generate {viz_type} visualization.")
                
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {request.analysis_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing analysis: {str(e)}")

@app.get("/files")
async def get_user_files(current_user: User = Depends(get_current_active_user)):
    """
    Get all files uploaded by the current user.
    """
    try:
        files = get_files_by_user(current_user.id)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving files: {str(e)}")

@app.delete("/files/{file_id}")
async def delete_user_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file uploaded by the current user.
    """
    try:
        # Remove from cache if present
        global rag_cache
        if file_id in rag_cache:
            del rag_cache[file_id]
            
        # Delete from database and filesystem
        success = delete_file(file_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
            
        return {"message": "File deleted successfully", "file_id": file_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@app.get("/")
def read_root():
    """
    Root endpoint for API health check.
    """
    return {
        "message": "SOC Level 1 log analysis API is running. Upload a file to get started.",
        "version": "2.0",
        "features": [
            "User-based file management",
            "Standard RAG",
            "Enhanced RAG with contextual compression",
            "Log analysis",
            "RAG performance evaluation",
            "Root cause analysis"
        ]
    }