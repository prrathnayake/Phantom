import sys
import os

import config
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class DebugLogger:
    def __init__(self):
        self.enabled = config.DEBUG_MODE
        self.debug_file = config.LOG_DIR / "debug.log"
        if self.enabled:
            config.ensure_log_dir()

    def log(self, category: str, message: str, data: Dict[str, Any] = None) -> None:
        if not self.enabled:
            return
        
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "message": message,
            "data": data or {},
        }
        try:
            with self.debug_file.open("a", encoding="utf-8") as f:
                f.write(f"[DEBUG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | {category} | {message}")
                if data:
                    import json
                    f.write(f" | {json.dumps(data)}")
                f.write("\n")
        except Exception as e:
            print(f"Debug log write failed: {e}")

    def info(self, message: str, data: Dict[str, Any] = None) -> None:
        self.log("INFO", message, data)

    def error(self, message: str, data: Dict[str, Any] = None) -> None:
        self.log("ERROR", message, data)

    def warning(self, message: str, data: Dict[str, Any] = None) -> None:
        self.log("WARNING", message, data)

    def sensor(self, sensor_name: str, message: str, data: Dict[str, Any] = None) -> None:
        self.log(f"SENSOR:{sensor_name}", message, data)

    def task(self, task_name: str, message: str, data: Dict[str, Any] = None) -> None:
        self.log(f"TASK:{task_name}", message, data)

    def detection(self, rule: str, message: str, data: Dict[str, Any] = None) -> None:
        self.log(f"DETECTION:{rule}", message, data)


debug_logger = DebugLogger()
