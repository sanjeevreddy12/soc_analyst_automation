from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import BaseModel
from datetime import datetime, timedelta
import shutil
from src.loaders.text_loader import load_text_file
from src.loaders.csv_loader import load_csv_file
from src.chains.retrieval_qa import prepare_vectorstore
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_ollama.llms import OllamaLLM
from fastapi.middleware.cors import CORSMiddleware
from src.auth.auth_models import get_current_active_user, User
from src.auth.auth_routes import router as auth_router
from src.analysis.log_analyzer import LogAnalyzer
import os
import json
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

# Persistent global state
vectorstore = None
qa_chain = None
current_file_name = None
raw_data_sample = None

UPLOAD_DIRECTORY = "./uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


# Input model for query requests
class QueryRequest(BaseModel):
    query: str


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to upload a custom file for log analysis.
    """
    global vectorstore, qa_chain

    # Save the uploaded file
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    # Determine file type and load data
    ext = os.path.splitext(file.filename)[1].lower()
    try:
        if ext in [".txt", ".log", ".md"]:
            data = load_text_file(file_path)
        elif ext == ".csv":
            data = load_csv_file(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

        # Prepare the vectorstore
        vectorstore = prepare_vectorstore(data)

        # Define the QA chain
        template = """You are a Level 1 SOC analyst analyzing server logs.
        Use the context below to answer the question as precisely and concisely as possible.
        {context}
        Question: {question}
        Answer:"""

        QA_CHAIN_PROMPT = PromptTemplate(
            input_variables=["context", "question"],
            template=template,
        )

        llm = OllamaLLM(model="llama3.1")
        qa_chain = RetrievalQA.from_chain_type(
            llm,
            retriever=vectorstore.as_retriever(),
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
        )

        return JSONResponse(content={"message": f"File '{file.filename}' successfully processed and vectorstore initialized."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")



@app.post("/query")
def query_logs(request: QueryRequest):
    """
    Endpoint to query the uploaded file using the RetrievalQA chain.
    """
    global qa_chain

    if qa_chain is None:
        raise HTTPException(status_code=500, detail="No file has been uploaded or processed.")

    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        result = qa_chain.invoke({"query": query})
        response_text = result.get("result", "No result found.")
        return {"query": query, "response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")

VISUALIZATIONS_DIR = "./visualizations"
if not os.path.exists(VISUALIZATIONS_DIR):
    os.makedirs(VISUALIZATIONS_DIR)

# Mount the static directory to serve visualizations
app.mount("/visualizations", StaticFiles(directory=VISUALIZATIONS_DIR), name="visualizations")

# Add to your global state variables
log_analyzer = None

# Extended request model
class AnalysisRequest(BaseModel):
    analysis_type: str
    options: dict = {}


def process_documents(self):
    """Process the document objects into structured log data."""
    self.parsed_logs = []
    
    print(f"Processing {len(self.documents)} documents")
    
    for doc in self.documents:
        content = doc.page_content
        metadata = doc.metadata
        
        print(f"Processing log entry: {content[:100]}...")
        
        # Try to parse the log entry
        try:
            log_entry = self._parse_log_entry(content)
            log_entry['source'] = metadata.get('source', 'unknown')
            self.parsed_logs.append(log_entry)
            print(f"Successfully parsed log entry")
        except Exception as e:
            print(f"Error parsing log entry: {e}")
            # Skip entries that can't be parsed
            continue
            
    # Convert to DataFrame for easier analysis if we have logs
    print(f"Total parsed logs: {len(self.parsed_logs)}")
    if self.parsed_logs:
        self.dataframe = pd.DataFrame(self.parsed_logs)
        print(f"DataFrame created with shape: {self.dataframe.shape}")
    else:
        print("No logs were successfully parsed")
        self.dataframe = None

@app.post("/analyze")
def analyze_logs(request: AnalysisRequest):
    """
    Endpoint to perform advanced analysis on the uploaded logs.
    """
    global log_analyzer, vectorstore
    
    if vectorstore is None:
        raise HTTPException(status_code=500, detail="No file has been uploaded or processed.")
        
    try:
        # Initialize analyzer if needed
        if log_analyzer is None:
            # Get documents from the vectorstore
            documents = vectorstore.as_retriever().get_relevant_documents("")
            log_analyzer = LogAnalyzer(documents)
            log_analyzer.process_documents()
        
        # Perform the requested analysis
        if request.analysis_type == "summary":
            result = log_analyzer.get_log_summary()
            return result
            
        elif request.analysis_type == "anomalies":
            result = log_analyzer.detect_anomalies()
            return result
            
        elif request.analysis_type == "security_events":
            result = log_analyzer.analyze_security_events()
            return result
            
        elif request.analysis_type == "report":
            result = log_analyzer.generate_report()
            return result
            
        elif request.analysis_type == "visualization":
            viz_type = request.options.get("visualization_type", "severity")
            title = request.options.get("title")
            output_path = os.path.join(VISUALIZATIONS_DIR, f"{viz_type}_{int(datetime.now().timestamp())}.png")
            
            # Generate the visualization
            viz_path = log_analyzer.create_visualization(viz_type, title, output_path)
            
            if viz_path:
                # Return relative path that can be used with the /visualizations endpoint
                return {"visualization_path": os.path.basename(viz_path)}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to generate {viz_type} visualization.")
                
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {request.analysis_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing analysis: {str(e)}")


@app.get("/initial-analysis")
def get_initial_analysis():
    """
    Perform an initial analysis of the uploaded log file.
    Returns summary statistics and key findings.
    """
    global log_analyzer, vectorstore
    
    if vectorstore is None:
        raise HTTPException(status_code=500, detail="No file has been uploaded or processed.")
        
    try:
        # Initialize analyzer if needed
        if log_analyzer is None:
            # Get documents from the vectorstore
            documents = vectorstore.as_retriever().get_relevant_documents("")
            log_analyzer = LogAnalyzer(documents)
            log_analyzer.process_documents()
        
        # Generate a comprehensive report
        report = log_analyzer.generate_report()
        
        # Generate visualizations for the report
        visualizations = {}
        viz_types = ["severity", "errors", "ip_addresses"]
        
        for viz_type in viz_types:
            output_path = os.path.join(VISUALIZATIONS_DIR, f"{viz_type}_{int(datetime.now().timestamp())}.png")
            viz_path = log_analyzer.create_visualization(viz_type, output_path=output_path)
            if viz_path:
                visualizations[viz_type] = os.path.basename(viz_path)
        
        report["visualizations"] = visualizations
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating initial analysis: {str(e)}")


# Update the upload_file endpoint to initialize the analyzer
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to upload a custom file for log analysis.
    """
    global vectorstore, qa_chain, log_analyzer

    # Save the uploaded file
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    # Determine file type and load data
    ext = os.path.splitext(file.filename)[1].lower()
    try:
        if ext in [".txt", ".log", ".md"]:
            data = load_text_file(file_path)
        elif ext == ".csv":
            data = load_csv_file(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

        # Prepare the vectorstore
        vectorstore = prepare_vectorstore(data)

        # Define the QA chain
        template = """You are a Level 1 SOC analyst analyzing server logs.
        Use the context below to answer the question as precisely and concisely as possible.
        {context}
        Question: {question}
        Answer:"""

        QA_CHAIN_PROMPT = PromptTemplate(
            input_variables=["context", "question"],
            template=template,
        )

        llm = OllamaLLM(model="llama3.1")
        qa_chain = RetrievalQA.from_chain_type(
            llm,
            retriever=vectorstore.as_retriever(),
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
        )
        
        # Initialize the log analyzer with the uploaded documents
        documents = vectorstore.docstore.docs.values()
        log_analyzer = LogAnalyzer(documents)

        return JSONResponse(content={"message": f"File '{file.filename}' successfully processed and vectorstore initialized."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

@app.get("/")
def read_root():
    """
    Root endpoint for API health check.
    """
    return {"message": "SOC Level 1 log analysis API is running. Upload a file to get started."}