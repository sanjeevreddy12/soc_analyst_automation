# src/analysis/log_analyzer.py

import re
import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime, timedelta
import json
from src.utils.suppress_stdout import SuppressStdout
from src.utils.graph_generator import generate_bar_graph_from_query

class LogAnalyzer:
    """
    Advanced log analysis functionality for security operations.
    Provides methods to extract patterns, perform statistical analysis, 
    and identify security events from log data.
    """
    
    def __init__(self, documents=None):
        """
        Initialize with document objects from vector store.
        
        Args:
            documents: List of document objects from the vector store
        """
        self.documents = documents or []
        self.parsed_logs = []
        self.dataframe = None
        self.common_patterns = {}
        
    def set_documents(self, documents):
        """Update the documents and reprocess them."""
        self.documents = documents
        self.process_documents()
        
    def process_documents(self):
        """Process the document objects into structured log data."""
        self.parsed_logs = []
        
        for doc in self.documents:
            content = doc.page_content
            metadata = doc.metadata
            
            # Try to parse the log entry
            try:
                log_entry = self._parse_log_entry(content)
                log_entry['source'] = metadata.get('source', 'unknown')
                self.parsed_logs.append(log_entry)
            except Exception as e:
                # Skip entries that can't be parsed
                continue
                
        # Convert to DataFrame for easier analysis if we have logs
        if self.parsed_logs:
            self.dataframe = pd.DataFrame(self.parsed_logs)
            
    def _parse_log_entry(self, log_text):
        """
        Parse a log entry into structured data.
        This method attempts to extract common log components like timestamp,
        severity, event type, and message.
        """
        log_entry = {'raw_message': log_text}
        
        # Try to extract timestamp
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)',  # ISO format
            r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',  # Syslog format
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})'  # MM/DD/YYYY format
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, log_text)
            if match:
                log_entry['timestamp'] = match.group(1)
                break
        
        # Try to extract severity level
        severity_pattern = r'\b(CRITICAL|ERROR|WARNING|INFO|DEBUG|ALERT|EMERGENCY|NOTICE)\b'
        severity_match = re.search(severity_pattern, log_text, re.IGNORECASE)
        if severity_match:
            log_entry['severity'] = severity_match.group(1).upper()
        
        # Try to extract IP addresses
        ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        ip_addresses = re.findall(ip_pattern, log_text)
        if ip_addresses:
            log_entry['ip_addresses'] = ip_addresses
        
        # Try to extract error codes
        error_code_pattern = r'\b(ERR|ERROR)[\s_:]+([A-Z0-9_]+)\b'
        error_match = re.search(error_code_pattern, log_text)
        if error_match:
            log_entry['error_code'] = error_match.group(2)
            
        # Extract user information if available
        user_pattern = r'\buser[\s:=]+([^\s,;]+)'
        user_match = re.search(user_pattern, log_text, re.IGNORECASE)
        if user_match:
            log_entry['user'] = user_match.group(1)
            
        return log_entry
    
    def get_log_summary(self):
        """
        Generate a summary of the log data.
        
        Returns:
            dict: Summary statistics about the logs
        """
        if not self.dataframe is not None and not self.dataframe.empty:
            return {"error": "No logs to analyze"}
        
        summary = {
            "total_logs": len(self.dataframe),
            "time_range": None,
            "severity_counts": None,
            "top_error_codes": None,
            "top_ip_addresses": None,
            "top_users": None
        }
        
        # Time range
        if 'timestamp' in self.dataframe.columns:
            try:
                timestamps = pd.to_datetime(self.dataframe['timestamp'])
                summary["time_range"] = {
                    "start": timestamps.min().isoformat(),
                    "end": timestamps.max().isoformat(),
                    "duration": str(timestamps.max() - timestamps.min())
                }
            except:
                pass
        
        # Severity counts
        if 'severity' in self.dataframe.columns:
            severity_counts = self.dataframe['severity'].value_counts().to_dict()
            summary["severity_counts"] = severity_counts
            
        # Top error codes
        if 'error_code' in self.dataframe.columns:
            top_errors = self.dataframe['error_code'].value_counts().head(10).to_dict()
            summary["top_error_codes"] = top_errors
            
        # Top IP addresses
        if 'ip_addresses' in self.dataframe.columns:
            # Flatten list of IP addresses
            all_ips = []
            for ips in self.dataframe['ip_addresses'].dropna():
                all_ips.extend(ips)
            ip_counts = Counter(all_ips)
            summary["top_ip_addresses"] = dict(ip_counts.most_common(10))
            
        # Top users
        if 'user' in self.dataframe.columns:
            top_users = self.dataframe['user'].value_counts().head(10).to_dict()
            summary["top_users"] = top_users
            
        return summary
    
    def detect_anomalies(self):
        """
        Detect anomalies in the log data.
        
        Returns:
            dict: Information about detected anomalies
        """
        anomalies = {
            "severity_spikes": [],
            "unusual_patterns": [],
            "potential_security_events": []
        }
        
        if self.dataframe is None or self.dataframe.empty:
            return {"error": "No logs to analyze for anomalies"}
        
        # Check for severity spikes (unusual number of errors/critical events)
        if 'timestamp' in self.dataframe.columns and 'severity' in self.dataframe.columns:
            try:
                # Convert to datetime and group by hour
                self.dataframe['datetime'] = pd.to_datetime(self.dataframe['timestamp'])
                hourly_severity = self.dataframe.groupby([
                    self.dataframe['datetime'].dt.date, 
                    self.dataframe['datetime'].dt.hour, 
                    'severity'
                ]).size().unstack(fill_value=0)
                
                # Look for hours with unusually high error/critical counts
                for severity in ['ERROR', 'CRITICAL', 'EMERGENCY', 'ALERT']:
                    if severity in hourly_severity.columns:
                        mean = hourly_severity[severity].mean()
                        std = hourly_severity[severity].std()
                        threshold = mean + 2*std  # 2 standard deviations
                        
                        # Find outlier hours
                        outliers = hourly_severity[hourly_severity[severity] > threshold]
                        for (date, hour), value in outliers[severity].items():
                            anomalies["severity_spikes"].append({
                                "date": str(date),
                                "hour": hour,
                                "severity": severity,
                                "count": int(value),
                                "average": float(mean),
                                "threshold": float(threshold)
                            })
            except Exception as e:
                pass
        
        # Look for brute force patterns (multiple failed logins)
        if 'raw_message' in self.dataframe.columns:
            failed_logins = self.dataframe[
                self.dataframe['raw_message'].str.contains('failed|unauthorized|invalid password', case=False)
            ]
            
            if 'user' in failed_logins.columns and 'ip_addresses' in failed_logins.columns:
                # Group by user and count failed attempts
                for user, user_logs in failed_logins.groupby('user'):
                    if len(user_logs) >= 5:  # 5+ failed attempts is suspicious
                        anomalies["potential_security_events"].append({
                            "type": "multiple_failed_logins",
                            "user": user,
                            "count": len(user_logs),
                            "ip_addresses": list(set(sum(user_logs['ip_addresses'].dropna().tolist(), [])))
                        })
        
        # Look for unusual access patterns
        if 'raw_message' in self.dataframe.columns:
            mask = self.dataframe[
                self.dataframe['raw_message'].str.contains('unusual|suspicious|unexpected|outside business hours', case=False)
            ]
            unusual_access = self.dataframe[mask]
            
            for _, log in unusual_access.iterrows():
                event = {
                    "message": log['raw_message'],
                    "timestamp": log.get('timestamp', 'unknown')
                }
                
                if 'ip_addresses' in log and not pd.isna(log['ip_addresses']):
                    event["ip_addresses"] = log['ip_addresses']
                    
                anomalies["unusual_patterns"].append(event)
                
        return anomalies
    
    def create_visualization(self, data_type, title=None, output_path=None):
        """
        Create visualizations of specific aspects of the log data.
        
        Args:
            data_type: Type of data to visualize (severity, errors, ips, etc.)
            title: Optional title for the visualization
            output_path: Optional path to save the visualization
            
        Returns:
            str: Path to the generated visualization
        """
        if self.dataframe is None or self.dataframe.empty:
            return None
            
        visualization_data = {}
        
        if data_type == 'severity':
            if 'severity' in self.dataframe.columns:
                severity_counts = self.dataframe['severity'].value_counts().to_dict()
                visualization_data = severity_counts
                if not title:
                    title = "Log Severity Distribution"
                    
        elif data_type == 'errors':
            if 'error_code' in self.dataframe.columns:
                error_counts = self.dataframe['error_code'].value_counts().head(10).to_dict()
                visualization_data = error_counts
                if not title:
                    title = "Top Error Codes"
                    
        elif data_type == 'ip_addresses':
            if 'ip_addresses' in self.dataframe.columns:
                all_ips = []
                for ips in self.dataframe['ip_addresses'].dropna():
                    all_ips.extend(ips)
                ip_counts = Counter(all_ips).most_common(10)
                visualization_data = dict(ip_counts)
                if not title:
                    title = "Top IP Addresses"
        
        if not output_path:
            output_path = f"./visualization_{data_type}.png"
            
        if visualization_data:
            return generate_bar_graph_from_query(visualization_data, output_path)
        
        return None
    
    def analyze_security_events(self):
        """
        Analyze logs specifically for security-relevant events.
        
        Returns:
            dict: Security events categorized by type
        """
        security_events = {
            "authentication_failures": [],
            "access_violations": [],
            "data_exfiltration": [],
            "malware_indicators": [],
            "privilege_escalation": []
        }
        
        if self.dataframe is None or self.dataframe.empty:
            return {"error": "No logs to analyze for security events"}
        
        # Look for authentication failures
        auth_failure_keywords = ['failed login', 'authentication failure', 'invalid password', 'auth failed']
        auth_failures = self._find_events_with_keywords(auth_failure_keywords)
        for _, event in auth_failures.iterrows():
            event_data = {
                "timestamp": event.get('timestamp', 'unknown'),
                "message": event['raw_message']
            }
            if 'user' in event and not pd.isna(event['user']):
                event_data['user'] = event['user']
            if 'ip_addresses' in event and not pd.isna(event['ip_addresses'].all()):
                event_data['ip_addresses'] = event['ip_addresses']
                
            security_events["authentication_failures"].append(event_data)
        
        # Look for access violations
        access_keywords = ['unauthorized access', 'permission denied', 'access denied', 'forbidden']
        access_violations = self._find_events_with_keywords(access_keywords)
        for _, event in access_violations.iterrows():
            event_data = {
                "timestamp": event.get('timestamp', 'unknown'),
                "message": event['raw_message']
            }
            if 'user' in event and not pd.isna(event['user']):
                event_data['user'] = event['user']
            if 'ip_addresses' in event and not pd.isna(event['ip_addresses'].all()):
                event_data['ip_addresses'] = event['ip_addresses']
                
            security_events["access_violations"].append(event_data)
        
        # Look for data exfiltration
        exfil_keywords = ['large download', 'data transfer', 'unusual download', 'excessive', 'data access']
        exfil_events = self._find_events_with_keywords(exfil_keywords)
        for _, event in exfil_events.iterrows():
            event_data = {
                "timestamp": event.get('timestamp', 'unknown'),
                "message": event['raw_message']
            }
            if 'user' in event and not pd.isna(event['user']):
                event_data['user'] = event['user']
            if 'ip_addresses' in event and not pd.isna(event['ip_addresses'].all()):
                event_data['ip_addresses'] = event['ip_addresses']
                
            security_events["data_exfiltration"].append(event_data)
        
        # Look for malware indicators
        malware_keywords = ['malware', 'virus', 'trojan', 'backdoor', 'ransomware', 'command and control']
        malware_events = self._find_events_with_keywords(malware_keywords)
        for _, event in malware_events.iterrows():
            security_events["malware_indicators"].append({
                "timestamp": event.get('timestamp', 'unknown'),
                "message": event['raw_message']
            })
        
        # Look for privilege escalation
        escalation_keywords = ['privilege escalation', 'sudo', 'root access', 'admin rights', 'elevated']
        escalation_events = self._find_events_with_keywords(escalation_keywords)
        for _, event in escalation_events.iterrows():
            event_data = {
                "timestamp": event.get('timestamp', 'unknown'),
                "message": event['raw_message']
            }
            if 'user' in event and not pd.isna(event['user']):
                event_data['user'] = event['user']
                
            security_events["privilege_escalation"].append(event_data)
        
        return security_events
    
    def _find_events_with_keywords(self, keywords):
        """Helper to find events containing specific keywords"""
        if 'raw_message' not in self.dataframe.columns:
            return pd.DataFrame()
            
        pattern = '|'.join(keywords)
        return self.dataframe[self.dataframe['raw_message'].str.contains(pattern, case=False)]
    
    def generate_report(self):
        """
        Generate a comprehensive security report from the log analysis.
        
        Returns:
            dict: Complete report with all analysis sections
        """
        report = {
            "summary": self.get_log_summary(),
            "anomalies": self.detect_anomalies(),
            "security_events": self.analyze_security_events()
        }
        
        # Add recommendations based on findings
        report["recommendations"] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report):
        """Generate security recommendations based on analysis results"""
        recommendations = []
        
        # Check for brute force attack indicators
        if report["anomalies"].get("potential_security_events"):
            brute_force_events = [e for e in report["anomalies"]["potential_security_events"] 
                                 if e.get("type") == "multiple_failed_logins"]
            if brute_force_events:
                recommendations.append({
                    "priority": "High",
                    "title": "Potential Brute Force Attacks Detected",
                    "description": f"Found {len(brute_force_events)} instances of multiple failed login attempts.",
                    "action": "Implement account lockout policies and IP-based rate limiting. Review affected accounts."
                })
        
        # Check for severity spikes
        if report["anomalies"].get("severity_spikes"):
            recommendations.append({
                "priority": "Medium",
                "title": "Unusual Error/Critical Event Spikes",
                "description": f"Detected {len(report['anomalies']['severity_spikes'])} time periods with unusually high numbers of severe events.",
                "action": "Investigate these time periods for potential security incidents or system issues."
            })
        
        # Check for malware indicators
        if report["security_events"].get("malware_indicators") and len(report["security_events"]["malware_indicators"]) > 0:
            recommendations.append({
                "priority": "Critical",
                "title": "Malware Activity Indicators",
                "description": f"Found {len(report['security_events']['malware_indicators'])} logs indicating possible malware activity.",
                "action": "Isolate affected systems, initiate malware scanning and cleanup procedures."
            })
        
        # Check for excessive authentication failures
        if report["security_events"].get("authentication_failures") and len(report["security_events"]["authentication_failures"]) > 10:
            recommendations.append({
                "priority": "High",
                "title": "Excessive Authentication Failures",
                "description": f"Found {len(report['security_events']['authentication_failures'])} authentication failure events.",
                "action": "Review authentication policies, implement MFA where possible, and investigate potential compromise."
            })
        
        # Check for privilege escalation attempts
        if report["security_events"].get("privilege_escalation") and len(report["security_events"]["privilege_escalation"]) > 0:
            recommendations.append({
                "priority": "High",
                "title": "Privilege Escalation Attempts",
                "description": f"Found {len(report['security_events']['privilege_escalation'])} potential privilege escalation events.",
                "action": "Audit user permissions, review sudo/administrator access policies, and verify legitimate need for elevated access."
            })
            
        return recommendations