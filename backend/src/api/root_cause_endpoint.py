

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
import os
from typing import Dict, Any
from pydantic import BaseModel

# Import the RootCauseAnalyzer
from src.analysis.root_cause_analyzer import RootCauseAnalyzer
from src.auth.auth_models import get_current_active_user, User
from src.auth.file_db import get_file_by_id

# Create router for root cause analysis endpoints
router = APIRouter(tags=["root cause analysis"])

# Initialize the analyzer with default API key
root_cause_analyzer = RootCauseAnalyzer()

class RootCauseRequest(BaseModel):
    file_id: int

class FileWrapper:
    """
    A wrapper class to provide the interface expected by the RootCauseAnalyzer
    but working with a file path instead of an uploaded file.
    """
    def __init__(self, file_path, filename):
        self.file_path = file_path
        self.filename = filename
        self._content = None

    async def read(self):
        """
        Read the file content.
        """
        if self._content is None:
            with open(self.file_path, 'rb') as file:
                self._content = file.read()
        return self._content

@router.post("/root-cause-analysis")
async def perform_root_cause_analysis(
    request: RootCauseRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Endpoint to perform root cause analysis on a specific uploaded file.
    """
    file_id = request.file_id
    
    # Check if the file exists and belongs to the user
    file_info = get_file_by_id(file_id)
    if not file_info or file_info['user_id'] != current_user.id:
        raise HTTPException(status_code=404, detail="File not found or access denied.")
    
    try:
        # Create a wrapper object that provides the interface the analyzer expects
        file_wrapper = FileWrapper(
            file_path=file_info['file_path'],
            filename=file_info['filename']
        )
        
        # Perform the analysis with error handling
        analysis_result = await root_cause_analyzer.analyze_logs(file_wrapper)
        
        # Check if the result is valid
        if not isinstance(analysis_result, dict):
            raise ValueError("Analysis result is not in the expected format")
        
        # Add file information to the response
        analysis_result["file_id"] = file_id
        
        # Return the analysis result
        return analysis_result
            
    except Exception as e:
        logging.error(f"Error in root cause analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing root cause analysis: {str(e)}"
        )