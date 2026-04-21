"""Central Agent with Skills and Tools.

The central intelligence layer that analyzes diagnostic payloads
from the Gateway and generates security reports. Supports skills
and tools for advanced autonomous operations.
"""
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import config
from src.core import OpenRouterClient
from src.core.tools import get_tool_registry, get_tool_executor
from src.utils.debug_log import debug_logger

from central_agent.context import ContextManager, create_context_manager
from central_agent.memory import SessionMemory, create_session_memory
from central_agent.skills import (
    get_skill_registry,
    SkillCategory,
    SkillStatus,
)


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
    """Central Agent with Skills and Tools.
    
    Manages the complete analysis flow:
    1. Receive payload from Gateway
    2. Review context and memory
    3. Execute relevant skills based on payload
    4. Build prompt with context + memory + skills + payload
    5. Call LLM for analysis
    6. Optionally execute tools for remediation
    7. Generate report to reports folder
    8. Update memory with findings
    
    Attributes:
        llm_client: OpenRouter client for LLM calls
        context_mgr: Session context manager
        memory: Session memory manager
        skill_registry: Registry for skill management
        tool_executor: Executor for tool execution
        reports_dir: Directory for report storage
    """
    
    def __init__(
        self,
        llm_client: Optional[OpenRouterClient] = None,
        context_mgr: Optional[ContextManager] = None,
        memory: Optional[SessionMemory] = None,
        reports_dir: Optional[Path] = None,
        skill_registry: Optional[Any] = None,
        tool_executor: Optional[Any] = None
    ):
        self.llm_client = llm_client or OpenRouterClient()
        self.context_mgr = context_mgr or create_context_manager()
        self.memory = memory or create_session_memory()
        self.reports_dir = reports_dir or Path("central_agent") / "reports"
        
        self.skill_registry = skill_registry or get_skill_registry()
        self.tool_executor = tool_executor or get_tool_executor()
        
        self._lock = Lock()
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self._register_skills()
        
        debug_logger.info("CentralAgent initialized", {
            "reports_dir": str(self.reports_dir),
            "skills": len(self.skill_registry.list_skills()),
            "tools": len(self.tool_executor._registry.list_tools())
        })
    
    def _register_skills(self) -> None:
        """Register all available skills."""
        from central_agent.skills.network_analysis import NetworkAnalysisSkill
        from central_agent.skills.process_analysis import ProcessAnalysisSkill
        from central_agent.skills.memory_analysis import MemoryAnalysisSkill
        from central_agent.skills.port_analysis import PortAnalysisSkill
        from central_agent.skills.log_analysis import LogAnalysisSkill
        from central_agent.skills.security_analysis import SecurityAnalysisSkill
        from central_agent.skills.system_diagnostics import SystemDiagnosticsSkill
        
        skills = [
            NetworkAnalysisSkill(),
            ProcessAnalysisSkill(),
            MemoryAnalysisSkill(),
            PortAnalysisSkill(),
            LogAnalysisSkill(),
            SecurityAnalysisSkill(),
            SystemDiagnosticsSkill(),
        ]
        
        for skill in skills:
            self.skill_registry.register_loader(skill.name, lambda s=skill: s)
    
    def analyze(
        self,
        payload: dict[str, Any],
        session_id: Optional[str] = None,
        trigger: str = "schedule",
        execute_skills: bool = True,
        execute_tools: bool = False
    ) -> AnalysisResult:
        """Run analysis on diagnostic payload.
        
        Args:
            payload: Diagnostic payload from Gateway
            session_id: Optional session ID (created if not provided)
            trigger: What triggered this analysis (schedule/manual)
            execute_skills: Whether to execute relevant skills
            execute_tools: Whether to execute tools for remediation
            
        Returns:
            AnalysisResult with analysis and metadata
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        debug_logger.info("Analysis started", {
            "session_id": session_id,
            "trigger": trigger,
            "execute_skills": execute_skills
        })
        
        with self._lock:
            self.context_mgr.update_context(session_id, payload)
            
            session_context = self.context_mgr.get_session(session_id)
            
            if session_context is None:
                session_context = self.context_mgr.create_session(session_id)
            
            relevant_memory = self._fetch_relevant_memory(payload)
            
            skill_results = {}
            if execute_skills:
                skill_results = self._execute_relevant_skills(payload)
            
            tool_results = {}
            if execute_tools:
                tool_results = self._execute_relevant_tools(payload)
            
            prompt = self._build_prompt(
                payload=payload,
                context=session_context,
                memory=relevant_memory,
                skill_results=skill_results,
                tool_results=tool_results
            )
            
            analysis = self._call_llm(prompt)
            
            result = AnalysisResult(
                session_id=session_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis=analysis,
                metadata={
                    "trigger": trigger,
                    "payload_source": payload.get("source", "unknown"),
                    "memory_used": len(relevant_memory),
                    "skills_executed": len(skill_results),
                    "tools_executed": len(tool_results)
                }
            )
            
            self._extract_findings(result, analysis)
            self._update_memory(session_id, payload, result, skill_results, tool_results)
            
            report_path = self._generate_report(result, payload, skill_results, tool_results)
            
            debug_logger.info("Analysis complete", {
                "session_id": session_id,
                "report": str(report_path),
                "risk_level": result.risk_level,
                "skills_used": list(skill_results.keys()),
                "tools_used": list(tool_results.keys())
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
        memory: dict[str, Any],
        skill_results: dict[str, Any] = None,
        tool_results: dict[str, Any] = None
    ) -> str:
        """Build analysis prompt from components."""
        skill_results = skill_results or {}
        tool_results = tool_results or {}
        
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
        
        if skill_results:
            lines.extend([
                "",
                "## Skill Execution Results",
            ])
            for skill_name, result in skill_results.items():
                status = result.get("status", "unknown")
                output = result.get("output", {})
                lines.append(f"### {skill_name} ({status})")
                if isinstance(output, dict):
                    for k, v in output.items():
                        if k not in ["status"]:
                            lines.append(f"- {k}: {str(v)[:200]}")
                lines.append("")
        
        if tool_results:
            lines.extend([
                "",
                "## Tool Execution Results",
            ])
            for tool_name, result in tool_results.items():
                status = result.get("status", "unknown")
                output = result.get("output", {})
                lines.append(f"### {tool_name} ({status})")
                if isinstance(output, dict):
                    for k, v in output.items():
                        lines.append(f"- {k}: {str(v)[:200]}")
                lines.append("")
        
        lines.extend([
            "",
            "## Diagnostic Payload",
            f"```json\n{json.dumps(payload, indent=2)}\n```",
            "",
            "## Available Tools",
            "You may request execution of these tools for remediation:",
            "- shell: Execute shell commands",
            "- file: File operations (read, write, list, search)",
            "- process: Process management (list, kill, info)",
            "- diagnostic: Run diagnostic collectors",
            "",
            "## Analysis Request",
            "Provide a security analysis including:",
            "1. Risk level (LOW/MEDIUM/HIGH/CRITICAL)",
            "2. Key findings",
            "3. Recommendations",
            "4. Any tools that should be executed for remediation",
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
    
    def _execute_relevant_skills(
        self,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute relevant skills based on payload."""
        results = {}
        
        source = payload.get("source", "")
        
        skill_map = {
            "network": ["network_analysis"],
            "process": ["process_analysis"],
            "memory": ["memory_analysis"],
            "port": ["port_analysis"],
            "service": ["security_analysis"],
            "system": ["system_diagnostics"],
            "security": ["security_analysis", "log_analysis"],
            "diagnostic": ["network_analysis", "process_analysis", "memory_analysis", "system_diagnostics"],
        }
        
        skills_to_run = skill_map.get(source, ["security_analysis", "system_diagnostics"])
        
        if not source:
            skills_to_run = ["network_analysis", "process_analysis", "memory_analysis", "port_analysis"]
        
        context = {"payload": payload, "source": source}
        
        for skill_name in skills_to_run:
            try:
                result = self.skill_registry.execute(skill_name, context)
                
                results[skill_name] = {
                    "status": result.status.value if result.status else "unknown",
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                }
                
                debug_logger.info("Skill executed", {
                    "skill": skill_name,
                    "status": result.status.value if result.status else "unknown"
                })
            except Exception as e:
                debug_logger.error("Skill execution failed", {
                    "skill": skill_name,
                    "error": str(e)
                })
                results[skill_name] = {
                    "status": "failed",
                    "error": str(e),
                }
        
        return results
    
    def _execute_relevant_tools(
        self,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute relevant tools based on payload."""
        results = {}
        
        tool_params = payload.get("tool_requests", [])
        
        if not tool_params:
            return results
        
        for request in tool_params:
            tool_name = request.get("tool")
            params = request.get("params", {})
            
            if not tool_name:
                continue
            
            try:
                result = self.tool_executor.execute(tool_name, params)
                
                results[tool_name] = {
                    "status": result.status.value if result.status else "unknown",
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                }
                
                debug_logger.info("Tool executed", {
                    "tool": tool_name,
                    "status": result.status.value if result.status else "unknown"
                })
            except Exception as e:
                debug_logger.error("Tool execution failed", {
                    "tool": tool_name,
                    "error": str(e)
                })
                results[tool_name] = {
                    "status": "failed",
                    "error": str(e),
                }
        
        return results
    
    def get_available_skills(self) -> list[dict[str, Any]]:
        """Get list of available skills."""
        skills = self.skill_registry.list_skills()
        return [s.to_dict() for s in skills]
    
    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools."""
        tools = self.tool_executor._registry.list_tools()
        return [t.__dict__ if hasattr(t, '__dict__') else {"name": t.name} for t in tools]
    
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
        result: AnalysisResult,
        skill_results: dict[str, Any] = None,
        tool_results: dict[str, Any] = None
    ) -> None:
        """Update memory with findings."""
        skill_results = skill_results or {}
        tool_results = tool_results or {}
        
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
        
        if skill_results:
            self.memory.store(
                key=f"skills:{session_id}",
                value=skill_results,
                session_id=session_id,
                tags=["skills", "execution"]
            )
        
        if tool_results:
            self.memory.store(
                key=f"tools:{session_id}",
                value=tool_results,
                session_id=session_id,
                tags=["tools", "execution"]
            )
        
        source = payload.get("source", "unknown")
        self.memory.store(
            key=f"source:{source}",
            value={
                "last_session": session_id,
                "risk_level": result.risk_level,
                "timestamp": result.timestamp,
                "skills_used": list(skill_results.keys()),
                "tools_used": list(tool_results.keys())
            },
            session_id=None,
            tags=["source", source]
        )
    
    def _generate_report(
        self,
        result: AnalysisResult,
        payload: dict[str, Any],
        skill_results: dict[str, Any] = None,
        tool_results: dict[str, Any] = None
    ) -> Path:
        """Write report to reports folder."""
        skill_results = skill_results or {}
        tool_results = tool_results or {}
        
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
            f"**Skills Executed**: {len(skill_results)}",
            f"**Tools Executed**: {len(tool_results)}",
            "",
            "---",
            "",
            "## Analysis",
            "",
            result.analysis,
            "",
        ]
        
        if skill_results:
            content.extend([
                "---",
                "",
                "## Skill Execution Results",
                ""
            ])
            for skill_name, sr in skill_results.items():
                content.append(f"### {skill_name}")
                content.append(f"- Status: {sr.get('status', 'unknown')}")
                if sr.get("error"):
                    content.append(f"- Error: {sr.get('error')}")
                content.append("")
        
        if tool_results:
            content.extend([
                "---",
                "",
                "## Tool Execution Results",
                ""
            ])
            for tool_name, tr in tool_results.items():
                content.append(f"### {tool_name}")
                content.append(f"- Status: {tr.get('status', 'unknown')}")
                if tr.get("error"):
                    content.append(f"- Error: {tr.get('error')}")
                content.append("")
        
        content.extend([
            "---",
            "",
            "## Raw Payload",
            "",
            f"```json\n{json.dumps(payload, indent=2)}\n```",
            "",
        ])
        
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
