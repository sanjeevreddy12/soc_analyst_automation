
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq  
from langchain_core.prompts import PromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
import json
import os
import re
from src.utils.suppress_stdout import SuppressStdout

class EnhancedRAG:
    """
    Enhanced RAG system with advanced chunking, metadata filtering, and evaluation capabilities.
    """
    
    def __init__(self, embedding_model="nomic-embed-text", llm_model="llama3-8b-8192", chunk_size=500, chunk_overlap=50, api_key="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"):
        """
        Initialize the enhanced RAG system.
        
        Args:
            embedding_model: Model name for embeddings
            llm_model: LLM model for generation
            chunk_size: Text chunk size for splitting
            chunk_overlap: Overlap between chunks
            api_key: Groq API key
        """
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.api_key = api_key
        self.vectorstore = None
        self.qa_chain = None
        self.evaluation_results = []
        
        self.eval_dir = "./evaluation"
        if not os.path.exists(self.eval_dir):
            os.makedirs(self.eval_dir)
        
        
        self.qa_template = """You are a Level 1 SOC analyst analyzing server logs.
        Use the context below to answer the question as precisely and concisely as possible.
        If you don't find the exact answer in the context, say so rather than making up information.
        
        Context:
        {context}
        
        Question: {question}
        Answer:"""
    
    def prepare_vectorstore(self, documents):
        """
        Prepare the vector store with advanced chunking strategy.
        
        Args:
            documents: List of document objects
            
        Returns:
            FAISS vector store
        """
       
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        all_splits = text_splitter.split_documents(documents)
        
        # Enhance metadata for better filtering later
        for i, doc in enumerate(all_splits):
            doc.metadata["chunk_id"] = i
            doc.metadata["timestamp"] = datetime.now().isoformat()
            
            # Extract log-specific metadata if present
            if "timestamp" in doc.page_content:
                # Attempt to extract timestamp from content
                import re
                timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', doc.page_content)
                if timestamp_match:
                    doc.metadata["log_timestamp"] = timestamp_match.group(0)
            
            # Determine log severity if present
            for severity in ["ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"]:
                if severity in doc.page_content:
                    doc.metadata["severity"] = severity
                    break
        
        # Create embeddings and vector DB
        with SuppressStdout():
            local_embeddings = OllamaEmbeddings(model=self.embedding_model)
            self.vectorstore = FAISS.from_documents(all_splits, local_embeddings)
        
        return self.vectorstore
    
    def setup_qa_chain(self):
        """
        Set up an enhanced QA chain with compression and better context handling.
        
        Returns:
            RetrievalQA chain
        """
        if not self.vectorstore:
            raise ValueError("Vector store not initialized. Call prepare_vectorstore first.")
        
        # Create the base retriever
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",  # Use maximal marginal relevance for diversity
            search_kwargs={"k": 5, "fetch_k": 10}
        )
        
        # Add contextual compression to the retriever
        with SuppressStdout():
            # Replace OllamaLLM with ChatGroq
            llm = ChatGroq(model=self.llm_model, groq_api_key=self.api_key, temperature=0.1)
            compressor = LLMChainExtractor.from_llm(llm)
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=retriever
            )
        
        # Create prompt
        QA_CHAIN_PROMPT = PromptTemplate(
            input_variables=["context", "question"],
            template=self.qa_template,
        )
        
        # Set up the QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm,
            retriever=compression_retriever,
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
            return_source_documents=True  # Return sources for evaluation
        )
        
        return self.qa_chain
    
    def query(self, query_text, filter_metadata=None):
        """
        Query the RAG system with metadata filtering options.
        
        Args:
            query_text: The query text
            filter_metadata: Optional metadata filters dict
            
        Returns:
            Dict containing response and source documents
        """
        if not self.qa_chain:
            self.setup_qa_chain()
        
        # Preprocess the query - expand acronyms, normalize terms
        processed_query = self._preprocess_query(query_text)
        
        # Set up inputs
        inputs = {"query": processed_query}
        
        # Apply metadata filters if provided
        if filter_metadata and hasattr(self.qa_chain.retriever, "search_kwargs"):
            self.qa_chain.retriever.search_kwargs["filter"] = filter_metadata
        
        # Get the answer
        try:
            result = self.qa_chain.invoke(inputs)
            
            # Format the response
            response = {
                "query": query_text,
                "processed_query": processed_query,
                "response": result.get("result", "No result found."),
                "source_documents": [
                    {"content": doc.page_content, "metadata": doc.metadata}
                    for doc in result.get("source_documents", [])
                ]
            }
            
            return response
        except Exception as e:
            return {
                "query": query_text,
                "error": str(e),
                "response": "Error processing query."
            }
    
    def _preprocess_query(self, query_text):
        """
        Preprocess the query for better matching.
        
        Args:
            query_text: Original query
            
        Returns:
            Processed query
        """
        # Simple preprocessing for now
        query = query_text.strip()
        
        # Expand common SOC acronyms
        acronyms = {
            "IP": "IP address",
            "IDS": "intrusion detection system",
            "IPS": "intrusion prevention system",
            "FW": "firewall",
            "SOC": "security operations center",
            "SIEM": "security information and event management"
        }
        
        for acronym, expansion in acronyms.items():
            # Replace standalone acronyms with expanded form
            query = query.replace(f" {acronym} ", f" {expansion} ")
        
        return query
    
    def evaluate_accuracy(self, test_queries, ground_truth, save_results=True):
        """
        Evaluate RAG accuracy using test queries and ground truth.
        
        Args:
            test_queries: List of test queries
            ground_truth: Dictionary mapping queries to correct answers
            save_results: Whether to save evaluation results
            
        Returns:
            Dictionary of evaluation metrics
        """
        if not self.qa_chain:
            self.setup_qa_chain()
        
        results = {
            "total_queries": len(test_queries),
            "correct": 0,
            "partial": 0,
            "incorrect": 0,
            "retrieval_precision": 0,
            "query_details": []
        }
        
        for i, query in enumerate(test_queries):
            if query not in ground_truth:
                continue
                
            # Get the RAG response
            response = self.query(query)
            answer = response.get("response", "")
            
            # Get ground truth
            correct_answer = ground_truth[query]
            
            # Compare with ground truth - very basic for now
            accuracy = self._calculate_answer_accuracy(answer, correct_answer)
            
            # Calculate retrieval precision
            retrieved_docs = response.get("source_documents", [])
            relevant_docs = sum(1 for doc in retrieved_docs if any(
                keyword in doc["content"] for keyword in correct_answer.split()[:5]
            ))
            retrieval_precision = relevant_docs / len(retrieved_docs) if retrieved_docs else 0
            
            # Record result
            query_result = {
                "query": query,
                "rag_answer": answer,
                "ground_truth": correct_answer,
                "accuracy": accuracy,
                "retrieval_precision": retrieval_precision
            }
            results["query_details"].append(query_result)
            
            # Update counters
            if accuracy > 0.8:
                results["correct"] += 1
            elif accuracy > 0.3:
                results["partial"] += 1
            else:
                results["incorrect"] += 1
                
            results["retrieval_precision"] += retrieval_precision
        
        # Calculate averages
        if results["total_queries"] > 0:
            results["retrieval_precision"] /= results["total_queries"]
            results["accuracy"] = (results["correct"] + 0.5 * results["partial"]) / results["total_queries"]
        
        # Save results
        if save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.eval_dir}/evaluation_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(results, f, indent=2)
        
        self.evaluation_results.append(results)
        return results
    
    def _calculate_answer_accuracy(self, answer, ground_truth):
        """
        Calculate accuracy between answer and ground truth.
        
        Args:
            answer: RAG generated answer
            ground_truth: Correct answer
            
        Returns:
            Accuracy score between 0 and 1
        """
        # Simple word overlap calculation - could be improved
        answer_words = set(answer.lower().split())
        truth_words = set(ground_truth.lower().split())
        
        if not truth_words:
            return 0
            
        overlap = len(answer_words.intersection(truth_words))
        return overlap / len(truth_words)
    
    def generate_evaluation_dataset(self, documents, num_samples=10):
        """
        Generate evaluation dataset from documents.
        
        Args:
            documents: List of document objects
            num_samples: Number of samples to generate
            
        Returns:
            Dictionary with test queries and ground truth
        """
        # Create sample queries and answers from documents
        queries = []
        ground_truth = {}
        
        # Use LLM to generate questions from documents
        with SuppressStdout():
            # Replace OllamaLLM with ChatGroq
            llm = ChatGroq(model=self.llm_model, groq_api_key=self.api_key, temperature=0.1)
            
            # Select random documents
            import random
            sample_docs = random.sample(documents, min(num_samples, len(documents)))
            
            for doc in sample_docs:
                prompt = f"""Given the following log entry, generate a specific question that a SOC analyst might ask, and the correct answer based solely on this information:
                
                LOG ENTRY:
                {doc.page_content}
                
                FORMAT:
                Question: [specific security-related question]
                Answer: [precise answer based only on the log entry]
                """
                
                response = llm.invoke(prompt)
                
                # Extract question and answer
                question_match = re.search(r'Question: (.*?)(?:\n|$)', response)
                answer_match = re.search(r'Answer: (.*?)(?:\n|$)', response)
                
                if question_match and answer_match:
                    question = question_match.group(1).strip()
                    answer = answer_match.group(1).strip()
                    
                    queries.append(question)
                    ground_truth[question] = answer
        
        return {
            "test_queries": queries,
            "ground_truth": ground_truth
        }


def prepare_enhanced_rag(data, embedding_model="nomic-embed-text", llm_model="llama3-8b-8192", api_key="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"):
    """
    Create and prepare an enhanced RAG system with the given data.
    
    Args:
        data: Document data
        embedding_model: Model name for embeddings
        llm_model: LLM model name
        api_key: Groq API key
        
    Returns:
        EnhancedRAG object ready for queries
    """
    # Initialize the RAG system
    rag = EnhancedRAG(
        embedding_model=embedding_model,
        llm_model=llm_model,
        chunk_size=500,
        chunk_overlap=100,
        api_key=api_key
    )
    
    # Prepare vectorstore
    rag.prepare_vectorstore(data)
    
    # Set up QA chain
    rag.setup_qa_chain()
    
    return rag