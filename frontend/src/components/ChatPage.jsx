import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User,
  Loader,
  ArrowLeft,
  FileText,
  AlertTriangle,
  Clock,
  Search,
  FileDigit,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useHistoryManager } from "./HistoryManager";
import { useLocation, Link, useNavigate } from "react-router-dom";
import NavBar from "./Navbar";

const ErrorAlert = ({ message }) => (
  <div className="flex items-center gap-2 bg-red-500/10 text-red-400 px-4 py-2 rounded-lg">
    <AlertTriangle className="h-4 w-4" />
    <p className="text-sm">{message}</p>
  </div>
);

const ChatMessage = ({ text, isBot, timestamp = new Date(), error }) => {
  const isError = text.toLowerCase().includes("critical error") || error;

  return (
    <div className={`flex gap-3 ${isBot ? "justify-start" : "justify-end"}`}>
      <div
        className={`flex gap-3 max-w-[80%] ${
          isBot ? "flex-row" : "flex-row-reverse"
        }`}
      >
        <div className="flex-shrink-0 mt-1">
          {isBot ? (
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <Bot className="w-5 h-5 text-blue-400" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center">
              <User className="w-5 h-5 text-gray-300" />
            </div>
          )}
        </div>

        <div
          className={`flex flex-col gap-1 ${
            isBot ? "items-start" : "items-end"
          }`}
        >
          <div
            className={`rounded-lg p-4 ${
              isBot
                ? isError
                  ? "bg-red-500/10 border border-red-500/20"
                  : "bg-blue-500/10 border border-blue-500/20"
                : "bg-gray-800 border border-gray-700"
            }`}
          >
            {isError && isBot && (
              <div className="flex items-center gap-2 text-red-400 mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium">Critical Error Detected</span>
              </div>
            )}
            <div
              className={`text-sm prose prose-invert max-w-none ${
                isError && isBot ? "text-red-200" : "text-gray-200"
              }`}
            >
              {isBot ? (
                <ReactMarkdown
                  components={{
                    code: ({ node, inline, className, children, ...props }) => (
                      <code
                        className={`${
                          inline
                            ? "bg-gray-800 px-1 py-0.5 rounded"
                            : "block bg-gray-800 p-4 rounded-lg"
                        } ${className}`}
                        {...props}
                      >
                        {children}
                      </code>
                    ),
                  }}
                >
                  {text}
                </ReactMarkdown>
              ) : (
                <p>{text}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Clock className="w-3 h-3" />
            {timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};

const QuerySuggestion = ({ text, onClick }) => (
  <button
    onClick={onClick}
    className="flex items-center gap-2 w-full text-left p-3 rounded-lg bg-gray-800/50 
             text-gray-300 hover:bg-gray-800 transition-colors text-sm group"
  >
    <Search className="w-4 h-4 text-gray-400 group-hover:text-blue-400 transition-colors" />
    {text}
  </button>
);

export default function ChatPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [fileId, setFileId] = useState(() => {
    console.log("Location state:", location.state); // Debug log
    return location.state?.fileId || localStorage.getItem('currentFileId');
  });
  useEffect(() => {
    console.log("Current fileId:", fileId);
    if (!fileId) {
      console.error("No fileId available in state. Check your navigation.");
    }
  }, [fileId]);
  
  // const { updateHistory } = useHistoryManager();
  const historyId = location.state?.historyId;

  // const handleNewMessage = (message) => {
  //   if (historyId) {
  //     updateHistory(historyId, {
  //       messageCount: messages.length + 1,
  //       lastMessage: message.text,
  //     });
  //   }
  // };

  const [messages, setMessages] = useState([
    {
      text: "I've analyzed your security logs. Ask me about specific events, errors, or patterns.",
      isBot: true,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const messagesEndRef = useRef(null);

  // handleNewMessage(messages)
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const queryRAG = async (query) => {
    try {
      const token = localStorage.getItem('token');
      console.log("Sending query with fileId:", fileId); 
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: {
           "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query,file_id: fileId,use_enhanced:true }),
      });

      if (!response.ok) throw new Error(`API Error: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Query Error:", error);
      throw error;
    }
  };

  const generateReport = async () => {
    try {
      setIsGeneratingReport(true);
      
      const response = await fetch(`http://localhost:8000/initial-analysis/${fileId}`);
      
      if (!response.ok) throw new Error(`API Error: ${response.status}`);
      
      const analysisData = await response.json();
      
      
      navigate("/report", {
        state: {
          fileName: location.state?.fileName, 
          analysis: analysisData
        }
      });
    } catch (error) {
      console.error("Report Generation Error:", error);
      setError("Failed to generate report. Please try again.");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setError(null);

    setMessages((prev) => [
      ...prev,
      {
        text: userMessage,
        isBot: false,
        timestamp: new Date(),
      },
    ]);

    setIsLoading(true);

    try {
      const { response } = await queryRAG(userMessage);

      setMessages((prev) => [
        ...prev,
        {
          text: response,
          isBot: true,
          timestamp: new Date(),
        },
      ]);
    } catch (error) {
      setError("Failed to get response. Please try again.");
      setMessages((prev) => [
        ...prev,
        {
          text: "I apologize, but I encountered an error processing your request. Please try again.",
          isBot: true,
          error: true,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gradient-to-b from-gray-900 to-gray-800">
      <NavBar />
      
      <header className="border-b border-gray-700 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link
                to="/file-dashboard"
                className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Back to Dashboard</span>
              </Link>
              
              {location.state?.fileName && (
                <div className="flex items-center gap-2 ml-4 pl-4 border-l border-gray-700">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-200">{location.state.fileName}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-4">
              {error && <ErrorAlert message={error} />}
              
              <button
                onClick={generateReport}
                disabled={isGeneratingReport || messages.length < 2}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 
                         disabled:bg-gray-600 disabled:cursor-not-allowed text-white 
                         rounded-lg transition-colors duration-200"
              >
                {isGeneratingReport ? (
                  <Loader className="w-4 h-4 animate-spin" />
                ) : (
                  <FileDigit className="w-4 h-4" />
                )}
                Generate Report
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-4 py-6">
          <div className="flex gap-6 h-full">
            <div className="flex-1 flex flex-col bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
              <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {messages.map((message, index) => (
                  <ChatMessage key={index} {...message} />
                ))}
                {isLoading && (
                  <div className="flex items-center gap-3 text-blue-400 p-4">
                    <Loader className="w-4 h-4 animate-spin" />
                    <span className="text-sm">
                      Analyzing logs and generating response...
                    </span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <form
                onSubmit={handleSubmit}
                className="border-t border-gray-700 p-4"
              >
                <div className="flex gap-4">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about specific events, errors, or patterns in your logs..."
                    className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-3 
                             focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 
                             disabled:cursor-not-allowed text-white rounded-lg px-6 py-3 
                             transition-colors duration-200 flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    Send
                  </button>
                </div>
              </form>
            </div>

            <div className="w-80 space-y-6 hidden lg:block">
              <div className="bg-gray-900 rounded-xl border border-gray-700 p-4">
                <h3 className="text-lg font-semibold text-white mb-4">
                  Quick Queries
                </h3>
                <div className="space-y-2">
                  <QuerySuggestion
                    text="Show critical errors"
                    onClick={() => setInput("What are the critical errors?")}
                  />
                  <QuerySuggestion
                    text="Find failed login attempts"
                    onClick={() =>
                      setInput("Show me all failed login attempts")
                    }
                  />
                  <QuerySuggestion
                    text="List suspicious IPs"
                    onClick={() => setInput("List any suspicious IP addresses")}
                  />
                </div>
              </div>

              <div className="bg-gray-900 rounded-xl border border-gray-700 p-4">
                <h3 className="text-lg font-semibold text-white mb-4">
                  Analysis Tips
                </h3>
                <ul className="space-y-3 text-sm text-gray-400">
                  <li className="flex items-start gap-2">
                    <Clock className="w-4 h-4 mt-0.5 text-blue-400" />
                    Specify time ranges for targeted analysis
                  </li>
                  <li className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5 text-blue-400" />
                    Look for patterns in error messages
                  </li>
                  <li className="flex items-start gap-2">
                    <Search className="w-4 h-4 mt-0.5 text-blue-400" />
                    Use specific error codes when available
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}