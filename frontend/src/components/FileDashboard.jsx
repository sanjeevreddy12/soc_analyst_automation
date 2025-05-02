import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FileText, ArrowLeft, Filter, RefreshCw } from "lucide-react";
import { LoadingOverlay } from "./LoadingComponents";
import { CustomAlert } from "./CustomAlert";
import NavBar from "./Navbar";

const FileDashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  
  const [fileId, setFileId] = useState(() => {
   
    const stateFileId = location.state?.fileId;
    if (stateFileId) {
      // Save to localStorage for persistence
      localStorage.setItem('currentFileId', stateFileId);
      return stateFileId;
    }
    
    return localStorage.getItem('currentFileId');
  });
  
  
  const [fileName, setFileName] = useState(location.state?.fileName || localStorage.getItem('currentFileName'));
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [logData, setLogData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [timeFilter, setTimeFilter] = useState("");
  const [ipFilter, setIpFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [messageFilter, setMessageFilter] = useState("");
  const [uniqueIps, setUniqueIps] = useState([]);
  const [uniqueTimes, setUniqueTimes] = useState([]);
  const [uniqueSeverities, setUniqueSeverities] = useState([]);

  useEffect(() => {
    // Save fileName to localStorage when it changes
    if (fileName && fileName !== "Log File") {
      localStorage.setItem('currentFileName', fileName);
    }
  }, [fileName]);

  useEffect(() => {
    if (!fileId) {
      setError("No file selected. Please select a file from the home page.");
      setLoading(false);
      return;
    }
    
    fetchFileData();
  }, [fileId, navigate]);

  const fetchFileData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
     
      const response = await fetch(`http://localhost:8000/initial-analysis/${fileId}`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch file data: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Set the log data
      setLogData(data.log_entries || []);
      setFilteredData(data.log_entries || []);
      
      // Extract unique IPs, timestamps, and severities for filtering
      extractFilterOptions(data.log_entries || []);
      
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const extractFilterOptions = (logs) => {
    // Extract unique timestamps, IPs, and severities for filter dropdowns
    const ips = [...new Set(logs.map(log => log.ip_address).filter(ip => ip !== "N/A"))];
    const times = [...new Set(logs.map(log => log.timestamp).filter(time => time !== "N/A"))];
    const severities = [...new Set(logs.map(log => log.severity))];
    
    setUniqueIps(ips);
    setUniqueTimes(times.slice(0, 20)); // Limit to avoid very large dropdowns
    setUniqueSeverities(severities);
  };

  const applyFilters = () => {
    let filtered = [...logData];
    
    if (timeFilter) {
      filtered = filtered.filter(log => log.timestamp.includes(timeFilter));
    }
    
    if (ipFilter) {
      filtered = filtered.filter(log => log.ip_address === ipFilter);
    }
    
    if (severityFilter) {
      filtered = filtered.filter(log => log.severity === severityFilter);
    }
    
    if (messageFilter) {
      filtered = filtered.filter(log => 
        log.message ? log.message.toLowerCase().includes(messageFilter.toLowerCase()) : 
        log.content.toLowerCase().includes(messageFilter.toLowerCase())
      );
    }
    
    setFilteredData(filtered);
  };

  const resetFilters = () => {
    setTimeFilter("");
    setIpFilter("");
    setSeverityFilter("");
    setMessageFilter("");
    setFilteredData(logData);
  };

  const getSeverityClass = (severity) => {
    switch(severity.toUpperCase()) {
      case "ERROR":
      case "CRITICAL":
      case "FATAL":
        return "text-red-500";
      case "WARNING":
      case "ALERT":
        return "text-yellow-500";
      case "INFO":
        return "text-blue-400";
      case "DEBUG":
        return "text-gray-400";
      default:
        return "text-gray-200";
    }
  };

  if (loading) {
    return <LoadingOverlay fileName={fileName} message="Loading file data..." />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 text-white p-4">
      <div className="max-w-7xl mx-auto">
        <NavBar/>
       
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-2">
            <FileText className="text-blue-400" />
            <h1 className="text-2xl font-bold">{fileName || "Log File"}</h1>
          </div>
        </div>

        {error && <CustomAlert message={error} type="error" className="mb-4" />}

        {/* File selection message when no file is selected */}
        {!fileId && (
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <FileText className="text-blue-400" />
              <p>Please select a file from the home page or upload a new file to analyze.</p>
            </div>
          </div>
        )}

        {/* Filter Section - only show if we have a fileId */}
        {fileId && (
          <div className="bg-gray-800 p-4 rounded-lg mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Filter size={18} className="text-blue-400" />
              <h2 className="text-lg font-semibold">Filters</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {/* Timestamp filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Timestamp</label>
                <select
                  value={timeFilter}
                  onChange={(e) => setTimeFilter(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                >
                  <option value="">All Timestamps</option>
                  {uniqueTimes.map((time, index) => (
                    <option key={index} value={time}>{time}</option>
                  ))}
                </select>
              </div>
              
              {/* IP Address filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">IP Address</label>
                <select
                  value={ipFilter}
                  onChange={(e) => setIpFilter(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                >
                  <option value="">All IP Addresses</option>
                  {uniqueIps.map((ip, index) => (
                    <option key={index} value={ip}>{ip}</option>
                  ))}
                </select>
              </div>
              
              {/* Severity filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Severity</label>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                >
                  <option value="">All Severities</option>
                  {uniqueSeverities.map((severity, index) => (
                    <option key={index} value={severity}>{severity}</option>
                  ))}
                </select>
              </div>
              
              {/* Message filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Message Filter</label>
                <input
                  type="text"
                  value={messageFilter}
                  onChange={(e) => setMessageFilter(e.target.value)}
                  placeholder="Filter by message content..."
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                />
              </div>
              
              {/* Filter buttons */}
              <div className="flex items-end gap-2">
                <button 
                  onClick={applyFilters}
                  className="flex-1 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded text-sm transition-colors"
                >
                  Apply Filters
                </button>
                <button 
                  onClick={resetFilters}
                  className="flex items-center justify-center bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
                >
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Log Table - only show if we have a fileId */}
        {fileId && (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-900 text-left">
                  <tr>
                    <th className="px-4 py-3 text-sm font-medium text-gray-300">Timestamp</th>
                    <th className="px-4 py-3 text-sm font-medium text-gray-300">IP Address</th>
                    <th className="px-4 py-3 text-sm font-medium text-gray-300">Severity</th>
                    <th className="px-4 py-3 text-sm font-medium text-gray-300">Message</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {filteredData.length > 0 ? (
                    filteredData.map((log, index) => (
                      <tr key={index} className="hover:bg-gray-750">
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{log.timestamp}</td>
                        <td className="px-4 py-3 text-sm font-mono">{log.ip_address}</td>
                        <td className={`px-4 py-3 text-sm ${getSeverityClass(log.severity)}`}>
                          {log.severity}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-300 max-w-xl truncate">
                          {log.message || log.content}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                        No log entries found or matching your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Pagination if needed */}
            {filteredData.length > 0 && (
              <div className="bg-gray-850 px-4 py-3 flex items-center justify-between border-t border-gray-700">
                <div className="text-sm text-gray-400">
                  Showing <span className="font-medium">{filteredData.length}</span> of{" "}
                  <span className="font-medium">{logData.length}</span> entries
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FileDashboard;