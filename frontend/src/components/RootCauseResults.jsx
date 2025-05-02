import React, { useState } from 'react';
import { AlertTriangle, Info, CheckCircle, AlertCircle, ChevronDown, ChevronUp, Download, ArrowLeft } from 'lucide-react';

const SeverityBadge = ({ severity }) => {
  const badgeStyles = {
    critical: "bg-red-900 text-red-100",
    high: "bg-orange-800 text-orange-100",
    medium: "bg-yellow-700 text-yellow-100",
    low: "bg-blue-800 text-blue-100"
  };
  
  const icons = {
    critical: <AlertTriangle className="w-3 h-3" />,
    high: <AlertCircle className="w-3 h-3" />,
    medium: <Info className="w-3 h-3" />,
    low: <CheckCircle className="w-3 h-3" />
  };
  
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${badgeStyles[severity]}`}>
      <span className="mr-1">{icons[severity]}</span>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
};

const IssueCard = ({ issue }) => {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className="mb-4 border border-gray-700 rounded-lg overflow-hidden bg-gray-800">
      <div 
        className="p-4 flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <SeverityBadge severity={issue.severity} />
          <h3 className="font-medium text-white">{issue.title}</h3>
        </div>
        <button className="text-gray-400 hover:text-white">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>
      
      {expanded && (
        <div className="p-4 border-t border-gray-700 bg-gray-900">
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-300 mb-1">Description</h4>
            <p className="text-gray-300">{issue.description}</p>
          </div>
          
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-300 mb-1">Evidence</h4>
            <div className="bg-gray-950 p-3 rounded-md border border-gray-800 overflow-x-auto">
              {issue.evidence.map((entry, i) => (
                <div key={i} className="text-gray-300 font-mono text-sm mb-1">
                  {entry}
                </div>
              ))}
            </div>
          </div>
          
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-300 mb-1">Root Cause</h4>
            <p className="text-gray-300">{issue.root_cause}</p>
          </div>
          
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-300 mb-1">Remediation Steps</h4>
            <ul className="list-disc list-inside text-gray-300">
              {issue.remediation.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ul>
          </div>
          
          {issue.references && issue.references.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-1">References</h4>
              <ul className="list-disc list-inside text-blue-400">
                {issue.references.map((ref, i) => (
                  <li key={i}>
                    <a href={ref} className="hover:underline" target="_blank" rel="noopener noreferrer">
                      {ref}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const RootCauseResults = ({ results, onReset }) => {
  const [filterSeverity, setFilterSeverity] = useState('all');
  
  const filteredIssues = filterSeverity === 'all'
    ? results.issues
    : results.issues.filter(issue => issue.severity === filterSeverity);
  
  const handleExport = () => {
    const jsonString = JSON.stringify(results, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-${results.file_name}-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
  };
  
  const handleNewAnalysis = async () => {
    if (results.file_id) {
      // Analysis was performed on an existing file, go back to file selection
      onReset();
    } else {
      // No file_id, just reset the component
      onReset();
    }
  };
  
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="bg-gray-800 rounded-lg shadow-lg overflow-hidden">
        <div className="p-6 border-b border-gray-700">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-white">Analysis Results</h2>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleNewAnalysis}
                className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 flex items-center"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back to Files
              </button>
              <button
                onClick={handleExport}
                className="px-3 py-1.5 bg-blue-700 text-white rounded hover:bg-blue-600 flex items-center"
              >
                <Download className="w-4 h-4 mr-1" />
                Export Results
              </button>
            </div>
          </div>
          
          <div className="mt-4 p-4 bg-gray-900 rounded-md">
            <p className="text-gray-300 mb-3">{results.summary}</p>
            <div className="flex items-center space-x-6">
              <div>
                <span className="text-gray-400">File Name:</span>{' '}
                <span className="text-white">{results.file_name}</span>
              </div>
              <div>
                <span className="text-gray-400">Size:</span>{' '}
                <span className="text-white">{(results.file_size / 1024).toFixed(2)} KB</span>
              </div>
              {results.file_id && (
                <div>
                  <span className="text-gray-400">File ID:</span>{' '}
                  <span className="text-white">{results.file_id}</span>
                </div>
              )}
            </div>
          </div>
        </div>
        
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-4">
              <h3 className="text-lg font-medium text-white">Issues Found</h3>
              <div className="flex items-center space-x-2">
                <span className="bg-red-900 text-red-100 px-2.5 py-1 rounded-full text-xs">{results.statistics.critical}</span>
                <span className="bg-orange-800 text-orange-100 px-2.5 py-1 rounded-full text-xs">{results.statistics.high}</span>
                <span className="bg-yellow-700 text-yellow-100 px-2.5 py-1 rounded-full text-xs">{results.statistics.medium}</span>
                <span className="bg-blue-800 text-blue-100 px-2.5 py-1 rounded-full text-xs">{results.statistics.low}</span>
              </div>
            </div>
            
            <div>
              <select 
                className="bg-gray-700 text-white rounded border-gray-600 py-1 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
              >
                <option value="all">All Issues ({results.statistics.total_issues})</option>
                <option value="critical">Critical ({results.statistics.critical})</option>
                <option value="high">High ({results.statistics.high})</option>
                <option value="medium">Medium ({results.statistics.medium})</option>
                <option value="low">Low ({results.statistics.low})</option>
              </select>
            </div>
          </div>
          
          {filteredIssues.length > 0 ? (
            <div>
              {filteredIssues.map(issue => (
                <IssueCard key={issue.id} issue={issue} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-400">No issues found with the selected severity level.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RootCauseResults;