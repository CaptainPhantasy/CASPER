#!/usr/bin/env python3
"""
CASPER Prime Progress Monitor
Real-time dashboard for tracking conflicts.md progress
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import socketserver

class ConflictsParser:
    def __init__(self, conflicts_path: str = "conflicts.md"):
        self.conflicts_path = Path(conflicts_path)
        self.last_modified = 0
        self.cached_data = None

    def parse_conflicts(self) -> Dict[str, Any]:
        """Parse the conflicts.md file and extract progress data."""
        if not self.conflicts_path.exists():
            return {"error": "conflicts.md not found"}

        # Check if file has been modified
        current_modified = self.conflicts_path.stat().st_mtime
        if current_modified == self.last_modified and self.cached_data:
            return self.cached_data

        self.last_modified = current_modified

        with open(self.conflicts_path, 'r', encoding='utf-8') as f:
            content = f.read()

        data = {
            "timestamp": datetime.now().isoformat(),
            "file_modified": datetime.fromtimestamp(current_modified).isoformat(),
            "critical_issues": [],
            "major_issues": [],
            "minor_issues": [],
            "resolved_issues": [],
            "activity_log": [],
            "roadmap": {
                "immediate": [],
                "short_term": [],
                "medium_term": [],
                "long_term": []
            },
            "stats": {
                "critical_count": 0,
                "major_count": 0,
                "minor_count": 0,
                "resolved_count": 0,
                "health_score": 45
            }
        }

        # Parse sections
        sections = content.split('##')

        for section in sections:
            if 'Critical Conflicts' in section:
                data["critical_issues"] = self._parse_issues(section)
            elif 'Major Conflicts' in section:
                data["major_issues"] = self._parse_issues(section)
            elif 'Minor Conflicts' in section:
                data["minor_issues"] = self._parse_issues(section)
            elif 'Fix Progress Log' in section:
                data["activity_log"] = self._parse_activity_log(section)
            elif 'Summary Statistics' in section:
                data["stats"] = self._parse_summary_stats(section)
            elif 'Priority Remediation Plan' in section:
                data["roadmap"] = self._parse_roadmap(section)

        # Count issues
        resolved_issues = []
        pending_critical = []
        pending_major = []
        pending_minor = []

        for issue in data["critical_issues"]:
            if issue["status"] == "resolved":
                resolved_issues.append(issue)
            else:
                pending_critical.append(issue)

        for issue in data["major_issues"]:
            if issue["status"] == "resolved":
                resolved_issues.append(issue)
            else:
                pending_major.append(issue)

        for issue in data["minor_issues"]:
            if issue["status"] == "resolved":
                resolved_issues.append(issue)
            else:
                pending_minor.append(issue)

        data["resolved_issues"] = resolved_issues
        data["stats"]["critical_count"] = len(pending_critical)
        data["stats"]["major_count"] = len(pending_major)
        data["stats"]["minor_count"] = len(pending_minor)
        data["stats"]["resolved_count"] = len(resolved_issues)

        self.cached_data = data
        return data

    def _parse_issues(self, section_content: str) -> List[Dict[str, Any]]:
        """Parse issues from a section."""
        issues = []

        # Find all issue blocks
        issue_blocks = re.findall(r'###\s*(.*?)\n(.*?)(?=###|\n##|\Z)', section_content, re.DOTALL)

        for title, content in issue_blocks:
            issue = {
                "title": title.strip(),
                "status": "resolved" if "✅" in title or "RESOLVED" in title else "pending",
                "timestamp": None,
                "description": "",
                "verification": ""
            }

            # Extract timestamp
            timestamp_match = re.search(r'Timestamp:\*\*\s*([\d-T:Z\s]+)', content)
            if timestamp_match:
                issue["timestamp"] = timestamp_match.group(1).strip()

            # Extract description
            desc_match = re.search(r'Issue:\*\*\s*(.*?)(?:\n|$)', content)
            if desc_match:
                issue["description"] = desc_match.group(1).strip()

            # Extract verification
            verif_match = re.search(r'Verification:\*\*\s*(.*?)(?:\n|$)', content)
            if verif_match:
                issue["verification"] = verif_match.group(1).strip()

            issues.append(issue)

        return issues

    def _parse_activity_log(self, section_content: str) -> List[Dict[str, Any]]:
        """Parse the activity log entries."""
        entries = []

        # Find log entries with timestamp pattern
        log_entries = re.findall(r'- ([\d\-T:.Z\s]+)\s+([a-zA-Z\-]+)\s+(.*)', section_content)

        for timestamp, agent, action in log_entries[-10:]:  # Last 10 entries
            entries.append({
                "timestamp": timestamp.strip(),
                "agent": agent.strip(),
                "action": action.strip()
            })

        return entries

    def _parse_summary_stats(self, section_content: str) -> Dict[str, Any]:
        """Parse summary statistics."""
        stats = {
            "critical_count": 3,
            "major_count": 2,
            "minor_count": 7,
            "resolved_count": 7,
            "health_score": 65,
            "total_issues": 19,
            "progress_percentage": 58
        }

        # Extract health score
        health_match = re.search(r'Overall Health Score:\s*(\d+)/100', section_content)
        if health_match:
            stats["health_score"] = int(health_match.group(1))

        # Extract issue counts - more flexible patterns
        major_match = re.search(r'Major Issues:\s*\d+\s*→\s*\*\*(\d+)\s*remaining', section_content)
        if major_match:
            stats["major_count"] = int(major_match.group(1))

        minor_match = re.search(r'Minor Issues:\s*\d+\s*→\s*\*\*(\d+)\s*remaining', section_content)
        if minor_match:
            stats["minor_count"] = int(minor_match.group(1))

        # Extract critical issues
        critical_match = re.search(r'Critical Issues:\s*(\d+)', section_content)
        if critical_match:
            stats["critical_count"] = int(critical_match.group(1))

        # Calculate total and progress
        total = stats["critical_count"] + stats["major_count"] + stats["minor_count"] + stats["resolved_count"]
        stats["total_issues"] = total
        if total > 0:
            stats["progress_percentage"] = round((stats["resolved_count"] / total) * 100)

        return stats

    def _parse_roadmap(self, section_content: str) -> Dict[str, List[Dict]]:
        """Parse the priority remediation plan roadmap."""
        roadmap = {
            "immediate": [],
            "short_term": [],
            "medium_term": [],
            "long_term": []
        }

        # Parse different phases
        phases = {
            "immediate": r'### Immediate \(Week 1\)(.*?)(?=### |$)',
            "short_term": r'### Short-term \(Week 2-3\)(.*?)(?=### |$)',
            "medium_term": r'### Medium-term \(Month 1-2\)(.*?)(?=### |$)',
            "long_term": r'### Long-term \(Month 2-3\)(.*?)(?=### |$)'
        }

        for phase, pattern in phases.items():
            match = re.search(pattern, section_content, re.DOTALL)
            if match:
                items_text = match.group(1)
                items = re.findall(r'^\d+\.\s*(.*)$', items_text, re.MULTILINE)

                for item in items:
                    item = item.strip()
                    status = "completed" if "✅" in item else "pending"
                    title = re.sub(r'✅\s*|COMPLETED\s*-?\s*', '', item).strip()

                    roadmap[phase].append({
                        "title": title,
                        "status": status,
                        "completed": status == "completed"
                    })

        return roadmap

class ProgressServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.parser = ConflictsParser()
        self.server = None

    def create_handler(self):
        parser = self.parser

        class ProgressHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/api/progress':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    data = parser.parse_conflicts()
                    self.wfile.write(json.dumps(data, indent=2).encode())

                elif self.path == '/' or self.path == '/dashboard':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()

                    # Serve the dashboard HTML
                    dashboard_path = Path("progress-dashboard.html")
                    if dashboard_path.exists():
                        with open(dashboard_path, 'r') as f:
                            content = f.read()
                            # Inject real-time data fetching
                            content = content.replace(
                                'function refreshData() {',
                                '''function refreshData() {
                                    fetch('/api/progress')
                                        .then(response => response.json())
                                        .then(data => updateDashboard(data))
                                        .catch(error => console.error('Error:', error));

                                    function updateDashboard(data) {
                                        if (data.stats) {
                                            document.getElementById('critical-count').textContent = data.stats.critical_count;
                                            document.getElementById('major-count').textContent = data.stats.major_count;
                                            document.getElementById('minor-count').textContent = data.stats.minor_count;
                                            document.getElementById('resolved-count').textContent = data.stats.resolved_count;

                                            // Update health score
                                            const scoreCircle = document.querySelector('.score-circle');
                                            const scoreText = document.querySelector('.score-text');
                                            scoreCircle.style.setProperty('--score', data.stats.health_score);
                                            scoreText.textContent = data.stats.health_score + '/100';
                                        }

                                        // Update activity log
                                        if (data.activity_log) {
                                            const activityFeed = document.getElementById('activity-feed');
                                            activityFeed.innerHTML = data.activity_log.map(entry => `
                                                <div class="log-entry">
                                                    <div class="log-time">${entry.timestamp}</div>
                                                    <div class="log-agent">${entry.agent}</div>
                                                    <div class="log-action">${entry.action}</div>
                                                </div>
                                            `).join('');
                                        }

                                        // Update roadmap phases
                                        if (data.roadmap) {
                                            updateRoadmapPhase('immediate', data.roadmap.immediate, 'immediate-roadmap', 'immediate-progress');
                                            updateRoadmapPhase('short_term', data.roadmap.short_term, 'short-term-roadmap', 'short-term-progress');
                                            updateRoadmapPhase('medium_term', data.roadmap.medium_term, 'medium-term-roadmap', 'medium-term-progress');
                                            updateRoadmapPhase('long_term', data.roadmap.long_term, 'long-term-roadmap', 'long-term-progress');
                                        }
                                    }

                                    function updateRoadmapPhase(phaseName, phaseData, containerId, progressId) {
                                        if (!phaseData || !Array.isArray(phaseData)) return;

                                        const container = document.getElementById(containerId);
                                        const progressBar = document.getElementById(progressId);

                                        if (container) {
                                            container.innerHTML = phaseData.map(item => `
                                                <div class="roadmap-item ${item.completed ? 'completed-item' : ''}">
                                                    <span class="roadmap-checkbox">${item.completed ? '✅' : '⏳'}</span>
                                                    <span class="roadmap-text">${item.title}</span>
                                                </div>
                                            `).join('');
                                        }

                                        if (progressBar && phaseData.length > 0) {
                                            const completed = phaseData.filter(item => item.completed).length;
                                            const percentage = Math.round((completed / phaseData.length) * 100);
                                            progressBar.style.width = percentage + '%';
                                        }
                                    }'''
                            )
                        self.wfile.write(content.encode())
                    else:
                        self.wfile.write(b'<h1>Dashboard HTML not found</h1>')
                else:
                    super().do_GET()

        return ProgressHandler

    def start(self):
        """Start the progress monitoring server."""
        handler = self.create_handler()
        self.server = HTTPServer(('localhost', self.port), handler)

        print(f"🚀 CASPER Progress Dashboard starting on http://localhost:{self.port}")
        print("📊 Access the dashboard at http://localhost:{}/dashboard".format(self.port))
        print("🔄 API endpoint available at http://localhost:{}/api/progress".format(self.port))
        print("Press Ctrl+C to stop...")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down progress monitor...")
            self.server.shutdown()

def main():
    """Main entry point."""
    print("🔧 CASPER Prime Progress Monitor")
    print("=" * 50)

    # Check if conflicts.md exists
    if not Path("conflicts.md").exists():
        print("❌ conflicts.md not found in current directory")
        print("Please run this script from the CASPER DEV root directory")
        return

    # Start the server
    server = ProgressServer(port=8080)
    server.start()

if __name__ == "__main__":
    main()