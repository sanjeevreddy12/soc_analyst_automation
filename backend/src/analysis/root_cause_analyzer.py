
import os
import json
import requests
from typing import Dict, Any, Union
import logging

class RootCauseAnalyzer:
    """
    Class for performing root cause analysis on log files using Groq API.
    """
    
    def __init__(self, api_key: str = "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"):
        """
        Initialize the RootCauseAnalyzer with the Groq API key.
        
        Args:
            api_key: The Groq API key
        """
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logging.info("RootCauseAnalyzer initialized with Groq API")
        
    async def analyze_logs(self, file) -> Dict[str, Any]:
        """
        Analyze log contents for root causes of issues.
        
        Args:
            file: A file-like object with read() method and filename attribute
            
        Returns:
            Dictionary containing the analysis results
        """
        try:
            # Read the file content
            content = await file.read()
            
            # Decode content if it's bytes
            if isinstance(content, bytes):
                try:
                    content = content.decode('utf-8')
                except UnicodeDecodeError:
                    return {
                        "error": "File encoding error - please ensure the file is properly encoded as UTF-8",
                        "status": "failed",
                        "file_name": file.filename
                    }
                
            # Log file information
            logging.info(f"Analyzing log file: {file.filename}, size: {len(content)} bytes")
            
            # Prepare the prompt for root cause analysis
            system_prompt = """You are an expert cybersecurity analyst specializing in log analysis and root cause identification.
Your task is to analyze log content to identify the root causes of any issues, prioritized by severity."""
            
            # Build the user prompt more safely
            user_prompt = self._build_root_cause_prompt(content)
            
            # Call Groq API
            try:
                # Prepare the request payload
                payload = {
                    "model": "llama3-8b-8192",  # You can change this to any supported model
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,  # Lower temperature for more deterministic responses
                    "response_format": {"type": "json_object"}
                }
                
                # Make the API call
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                # Check if the request was successful
                response.raise_for_status()
                
                # Parse the response
                response_json = response.json()
                response_text = response_json["choices"][0]["message"]["content"]
                
                # Parse the analysis
                analysis = self._parse_llm_response(response_text)
                
                # Add metadata
                analysis["file_name"] = file.filename
                analysis["file_size"] = len(content)
                
                return analysis
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Error making request to Groq API: {str(e)}")
                return {
                    "error": str(e),
                    "status": "failed",
                    "file_name": file.filename
                }
            except Exception as e:
                logging.error(f"Error analyzing logs with Groq API: {str(e)}")
                return {
                    "error": str(e),
                    "status": "failed",
                    "file_name": file.filename
                }
        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "file_name": file.filename if hasattr(file, 'filename') else "unknown"
            }
    
    def _build_root_cause_prompt(self, log_content: str) -> str:
        """
        Build a specialized prompt for root cause analysis.
        
        Args:
            log_content: The content of the log file
            
        Returns:
            A prompt string for the LLM
        """
        # Sample size for large files (first 10000 chars)
        log_sample = log_content[:10000] if len(log_content) > 10000 else log_content
        
        # Safely build the prompt using string concatenation instead of formatting
        prompt = (
            "Analyze the following log content to identify the root causes of any issues, prioritized by severity.\n\n"
            "LOG CONTENT:\n"
            "```\n"
            + log_sample +
            "\n```\n\n"
            "INSTRUCTIONS:\n"
            "1. Identify the most likely root causes of any issues in the logs\n"
            "2. Prioritize the issues by severity (critical, high, medium, low)\n"
            "3. For each issue, extract specific evidence from the logs\n"
            "4. Provide specific remediation steps for each issue\n"
            "5. Include reference documentation links if applicable\n\n"
            "FORMAT YOUR RESPONSE AS A JSON OBJECT with the following structure:\n"
            '{\n'
            '    "summary": "Brief summary of the log analysis",\n'
            '    "issues": [\n'
            '        {\n'
            '            "id": "unique_id",\n'
            '            "title": "Issue title",\n'
            '            "severity": "critical|high|medium|low",\n'
            '            "description": "Detailed description of the issue",\n'
            '            "evidence": ["Log entry 1", "Log entry 2"],\n'
            '            "root_cause": "Explanation of the root cause",\n'
            '            "remediation": ["Step 1", "Step 2"],\n'
            '            "references": ["Reference 1", "Reference 2"]\n'
            '        }\n'
            '    ],\n'
            '    "statistics": {\n'
            '        "total_issues": 0,\n'
            '        "critical": 0,\n'
            '        "high": 0,\n'
            '        "medium": 0,\n'
            '        "low": 0\n'
            '    }\n'
            '}'
        )
        
        return prompt
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the LLM response and ensure it's in the correct format.
        
        Args:
            response_text: The text response from the LLM
            
        Returns:
            A structured dictionary of the analysis
        """
        try:
            # Try to parse the response as JSON
            analysis = json.loads(response_text)
            
            # Validate the required fields
            if "summary" not in analysis or "issues" not in analysis:
                # Add missing fields if necessary
                if "summary" not in analysis:
                    analysis["summary"] = "Analysis completed but summary not provided"
                if "issues" not in analysis:
                    analysis["issues"] = []
                
            # Generate statistics if not present
            if "statistics" not in analysis:
                severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                for issue in analysis["issues"]:
                    severity = issue.get("severity", "").lower()
                    if severity in severity_counts:
                        severity_counts[severity] += 1
                
                analysis["statistics"] = {
                    "total_issues": len(analysis["issues"]),
                    **severity_counts
                }
                
            return analysis
            
        except json.JSONDecodeError:
            # If the response is not valid JSON, return a basic structure
            logging.error("Failed to parse Groq API response as JSON")
            return {
                "summary": "Failed to parse analysis results",
                "issues": [],
                "statistics": {
                    "total_issues": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                },
                "raw_response": response_text[:1000]  # Include part of the raw response for debugging
            }