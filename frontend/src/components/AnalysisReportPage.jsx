import React, { useState } from "react";
import {
  Download,
  FileText,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Clock,
  AlertTriangle,
  Shield,
  PieChart,
  Server,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";

const SectionHeader = ({ title, children, isOpen, toggleOpen }) => (
  <div className="border-b border-gray-700 pb-4 mb-6">
    <button 
      onClick={toggleOpen}
      className="flex items-center justify-between w-full text-xl font-semibold text-white"
    >
      <span>{title}</span>
      {isOpen ? (
        <ChevronUp className="h-5 w-5 text-gray-400" />
      ) : (
        <ChevronDown className="h-5 w-5 text-gray-400" />
      )}
    </button>
    {isOpen && <div className="mt-6">{children}</div>}
  </div>
);

const MetricCard = ({ icon: Icon, title, value, color, description }) => (
  <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 hover:border-blue-400 transition-colors">
    <div className="flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-400">{title}</p>
        <p className="text-2xl font-semibold text-white">{value}</p>
        {description && <p className="text-xs text-gray-400 mt-1">{description}</p>}
      </div>
    </div>
  </div>
);

const ThreatItem = ({ threat, severity, description, recommendation }) => {
  const severityColors = {
    high: "bg-red-500/10 text-red-400 border-red-500/20",
    medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };

  return (
    <div className={`rounded-lg p-4 mb-4 border ${severityColors[severity.toLowerCase()]}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium">{threat}</h3>
        <span className={`px-2 py-1 text-xs rounded-full ${
          severity === "high" ? "bg-red-500/20" : 
          severity === "medium" ? "bg-yellow-500/20" : 
          "bg-blue-500/20"
        }`}>
          {severity.toUpperCase()}
        </span>
      </div>
      <p className="text-sm mb-3">{description}</p>
      <div>
        <p className="text-xs font-medium mb-1">RECOMMENDATION:</p>
        <p className="text-sm">{recommendation}</p>
      </div>
    </div>
  );
};

const AnalysisReportPage = () => {
  const location = useLocation();
  const { fileName, analysis } = location.state || { 
    fileName: "Unknown File",
    analysis: null 
  };

  // Sections visibility state
  const [sections, setSections] = useState({
    summary: true,
    metrics: true,
    threats: true,
    recommendations: true,
    rawData: false
  });

  const toggleSection = (section) => {
    setSections({
      ...sections,
      [section]: !sections[section]
    });
  };

  // Function to download report as JSON
  const downloadReport = () => {
    const reportData = JSON.stringify(analysis, null, 2);
    const blob = new Blob([reportData], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileName.split('.')[0]}-analysis-report.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Function to download report as text/markdown
  const downloadReportAsText = () => {
    // Convert analysis data to readable text format
    let reportText = `# Security Analysis Report for ${fileName}\n\n`;
    reportText += `## Summary\n${analysis.summary}\n\n`;
    reportText += `## Metrics\n`;
    reportText += `- Total Log Entries: ${analysis.metrics.totalEntries}\n`;
    reportText += `- Critical Errors: ${analysis.metrics.criticalErrors}\n`;
    reportText += `- Success Rate: ${analysis.metrics.successRate}%\n`;
    reportText += `- Suspicious Activities: ${analysis.metrics.suspiciousActivities}\n\n`;
    
    reportText += `## Identified Threats\n`;
    analysis.threats.forEach((threat, idx) => {
      reportText += `### ${idx + 1}. ${threat.name} (${threat.severity})\n`;
      reportText += `${threat.description}\n`;
      reportText += `**Recommendation:** ${threat.recommendation}\n\n`;
    });
    
    reportText += `## Recommendations\n`;
    analysis.recommendations.forEach((rec, idx) => {
      reportText += `${idx + 1}. ${rec}\n`; 
    });
    
    reportText += `\n## Raw Data Examples\n`;
    reportText += `${analysis.rawDataExamples}\n`;
    
    // Create and download file
    const blob = new Blob([reportText], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileName.split('.')[0]}-analysis-report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Use this when no analysis data is available
  const mockAnalysisData = {
    summary: "This is a placeholder for when analysis data is unavailable. In a real implementation, this would contain the LLM-generated analysis summary based on the uploaded log file.",
    metrics: {
      totalEntries: "N/A",
      criticalErrors: "N/A",
      successRate: "N/A",
      suspiciousActivities: "N/A"
    },
    threats: [
      {
        name: "Example Threat",
        severity: "medium",
        description: "This is a placeholder for an identified threat.",
        recommendation: "This would contain a specific recommendation for addressing the threat."
      }
    ],
    recommendations: [
      "This section would contain specific recommendations based on the analysis."
    ],
    rawDataExamples: "This section would contain extracted examples from the log data that are relevant to the analysis."
  };

  // Use actual analysis data or fallback to mock data
  const reportData = analysis || mockAnalysisData;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800">
      <header className="border-b border-gray-700 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Back</span>
              </Link>
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-blue-400" />
                <h1 className="text-lg font-semibold text-white">
                  Security Analysis Report
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={downloadReportAsText}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>Download as MD</span>
              </button>
              <button
                onClick={downloadReport}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>Download as JSON</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">{fileName}</h2>
          </div>
          <p className="text-gray-300">{reportData.summary}</p>
        </div>

        <div className="space-y-8">
          {/* Metrics Section */}
          <SectionHeader 
            title="Key Metrics" 
            isOpen={sections.metrics}
            toggleOpen={() => toggleSection('metrics')}
          >
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <MetricCard
                icon={FileText}
                title="Total Log Entries"
                value={reportData.metrics.totalEntries}
                color="bg-blue-500"
              />
              <MetricCard
                icon={AlertTriangle}
                title="Critical Errors"
                value={reportData.metrics.criticalErrors}
                color="bg-red-500"
              />
              <MetricCard
                icon={Server}
                title="Success Rate"
                value={`${reportData.metrics.successRate}%`}
                color="bg-green-500"
              />
              <MetricCard
                icon={PieChart}
                title="Suspicious Activities"
                value={reportData.metrics.suspiciousActivities}
                color="bg-yellow-500"
              />
            </div>
          </SectionHeader>

          {/* Threats Section */}
          <SectionHeader 
            title="Identified Threats" 
            isOpen={sections.threats}
            toggleOpen={() => toggleSection('threats')}
          >
            <div className="space-y-4">
              {reportData.threats.map((threat, index) => (
                <ThreatItem
                  key={index}
                  threat={threat.name}
                  severity={threat.severity}
                  description={threat.description}
                  recommendation={threat.recommendation}
                />
              ))}
            </div>
          </SectionHeader>

          {/* Recommendations Section */}
          <SectionHeader 
            title="Recommendations" 
            isOpen={sections.recommendations}
            toggleOpen={() => toggleSection('recommendations')}
          >
            <div className="bg-gray-800/50 rounded-lg p-4">
              <ul className="space-y-3">
                {reportData.recommendations.map((recommendation, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-sm">
                      {index + 1}
                    </span>
                    <p className="text-gray-300">{recommendation}</p>
                  </li>
                ))}
              </ul>
            </div>
          </SectionHeader>

          {/* Raw Data Examples */}
          <SectionHeader 
            title="Raw Data Examples" 
            isOpen={sections.rawData}
            toggleOpen={() => toggleSection('rawData')}
          >
            <div className="bg-gray-800 rounded-lg p-4 overflow-x-auto">
              <pre className="text-gray-300 text-sm whitespace-pre-wrap">
                {reportData.rawDataExamples}
              </pre>
            </div>
          </SectionHeader>
        </div>
      </main>
    </div>
  );
};

export default AnalysisReportPage;