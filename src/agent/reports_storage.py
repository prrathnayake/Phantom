"""Reports Storage for Agent.

Manages report storage, retrieval, organization, and rotation.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, List, Optional

from src.utils.debug_log import debug_logger


class ReportStorage:
    """Report storage and retrieval.
    
    Manages report organization by date, search,
    metadata indexing, and TTL-based rotation.
    
    Attributes:
        reports_dir: Root directory for reports
    """
    
    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = reports_dir or Path("src/agent") / "reports"
        self._lock = Lock()
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        debug_logger.info("ReportStorage initialized", {
            "reports_dir": str(self.reports_dir)
        })
    
    def save_report(
        self,
        session_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Path:
        """Save report to storage.
        
        Args:
            session_id: Session ID
            content: Report content
            metadata: Optional metadata
            
        Returns:
            Path to saved report
        """
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_dir = self.reports_dir / date_str
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"report_{session_id}_{timestamp}.md"
        report_path = report_dir / filename
        
        with self._lock:
            with report_path.open("w", encoding="utf-8") as f:
                f.write(content)
            
            if metadata:
                meta_path = report_dir / f"report_{session_id}_{timestamp}.json"
                with meta_path.open("w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
        
        debug_logger.info("Report saved", {
            "session_id": session_id,
            "path": str(report_path)
        })
        
        return report_path
    
    def get_report(self, session_id: str) -> Optional[Path]:
        """Get report path for session.
        
        Searches across all date directories and returns the
        most recent report if multiple exist.
        
        Args:
            session_id: Session ID
            
        Returns:
            Path to report or None
        """
        matches = []
        
        for date_dir in self.reports_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for f in date_dir.glob(f"report_{session_id}_*.md"):
                try:
                    matches.append((f, f.stat().st_mtime))
                except OSError:
                    continue
        
        if not matches:
            return None
        
        # Return the most recent match
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][0]
    
    def get_report_content(self, session_id: str) -> Optional[str]:
        """Get report content for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Report content or None
        """
        report_path = self.get_report(session_id)
        
        if report_path is None:
            return None
        
        try:
            return report_path.read_text(encoding="utf-8")
        except OSError:
            return None
    
    def get_recent_reports(
        self,
        count: int = 10,
        date: Optional[str] = None
    ) -> List[Path]:
        """Get recent reports.
        
        Args:
            count: Number of reports
            date: Optional date filter (YYYY-MM-DD)
            
        Returns:
            List of report paths
        """
        reports = []
        
        if date:
            date_dir = self.reports_dir / date
            if date_dir.is_dir():
                reports.extend(date_dir.glob("report_*.md"))
        else:
            for date_dir in sorted(self.reports_dir.iterdir(), reverse=True):
                if date_dir.is_dir():
                    reports.extend(date_dir.glob("report_*.md"))
        
        reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return reports[:count]
    
    def get_reports_by_date(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[Path]:
        """Get reports by date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of report paths
        """
        reports = []
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else start
        
        for date_dir in self.reports_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            except ValueError:
                continue
            
            if start <= dir_date <= end:
                reports.extend(date_dir.glob("report_*.md"))
        
        reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return reports
    
    def search_reports(self, query: str) -> List[Path]:
        """Search reports by content.
        
        Args:
            query: Search query
            
        Returns:
            Matching report paths
        """
        results = []
        query_lower = query.lower()
        
        for report_path in self.reports_dir.glob("**/*.md"):
            try:
                content = report_path.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    results.append(report_path)
            except Exception:
                continue
        
        return results
    
    def delete_report(self, session_id: str) -> bool:
        """Delete report for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted
        """
        report_path = self.get_report(session_id)
        
        if report_path is None:
            return False
        
        with self._lock:
            try:
                report_path.unlink()
            except OSError:
                pass
            
            json_path = report_path.with_suffix(".json")
            if json_path.exists():
                try:
                    json_path.unlink()
                except OSError:
                    pass
        
        debug_logger.info("Report deleted", {"session_id": session_id})
        
        return True
    
    def get_report_count(self) -> int:
        """Get total report count."""
        return len(list(self.reports_dir.glob("**/*.md")))
    
    def get_date_directories(self) -> List[str]:
        """Get list of date directories.
        
        Returns:
            List of date strings (YYYY-MM-DD)
        """
        dates = []
        
        for date_dir in self.reports_dir.iterdir():
            if date_dir.is_dir():
                try:
                    datetime.strptime(date_dir.name, "%Y-%m-%d")
                    dates.append(date_dir.name)
                except ValueError:
                    continue
        
        return sorted(dates, reverse=True)
    
    def rotate_reports(
        self,
        max_age_days: Optional[int] = None,
        max_count: Optional[int] = None
    ) -> int:
        """Rotate old reports based on age or count.
        
        Args:
            max_age_days: Delete reports older than this many days
            max_count: Keep only the most recent N reports
            
        Returns:
            Number of reports deleted
        """
        deleted = 0
        
        with self._lock:
            all_reports = list(self.reports_dir.glob("**/*.md"))
            all_reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max_age_days) if max_age_days is not None else None
        
        for idx, report_path in enumerate(all_reports):
            should_delete = False
            
            try:
                mtime = datetime.fromtimestamp(report_path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            
            if cutoff is not None and mtime < cutoff:
                should_delete = True
            
            if max_count is not None and idx >= max_count:
                should_delete = True
                
                if should_delete:
                    try:
                        report_path.unlink()
                        json_path = report_path.with_suffix(".json")
                        if json_path.exists():
                            json_path.unlink()
                        deleted += 1
                    except OSError:
                        continue
            
            # Clean up empty date directories
            for date_dir in self.reports_dir.iterdir():
                if date_dir.is_dir() and not any(date_dir.iterdir()):
                    try:
                        date_dir.rmdir()
                    except OSError:
                        pass
        
        if deleted:
            debug_logger.info("Reports rotated", {
                "deleted": deleted,
                "max_age_days": max_age_days,
                "max_count": max_count
            })
        
        return deleted


def create_report_storage(reports_dir: Optional[Path] = None) -> ReportStorage:
    """Create ReportStorage with default settings.
    
    Returns:
        Configured ReportStorage instance
    """
    return ReportStorage(
        reports_dir=reports_dir or Path("src/agent") / "reports"
    )
