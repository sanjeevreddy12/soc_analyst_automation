import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./components/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import HomePage from "./components/HomePage";
import ChatPage from "./components/ChatPage";
import HistoryManager from "./components/HistoryManager";
import LogAnalyzerDashboard from "./components/LogAnalyzerDashboard";
import Login from "./components/Login";
import Register from "./components/Register"; // Note: fix the filename on your end
import AnalysisReportPage from "./components/AnalysisReportPage"
import RootCauseAnalyzerPage from "./components/RootCauseAnalyzerPage";
import FileDashboard from "./components/FileDashboard";

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Protected Routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          } />
          <Route path="/chat" element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          } />
          <Route path="/history" element={
            <ProtectedRoute>
              <HistoryManager />
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <LogAnalyzerDashboard />
            </ProtectedRoute>
          } />
          <Route path="/report" element={
            <ProtectedRoute>
              <AnalysisReportPage/>
            </ProtectedRoute>
          } />
          <Route path="/file-dashboard" element={
            <ProtectedRoute>
              <FileDashboard/>
              
                          </ProtectedRoute>
          } />
          <Route path="/root-cause-analysis" element={
           
              <RootCauseAnalyzerPage/>
            
          } />

        </Routes>
      </Router>
    </AuthProvider>
  );
}