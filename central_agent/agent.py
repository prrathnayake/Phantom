"""Central Agent with single LLM analysis loop.

The central intelligence layer that analyzes diagnostic payloads
from the Gateway and generates security reports.
"""
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import config
from core import OpenRouterClient
from utils.debug_log import debug_logger

from central_agent.context import ContextManager, create_context_manager
from central_agent.memory import SessionMemory, create_session_memory


@dataclass
class AnalysisResult:
    """Container for analysis result."""
    session_id: str
    timestamp: str
    analysis: str
    recommendations: list[str] = field(default_factory=list)
    risk_level: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)


class CentralAgent:
    """Central Agent with single LLM analysis loop.
    
    Manages the complete analysis flow:
    1. Receive payload from Gateway
    2. Review context and memory
    3. Build prompt with context + memory + payload
    4. Call LLM for analysis
    5. Generate report to reports folder
    6. Update memory with findings
    
    Attributes:
        llm_client: OpenRouter client for LLM calls
        context_mgr: Session context manager
        memory: Session memory manager
        reports_dir: Directory for report storage
    """
    
    def __init__(
        self,
        llm_client: Optional[OpenRouterClient] = None,
        context_mgr: Optional[ContextManager] = None,
        memory: Optional[SessionMemory] = None,
        reports_dir: Optional[Path] = None
    ):
        self.llm_client = llm_client or OpenRouterClient()
        self.context_mgr = context_mgr or create_context_manager()
        self.memory = memory or create_session_memory()
        self.reports_dir = reports_dir or Path("central_agent") / "reports"
        
        self._lock = Lock()
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        debug_logger.info("CentralAgent initialized", {
            "reports_dir": str(self.reports_dir)
        })
    
    def analyze(
        self,
        payload: dict[str, Any],
        session_id: Optional[str] = None,
        trigger: str = "schedule"
    ) -> AnalysisResult:
        """Run analysis on diagnostic payload.
        
        Args:
            payload: Diagnostic payload from Gateway
            session_id: Optional session ID (created if not provided)
            trigger: What triggered this analysis (schedule/manual)
            
        Returns:
            AnalysisResult with analysis and metadata
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        debug_logger.info("Analysis started", {
            "session_id": session_id,
            "trigger": trigger
        })
        
        with self._lock:
            self.context_mgr.update_context(session_id, payload)
            
            session_context = self.context_mgr.get_session(session_id)
            
            if session_context is None:
                session_context = self.context_mgr.create_session(session_id)
            
            relevant_memory = self._fetch_relevant_memory(payload)
            
            prompt = self._build_prompt(
                payload=payload,
                context=session_context,
                memory=relevant_memory
            )
            
            analysis = self._call_llm(prompt)
            
            result = AnalysisResult(
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat(),
                analysis=analysis,
                metadata={
                    "trigger": trigger,
                    "payload_source": payload.get("source", "unknown"),
                    "memory_used": len(relevant_memory)
                }
            )
            
            self._extract_findings(result, analysis)
            self._update_memory(session_id, payload, result)
            
            report_path = self._generate_report(result, payload)
            
            debug_logger.info("Analysis complete", {
                "session_id": session_id,
                "report": str(report_path),
                "risk_level": result.risk_level
            })
            
            return result
    
    def analyze_and_wait(
        self,
        payloads: list[dict[str, Any]],
        session_id: Optional[str] = None
    ) -> AnalysisResult:
        """Analyze multiple payloads in sequence.
        
        Args:
            payloads: List of diagnostic payloads
            session_id: Optional session ID
            
        Returns:
            Combined AnalysisResult
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        combined_payload = {
            "source": "batch",
            "timestamp": datetime.utcnow().isoformat(),
            "payloads": payloads,
            "count": len(payloads)
        }
        
        return self.analyze(combined_payload, session_id=session_id)
    
    def get_report(
        self,
        session_id: str
    ) -> Optional[Path]:
        """Get report path for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Path to report file or None
        """
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        report_dir = self.reports_dir / date_str
        
        if not report_dir.exists():
            return None
        
        for f in report_dir.glob(f"report_{session_id}_*.md"):
            return f
        
        return None
    
    def get_recent_reports(
        self,
        count: int = 10
    ) -> list[Path]:
        """Get recent reports.
        
        Args:
            count: Number of reports to return
            
        Returns:
            List of report paths (newest first)
        """
        reports = []
        
        for date_dir in sorted(self.reports_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                reports.extend(date_dir.glob("report_*.md"))
        
        reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return reports[:count]
    
    def clear_session(self, session_id: str) -> None:
        """Clear session context and memory.
        
        Args:
            session_id: Session ID to clear
        """
        self.context_mgr._sessions.pop(session_id, None)
        self.memory.clear_session(session_id)
        
        debug_logger.info("Session cleared", {"session_id": session_id})
    
    def _build_prompt(
        self,
        payload: dict[str, Any],
        context: Any,
        memory: dict[str, Any]
    ) -> str:
        """Build analysis prompt from components."""
        lines = [
            "# Security Analysis Request",
            "",
            "## Session Context",
            f"- Session ID: {context.session_id}",
            f"- Payload Count: {len(context.payloads)}",
            f"- Previous Findings: {len(context.findings)}",
            "",
            "## Relevant Memory",
        ]
        
        if memory:
            for key, value in memory.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- No relevant memories found")
        
        lines.extend([
            "",
            "## Diagnostic Payload",
            f"```json\n{json.dumps(payload, indent=2)}\n```",
            "",
            "## Analysis Request",
            "Provide a security analysis including:",
            "1. Risk level (LOW/MEDIUM/HIGH/CRITICAL)",
            "2. Key findings",
            "3. Recommendations",
            "",
            "Respond in structured format."
        ])
        
        return "\n".join(lines)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        messages = [
            {"role": "system", "content": "You are a security analyst agent. Analyze diagnostic data and provide actionable insights in a structured format."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm_client.chat_completion(messages, max_tokens=512)
        
        if response is None:
            return "LLM analysis unavailable - check API configuration"
        
        return response
    
    def _fetch_relevant_memory(
        self,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Fetch relevant memories for payload."""
        source = payload.get("source", "")
        
        memories = {}
        
        if source:
            related = self.memory.search(source)
            for key, value in related[:3]:
                memories[key] = value
        
        recent = self.memory.get_recent(5)
        for key, value in recent:
            if key not in memories:
                memories[f"recent:{key}"] = value
        
        return memories
    
    def _extract_findings(
        self,
        result: AnalysisResult,
        analysis: str
    ) -> None:
        """Extract findings from analysis text."""
        result.analysis = analysis
        
        for line in analysis.lower().split("\n"):
            if "risk level:" in line or "risk:" in line:
                for level in ["critical", "high", "medium", "low"]:
                    if level in line:
                        result.risk_level = level.upper()
                        break
            
            if "recommend" in line:
                result.recommendations.append(line.strip())
    
    def _update_memory(
        self,
        session_id: str,
        payload: dict[str, Any],
        result: AnalysisResult
    ) -> None:
        """Update memory with findings."""
        self.memory.store(
            key=f"analysis:{session_id}",
            value=result.analysis,
            session_id=session_id,
            tags=["analysis", "result"]
        )
        
        self.memory.store(
            key=f"payload:{session_id}",
            value=payload,
            session_id=session_id,
            tags=["payload", payload.get("source", "unknown")]
        )
        
        source = payload.get("source", "unknown")
        self.memory.store(
            key=f"source:{source}",
            value={
                "last_session": session_id,
                "risk_level": result.risk_level,
                "timestamp": result.timestamp
            },
            session_id=None,
            tags=["source", source]
        )
    
    def _generate_report(
        self,
        result: AnalysisResult,
        payload: dict[str, Any]
    ) -> Path:
        """Write report to reports folder."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        report_dir = self.reports_dir / date_str
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = result.timestamp.replace(":", "-")
        report_path = report_dir / f"report_{result.session_id}_{timestamp}.md"
        
        content = [
            f"# Security Analysis Report",
            "",
            f"**Session ID**: {result.session_id}",
            f"**Timestamp**: {result.timestamp}",
            f"**Risk Level**: {result.risk_level}",
            f"**Trigger**: {result.metadata.get('trigger', 'unknown')}",
            "",
            "---",
            "",
            "## Analysis",
            "",
            result.analysis,
            "",
            "---",
            "",
            "## Raw Payload",
            "",
            f"```json\n{json.dumps(payload, indent=2)}\n```",
            "",
        ]
        
        if result.recommendations:
            content.extend([
                "## Recommendations",
                ""
            ])
            for rec in result.recommendations:
                content.append(f"- {rec}")
            content.append("")
        
        report_path.write_text("\n".join(content), encoding="utf-8")
        
        debug_logger.info("Report generated", {"path": str(report_path)})
        
        return report_path


def create_central_agent() -> CentralAgent:
    """Create CentralAgent with default settings.
    
    Returns:
        Configured CentralAgent instance
    """
    return CentralAgent(
        llm_client=OpenRouterClient(),
        context_mgr=create_context_manager(),
        memory=create_session_memory(),
        reports_dir=Path("central_agent") / "reports"
    )