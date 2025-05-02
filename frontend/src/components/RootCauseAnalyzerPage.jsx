import React, { useState } from 'react';
import NavBar from './NavBar';
import RootCauseUploader from './RootCauseUploader';
import RootCauseResults from './RootCauseResults';

const RootCauseAnalyzerPage = () => {
  const [analysisResults, setAnalysisResults] = useState(null);
  
  const handleAnalysisComplete = (results) => {
    setAnalysisResults(results);
  };
  
  const handleReset = () => {
    setAnalysisResults(null);
  };
  
  return (
    <div className="min-h-screen bg-gray-900 text-gray-200">
      <NavBar />
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Root Cause Analysis</h1>
          <p className="text-gray-400 mt-2">
            Upload or select log files to identify potential root causes and get remediation recommendations.
          </p>
        </div>
        
        <div className="my-8">
          {analysisResults ? (
            <RootCauseResults 
              results={analysisResults}
              onReset={handleReset}
            />
          ) : (
            <RootCauseUploader 
              onAnalysisComplete={handleAnalysisComplete}
            />
          )}
        </div>
      </main>
    </div>
  );
};

export default RootCauseAnalyzerPage;