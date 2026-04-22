"""CLI Handler for Gateway.

Provides command-line interface for local operations.
"""
import sys
from typing import Any, Dict, List, Optional

from src.utils.debug_log import debug_logger


class CLIHandler:
    """CLI handler for Gateway operations.
    
    Provides commands:
    - status: Show gateway status
    - schedules: List/manage schedules
    - run: Run schedules manually
    - analyze: Trigger analysis
    - reports: View reports
    
    Attributes:
        schedule_manager: ScheduleManager instance
        agent: Agent instance
    """
    
    def __init__(
        self,
        schedule_manager: Optional[Any] = None,
        agent: Optional[Any] = None
    ):
        self.schedule_manager = schedule_manager
        self.agent = agent
        
        debug_logger.info("CLIHandler initialized")
    
    def run_command(
        self,
        args: List[str]
    ) -> int:
        """Run CLI command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        if not args:
            self._print_usage()
            return 0
        
        command = args[0]
        
        if command == "status":
            return self._cmd_status()
        elif command == "schedules":
            return self._cmd_schedules(args[1:])
        elif command == "run":
            return self._cmd_run(args[1:])
        elif command == "analyze":
            return self._cmd_analyze(args[1:])
        elif command == "reports":
            return self._cmd_reports(args[1:])
        elif command in ("-h", "--help"):
            self._print_usage()
            return 0
        else:
            print(f"Unknown command: {command}")
            self._print_usage()
            return 1
    
    def _print_usage(self) -> None:
        """Print usage information."""
        print(""" Gateway CLI Commands:
    
    status              Show gateway status
    schedules           List all schedules
    schedules enable <name>   Enable schedule
    schedules disable <name> Disable schedule
    run <name>          Run specific schedule
    run all             Run all due schedules
    analyze <payload>   Trigger analysis
    reports             List recent reports
    reports <session>  View specific report
    help                Show this help
        """)
    
    def _cmd_status(self) -> int:
        """Show gateway status."""
        print("\n=== Gateway Status ===\n")
        
        if self.schedule_manager:
            schedules = self.schedule_manager.get_all_schedules()
            print(f"Schedules: {len(schedules)}")
            for name, info in schedules.items():
                status = "enabled" if info.get("enabled") else "disabled"
                print(f"  - {name}: {status}")
        else:
            print("ScheduleManager: Not configured")
        
        if self.agent:
            report_count = len(self.agent.get_recent_reports())
            print(f"Reports: {report_count}")
        else:
            print("Agent: Not configured")
        
        print()
        return 0
    
    def _cmd_schedules(self, args: List[str]) -> int:
        """Manage schedules."""
        if not args or args[0] in ("list", "ls"):
            return self._list_schedules()
        elif args[0] == "enable" and len(args) > 1:
            return self._enable_schedule(args[1])
        elif args[0] == "disable" and len(args) > 1:
            return self._disable_schedule(args[1])
        else:
            print("Usage: schedules [list|enable <name>|disable <name>]")
            return 1
    
    def _list_schedules(self) -> int:
        """List all schedules."""
        if not self.schedule_manager:
            print("ScheduleManager not configured")
            return 1
        
        schedules = self.schedule_manager.get_all_schedules()
        
        if not schedules:
            print("No schedules configured")
            return 0
        
        print(f"\nSchedules ({len(schedules)}):\n")
        for name, info in schedules.items():
            status = "enabled" if info.get("enabled") else "disabled"
            interval = info.get("interval", 0)
            next_run = info.get("next_run", "N/A")
            print(f"  {name}: {status} (interval: {interval}s, next: {next_run})")
        
        print()
        return 0
    
    def _enable_schedule(self, name: str) -> int:
        """Enable schedule."""
        if not self.schedule_manager:
            print("ScheduleManager not configured")
            return 1
        
        if self.schedule_manager.enable_schedule(name):
            print(f"Enabled: {name}")
            return 0
        else:
            print(f"Schedule not found: {name}")
            return 1
    
    def _disable_schedule(self, name: str) -> int:
        """Disable schedule."""
        if not self.schedule_manager:
            print("ScheduleManager not configured")
            return 1
        
        if self.schedule_manager.disable_schedule(name):
            print(f"Disabled: {name}")
            return 0
        else:
            print(f"Schedule not found: {name}")
            return 1
    
    def _cmd_run(self, args: List[str]) -> int:
        """Run schedules."""
        if not args:
            print("Usage: run <name>|all")
            return 1
        
        if not self.schedule_manager:
            print("ScheduleManager not configured")
            return 1
        
        if args[0] == "all":
            results = self.schedule_manager.run_all_due()
            print(f"Run complete: {len(results)} schedules executed")
            return 0
        
        name = args[0]
        result = self.schedule_manager.run_schedule(name)
        
        if result:
            print(f"Completed: {name}")
            return 0
        else:
            print(f"Failed: {name}")
            return 1
    
    def _cmd_analyze(self, args: List[str]) -> int:
        """Trigger analysis."""
        if not self.agent:
            print("Agent not configured")
            return 1
        
        payload = {
            "source": "cli",
            "data": args if args else {}
        }
        
        result = self.agent.analyze(
            payload=payload,
            trigger="cli"
        )
        
        print(f"\nAnalysis complete:")
        print(f"  Session: {result.session_id}")
        print(f"  Risk: {result.risk_level}")
        print(f"  Report: {result.session_id}\n")
        
        return 0
    
    def _cmd_reports(self, args: List[str]) -> int:
        """Manage reports."""
        if not self.agent:
            print("Agent not configured")
            return 1
        
        if not args:
            return self._list_reports()
        
        session_id = args[0]
        return self._view_report(session_id)
    
    def _list_reports(self) -> int:
        """List recent reports."""
        reports = self.agent.get_recent_reports()
        
        if not reports:
            print("No reports found")
            return 0
        
        print(f"\nRecent Reports ({len(reports)}):\n")
        for report in reports:
            print(f"  - {report.name}")
        
        print()
        return 0
    
    def _view_report(self, session_id: str) -> int:
        """View specific report."""
        report_path = self.agent.get_report(session_id)
        
        if not report_path:
            print(f"Report not found: {session_id}")
            return 1
        
        print(f"\n{'='*50}")
        print(report_path.read_text())
        print(f"{'='*50}\n")
        
        return 0


def create_cli_handler(
    schedule_manager: Optional[Any] = None,
    agent: Optional[Any] = None
) -> CLIHandler:
    """Create CLI handler.
    
    Returns:
        Configured CLIHandler instance
    """
    return CLIHandler(
        schedule_manager=schedule_manager,
        agent=agent
    )
