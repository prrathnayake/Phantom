"""File Trigger for Gateway.

Provides drop folder monitoring for file-based triggers.
"""
import json
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Callable, Dict, Optional

from src.utils.debug_log import debug_logger


class FileTrigger:
    """File-based trigger for Gateway.
    
    Monitors a drop folder for new files and triggers
    analysis when files are detected.
    
    Attributes:
        watch_path: Path to watch for new files
        agent: Agent instance
        file_extensions: Extensions to monitor
        poll_interval: Check interval in seconds
    """
    
    def __init__(
        self,
        watch_path: Optional[Path] = None,
        agent: Optional[Any] = None,
        file_extensions: Optional[list] = None,
        poll_interval: int = 5
    ):
        import config
        self.watch_path = watch_path or config.LOG_DIR / "triggers"
        self.agent = agent
        self.file_extensions = file_extensions or [".json", ".txt", ".log"]
        self.poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._seen_files: set = set()
        self._scan_lock = Lock()
        
        self.watch_path.mkdir(parents=True, exist_ok=True)
        
        debug_logger.info("FileTrigger initialized", {
            "watch_path": str(self.watch_path),
            "extensions": self.file_extensions
        })
    
    def start(self) -> None:
        """Start monitoring drop folder."""
        self._running = True
        self._scan_initial()
        
        self._thread = Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        debug_logger.info("FileTrigger started", {
            "path": str(self.watch_path)
        })
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        
        debug_logger.info("FileTrigger stopped")
    
    def _scan_initial(self) -> None:
        """Scan for existing files on start."""
        with self._scan_lock:
            for f in self.watch_path.iterdir():
                if f.is_file():
                    self._seen_files.add(f.name)
    
    def _monitor_loop(self) -> None:
        """Monitor loop."""
        while self._running:
            try:
                self._check_for_new_files()
            except Exception as e:
                debug_logger.error("Monitor error", {"error": str(e)})
            
            time.sleep(self.poll_interval)
    
    def _check_for_new_files(self) -> None:
        """Check for new files in watch folder."""
        new_files = []
        with self._scan_lock:
            for f in self.watch_path.iterdir():
                if not f.is_file():
                    continue
                
                if f.name in self._seen_files:
                    continue
                
                if f.suffix not in self.file_extensions:
                    continue
                
                self._seen_files.add(f.name)
                new_files.append(f)
        
        for f in new_files:
            self._process_file(f)
    
    def _process_file(self, file_path: Path) -> None:
        """Process triggered file."""
        session_id = str(uuid.uuid4())
        
        debug_logger.info("Processing trigger file", {
            "session_id": session_id,
            "file": file_path.name
        })
        
        try:
            if file_path.suffix == ".json":
                with file_path.open() as fp:
                    payload = json.load(fp)
            else:
                content = file_path.read_text()
                payload = {
                    "source": "file_trigger",
                    "filename": file_path.name,
                    "content": content
                }
            
            if self.agent:
                result = self.agent.analyze(
                    payload=payload,
                    session_id=session_id,
                    trigger="file"
                )
                
                debug_logger.info("Analysis complete", {
                    "session_id": session_id,
                    "risk_level": result.risk_level
                })
            
            self._archive_file(file_path)
        
        except Exception as e:
            debug_logger.error("File processing error", {
                "file": file_path.name,
                "error": str(e)
            })
    
    def _archive_file(self, file_path: Path) -> None:
        """Archive processed file."""
        try:
            archive_dir = self.watch_path / "processed"
            archive_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            
            file_path.rename(archive_dir / new_name)
            
            debug_logger.info("File archived", {
                "original": file_path.name,
                "archived": new_name
            })
        
        except Exception as e:
            debug_logger.error("Archive failed", {"error": str(e)})
    
    def add_file(self, payload: Dict[str, Any], filename: str) -> Path:
        """Add trigger file to watch folder.
        
        Args:
            payload: Payload data
            filename: Filename to use
            
        Returns:
            Path to created file
        """
        file_path = self.watch_path / filename
        
        with file_path.open("w") as fp:
            json.dump(payload, fp, indent=2)
        
        debug_logger.info("Trigger file added", {
            "file": filename
        })
        
        return file_path


def create_file_trigger(
    watch_path: Optional[Path] = None,
    central_agent: Optional[Any] = None
) -> FileTrigger:
    """Create file trigger.
    
    Returns:
        Configured FileTrigger instance
    """
    return FileTrigger(
        watch_path=watch_path,
        agent=agent
    )
