import React, { useState, useEffect } from 'react';
import { Upload, AlertCircle, FileIcon } from 'lucide-react';

const RootCauseUploader = ({ onAnalysisComplete }) => {
  const [file, setFile] = useState(null);
  const [userFiles, setUserFiles] = useState([]);
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const supportedTypes = ['.log', '.txt', '.md', '.csv', '.json'];
  
  // Fetch user's files when component mounts
  useEffect(() => {
    fetchUserFiles();
  }, []);
  const token = localStorage.getItem('token'); 
  
  const fetchUserFiles = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/files', {
        method: 'GET',
        headers:{
          "Authorization": `Bearer ${token}`

        },
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      
      const data = await response.json();
      setUserFiles(data.files || []);
    } catch (err) {
      setError('Error loading your files. Please refresh the page.');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (selectedFile) => {
    // Check file extension
    const fileName = selectedFile.name;
    const fileExtension = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
    
    if (!supportedTypes.includes(fileExtension)) {
      setError(`Unsupported file type. Please upload ${supportedTypes.join(', ')} files.`);
      setFile(null);
      return;
    }
    
    setFile(selectedFile);
    setSelectedFileId(null); // Clear any selected existing file
    setError(null);
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };
  
  const handleExistingFileSelect = (fileId) => {
    setSelectedFileId(fileId);
    setFile(null); // Clear any new file selection
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file && !selectedFileId) {
      setError("Please select a file to analyze");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      let response;
      
      if (file) {
        // Upload new file first
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch('http://127.0.0.1:8000/upload', {
          method: 'POST',
          headers:{
            "Authorization": `Bearer ${token}`
  
          },
          body: formData,
          credentials: 'include',
        });
        
        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json();
          throw new Error(errorData.message || 'Failed to upload file');
        }
        
        const uploadResult = await uploadResponse.json();
        const fileId = uploadResult.file_id;
        
        // Now analyze the newly uploaded file
        response = await fetch('http://127.0.0.1:8000/root-cause-analysis', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ file_id: fileId }),
          credentials: 'include',
        });
      } else {
        // Analyze existing file
        response = await fetch('http://127.0.0.1:8000/root-cause-analysis', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ file_id: selectedFileId }),
          credentials: 'include',
        });
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to analyze log file');
      }
      
      const analysisResult = await response.json();
      onAnalysisComplete(analysisResult);
      
      // Refresh file list after successful upload
      if (file) {
        fetchUserFiles();
      }
      
    } catch (err) {
      setError(err.message || 'An error occurred during analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-6 bg-gray-800 rounded-lg shadow-lg">
      <h2 className="text-xl font-semibold text-white mb-4">Root Cause Analysis</h2>
      
      {userFiles.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-medium text-white mb-2">Your Files</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {userFiles.map(file => (
              <div 
                key={file.id}
                onClick={() => handleExistingFileSelect(file.id)}
                className={`p-3 border rounded-md flex items-center cursor-pointer
                  ${selectedFileId === file.id 
                    ? 'bg-blue-700/20 border-blue-600' 
                    : 'bg-gray-700 border-gray-600 hover:border-gray-500'}`}
              >
                <FileIcon className="w-5 h-5 text-gray-400 mr-2" />
                <div className="overflow-hidden">
                  <p className="text-sm text-white truncate">{file.filename}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(file.upload_date).toLocaleDateString()} • 
                    {(file.file_size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div className="mb-4">
        <h3 className="text-lg font-medium text-white mb-2">Upload New File</h3>
        <form onSubmit={handleSubmit}>
          <div 
            className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center text-center
              ${dragActive ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-gray-400'}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="w-12 h-12 text-gray-400 mb-4" />
            
            <p className="text-lg text-gray-300 mb-2">
              {file ? file.name : 'Drag and drop your log file here'}
            </p>
            
            <p className="text-sm text-gray-400 mb-4">
              {file 
                ? `${(file.size / 1024).toFixed(2)} KB` 
                : `Supported formats: ${supportedTypes.join(', ')}`}
            </p>
            
            {!file && (
              <div>
                <label className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer">
                  Browse Files
                  <input
                    type="file"
                    className="hidden"
                    accept=".log,.txt,.md,.csv,.json"
                    onChange={handleFileChange}
                  />
                </label>
              </div>
            )}
            
            {file && (
              <div className="flex space-x-3 mt-2">
                <button 
                  type="button"
                  className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600"
                  onClick={() => setFile(null)}
                >
                  Change File
                </button>
              </div>
            )}
          </div>
          
          <div className="mt-4 flex justify-center">
            <button 
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={loading || (!file && !selectedFileId)}
            >
              {loading ? 'Analyzing...' : 'Start Analysis'}
            </button>
          </div>
        </form>
      </div>
      
      {error && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-md flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0 mt-0.5" />
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}
      
      <div className="mt-6">
        <h3 className="text-lg font-medium text-white mb-2">Supported File Types</h3>
        <ul className="list-disc list-inside text-gray-300 space-y-1">
          <li>.log - Standard log files</li>
          <li>.txt - Text files containing logs</li>
          <li>.md - Markdown files with log content</li>
          <li>.csv - Comma-separated values for structured logs</li>
          <li>.json - JSON-formatted log data</li>
        </ul>
      </div>
    </div>
  );
};

export default RootCauseUploader;