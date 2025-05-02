# src/evaluation/rag_evaluator.py

from typing import List, Dict, Any, Optional
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from rouge_score import rouge_scorer
from sklearn.metrics import precision_recall_fscore_support
import numpy as np

class RAGEvaluator:
    """
    A comprehensive evaluation module for RAG systems.
    
    Provides:
    - Accuracy measurement
    - Retrieval effectiveness
    - Answer relevance
    - Visualization of results
    """
    
    def __init__(self, rag_system=None):
        """
        Initialize the RAG evaluator.
        
        Args:
            rag_system: RAG system to evaluate (optional)
        """
        self.rag_system = rag_system
        self.eval_results = []
        self.ground_truth_data = {}
        
        # Create output directories
        self.results_dir = "./evaluation_results"
        self.viz_dir = "./evaluation_viz"
        
        for dir_path in [self.results_dir, self.viz_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                
        # Initialize Rouge scorer
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    def load_ground_truth(self, filepath):
        """
        Load ground truth data from JSON file.
        
        Args:
            filepath: Path to the ground truth file
            
        Returns:
            Dictionary containing ground truth data
        """
        try:
            with open(filepath, 'r') as f:
                self.ground_truth_data = json.load(f)
            return self.ground_truth_data
        except Exception as e:
            print(f"Error loading ground truth data: {e}")
            return {}
    
    def save_ground_truth(self, filepath):
        """
        Save ground truth data to a file.
        
        Args:
            filepath: Where to save the ground truth
        """
        with open(filepath, 'w') as f:
            json.dump(self.ground_truth_data, f, indent=2)
    
    def create_evaluation_dataset(self, documents, num_samples=20, save_path=None):
        """
        Create evaluation dataset from documents.
        
        Args:
            documents: List of document objects
            num_samples: Number of samples to generate
            save_path: Where to save the dataset
            
        Returns:
            Dictionary with test queries and ground truth
        """
        if self.rag_system:
            dataset = self.rag_system.generate_evaluation_dataset(documents, num_samples)
        else:
            # Manual dataset creation if no RAG system is provided
            dataset = self._manual_dataset_creation(documents, num_samples)
        
        # Store in the instance
        self.ground_truth_data = dataset
        
        # Save if path is provided
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(dataset, f, indent=2)
        
        return dataset
    
    def _manual_dataset_creation(self, documents, num_samples):
        """Create evaluation dataset manually from documents."""
        # Simplified implementation for when no LLM is available
        queries = []
        ground_truth = {}
        
        import random
        sample_docs = random.sample(documents, min(num_samples, len(documents)))
        
        for i, doc in enumerate(sample_docs):
            # Extract potential information from the document
            content = doc.page_content
            
            # Generate a simple question based on content keywords
            keywords = ["error", "failed", "warning", "critical", "success", 
                       "access", "user", "IP", "server", "login"]
            
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    # Create a query about this keyword
                    query = f"What {keyword} events are mentioned in the logs?"
                    queries.append(query)
                    
                    # Extract a sentence containing the keyword as ground truth
                    sentences = content.split('. ')
                    relevant = [s for s in sentences if keyword.lower() in s.lower()]
                    answer = '. '.join(relevant) if relevant else f"Information about {keyword}"
                    
                    ground_truth[query] = answer
                    break
            
            # If no keyword matched, create a generic question
            if not any(keyword.lower() in content.lower() for keyword in keywords):
                query = f"Summarize log entry {i+1}"
                queries.append(query)
                ground_truth[query] = content[:100] + "..."  # First 100 chars
        
        return {
            "test_queries": queries,
            "ground_truth": ground_truth
        }
    
    def evaluate(self, rag_system=None, test_queries=None, ground_truth=None):
        """
        Evaluate RAG system performance.
        
        Args:
            rag_system: RAG system to evaluate (optional)
            test_queries: List of test queries (optional)
            ground_truth: Ground truth answers (optional)
            
        Returns:
            Dictionary of evaluation metrics
        """
        # Use provided system or stored one
        system = rag_system or self.rag_system
        if not system:
            raise ValueError("No RAG system provided for evaluation")
        
        # Use provided queries/ground truth or stored ones
        queries = test_queries or self.ground_truth_data.get("test_queries", [])
        truth = ground_truth or self.ground_truth_data.get("ground_truth", {})
        
        if not queries or not truth:
            raise ValueError("No test queries or ground truth data available")
        
        # Initialize results
        results = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_queries": len(queries),
                "rouge1": 0,
                "rouge2": 0, 
                "rougeL": 0,
                "precision": 0,
                "recall": 0,
                "f1": 0,
                "retrieval_precision": 0,
                "mean_answer_relevance": 0
            },
            "query_results": []
        }
        
        for query in queries:
            if query not in truth:
                continue
                
            # Get RAG response
            response = system.query(query)
            answer = response.get("response", "")
            
            # Correct answer
            correct_answer = truth[query]
            
            # Calculate ROUGE scores
            rouge_scores = self.rouge_scorer.score(answer, correct_answer)
            
            # Calculate other metrics
            retrieval_stats = self._calculate_retrieval_precision(
                response.get("source_documents", []), 
                correct_answer
            )
            
            relevance_score = self._calculate_answer_relevance(answer, query, correct_answer)
            
            # Store query results
            query_result = {
                "query": query,
                "rag_answer": answer,
                "ground_truth": correct_answer,
                "rouge1": rouge_scores["rouge1"].fmeasure,
                "rouge2": rouge_scores["rouge2"].fmeasure,
                "rougeL": rouge_scores["rougeL"].fmeasure,
                "retrieval_precision": retrieval_stats["precision"],
                "retrieval_recall": retrieval_stats["recall"],
                "answer_relevance": relevance_score
            }
            
            results["query_results"].append(query_result)
            
            # Update aggregate metrics
            results["metrics"]["rouge1"] += rouge_scores["rouge1"].fmeasure
            results["metrics"]["rouge2"] += rouge_scores["rouge2"].fmeasure
            results["metrics"]["rougeL"] += rouge_scores["rougeL"].fmeasure
            results["metrics"]["precision"] += retrieval_stats["precision"]
            results["metrics"]["recall"] += retrieval_stats["recall"]
            results["metrics"]["retrieval_precision"] += retrieval_stats["precision"]
            results["metrics"]["mean_answer_relevance"] += relevance_score
        
        # Calculate averages
        if len(results["query_results"]) > 0:
            for key in results["metrics"]:
                if key != "total_queries":
                    results["metrics"][key] /= len(results["query_results"])
        
        # Calculate F1 score
        p = results["metrics"]["precision"]
        r = results["metrics"]["recall"]
        results["metrics"]["f1"] = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        
        # Store the results
        self.eval_results.append(results)
        
        return results
    
    def _calculate_retrieval_precision(self, retrieved_docs, correct_answer):
        """Calculate precision and recall of retrieved documents."""
        if not retrieved_docs:
            return {"precision": 0, "recall": 0}
        
        # Get tokens from correct answer
        correct_tokens = set(correct_answer.lower().split())
        
        # Count relevant docs (containing key tokens from correct answer)
        relevant_count = 0
        for doc in retrieved_docs:
            doc_tokens = set(doc["content"].lower().split())
            if len(correct_tokens.intersection(doc_tokens)) > 0:
                relevant_count += 1
        
        precision = relevant_count / len(retrieved_docs) if retrieved_docs else 0
        
        # Recall is harder without knowing all relevant docs, using a proxy
        # Assume recall is proportional to token coverage
        token_coverage = 0
        all_doc_tokens = set()
        for doc in retrieved_docs:
            all_doc_tokens.update(doc["content"].lower().split())
        
        token_coverage = len(correct_tokens.intersection(all_doc_tokens)) / len(correct_tokens) if correct_tokens else 0
        
        return {
            "precision": precision,
            "recall": token_coverage
        }
    
    def _calculate_answer_relevance(self, answer, query, correct_answer):
        """Calculate how relevant the answer is to the query."""
        # Simple implementation - could be improved with semantic similarity
        query_tokens = set(query.lower().split())
        answer_tokens = set(answer.lower().split())
        
        # Count query terms in answer
        overlap = len(query_tokens.intersection(answer_tokens))
        
        # Check answer length - penalize very short answers
        length_factor = min(1.0, len(answer) / 100)
        
        # Calculate relevance score
        relevance = (overlap / len(query_tokens) if query_tokens else 0) * length_factor
        
        return relevance
    
    def save_results(self, results=None, filename=None):
        """Save evaluation results to file."""
        data = results or (self.eval_results[-1] if self.eval_results else None)
        if not data:
            return None
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.results_dir}/rag_eval_{timestamp}.json"
            
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        return filename
    
    def visualize_results(self, results=None, save_path=None):
        """
        Create visualizations of evaluation results.
        
        Args:
            results: Results to visualize (optional, uses latest if not provided)
            save_path: Directory to save visualizations
            
        Returns:
            Dictionary of saved visualization paths
        """
        data = results or (self.eval_results[-1] if self.eval_results else None)
        if not data:
            return None
            
        save_dir = save_path or self.viz_dir
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        viz_paths = {}
        
        # Create dataframe from query results
        query_results = data.get("query_results", [])
        if not query_results:
            return {}
            
        df = pd.DataFrame(query_results)
        
        # 1. ROUGE scores comparison
        plt.figure(figsize=(10, 6))
        rouge_cols = [col for col in df.columns if col.startswith('rouge')]
        rouge_df = df[rouge_cols]
        
        sns.boxplot(data=rouge_df)
        plt.title('ROUGE Scores Distribution')
        plt.ylabel('Score')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        rouge_path = f"{save_dir}/rouge_scores_{timestamp}.png"
        plt.savefig(rouge_path)
        plt.close()
        viz_paths['rouge_scores'] = rouge_path
        
        # 2. Retrieval precision vs answer relevance
        plt.figure(figsize=(10, 6))
        sns.scatterplot(
            x='retrieval_precision', 
            y='answer_relevance', 
            data=df,
            alpha=0.7,
            s=100
        )
        plt.title('Retrieval Precision vs Answer Relevance')
        plt.xlabel('Retrieval Precision')
        plt.ylabel('Answer Relevance')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add a line of best fit
        sns.regplot(
            x='retrieval_precision', 
            y='answer_relevance', 
            data=df,
            scatter=False
        )
        
        rel_prec_path = f"{save_dir}/relevance_precision_{timestamp}.png"
        plt.savefig(rel_prec_path)
        plt.close()
        viz_paths['relevance_precision'] = rel_prec_path
        
        # 3. Combined metrics radar chart
        metrics = data.get("metrics", {})
        if metrics:
            metric_keys = [
                'rouge1', 'rouge2', 'rougeL', 
                'precision', 'recall', 'f1', 
                'retrieval_precision', 'mean_answer_relevance'
            ]
            
            values = [metrics.get(m, 0) for m in metric_keys]
            
            # Create radar chart
            angles = np.linspace(0, 2*np.pi, len(metric_keys), endpoint=False).tolist()
            values = values + [values[0]]  # Close the loop
            angles = angles + [angles[0]]  # Close the loop
            
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
            ax.plot(angles, values, 'o-', linewidth=2)
            ax.fill(angles, values, alpha=0.25)
            ax.set_thetagrids(np.degrees(angles[:-1]), metric_keys)
            ax.set_ylim(0, 1)
            plt.title('RAG System Performance Metrics', size=15)
            
            radar_path = f"{save_dir}/metrics_radar_{timestamp}.png"
            plt.savefig(radar_path)
            plt.close()
            viz_paths['radar_chart'] = radar_path
            
        return viz_paths


# Usage function for evaluator
def evaluate_rag_performance(rag_system, test_data=None, ground_truth=None, generate_viz=True):
    """
    Evaluate RAG system performance.
    
    Args:
        rag_system: The RAG system to evaluate
        test_data: Test queries (optional)
        ground_truth: Ground truth answers (optional)
        generate_viz: Whether to generate visualizations
        
    Returns:
        Dictionary with evaluation results and visualization paths
    """
    evaluator = RAGEvaluator(rag_system)
    
    # Use provided test data or generate new data
    if not test_data and not ground_truth:
        # Get documents from the vectorstore
        documents = list(rag_system.vectorstore.docstore.docs.values())
        
        # Generate evaluation dataset
        dataset = evaluator.create_evaluation_dataset(
            documents, 
            num_samples=10,
            save_path="./evaluation_results/test_dataset.json"
        )
        test_data = dataset.get("test_queries", [])
        ground_truth = dataset.get("ground_truth", {})
    
    # Run evaluation
    results = evaluator.evaluate(
        rag_system=rag_system,
        test_queries=test_data,
        ground_truth=ground_truth
    )
    
    # Save results
    results_file = evaluator.save_results(results)
    
    # Generate visualizations if requested
    viz_paths = {}
    if generate_viz:
        viz_paths = evaluator.visualize_results(results)
    
    return {
        "results": results,
        "results_file": results_file,
        "visualizations": viz_paths
    }