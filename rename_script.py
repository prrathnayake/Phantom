import os
import re
from pathlib import Path

ROOT = Path("C:/Users/cybor/Desktop/Phantom")

# Patterns to replace in all text files
REPLACEMENTS = [
    # Import paths
    (r"from src\.central_agent", "from src.agent"),
    (r"import src\.central_agent", "import src.agent"),
    (r"from central_agent", "from agent"),
    (r"import central_agent", "import agent"),
    
    # Path references
    (r'Path\("central_agent"\)', 'Path("agent")'),
    (r"Path\('central_agent'\)", "Path('agent')"),
    (r'Path\("central_agent/reports"\)', 'Path("agent/reports")'),
    (r"Path\('central_agent/reports'\)", "Path('agent/reports')"),
    
    # Directory references in strings/comments
    (r"central_agent/reports", "agent/reports"),
    (r"central_agent/reports/", "agent/reports/"),
    
    # Class and function names
    (r"\bCentralAgent\b", "Agent"),
    (r"\bcreate_central_agent\b", "create_agent"),
    
    # Docstrings and comments - "Central Agent" → "Agent"
    (r"Central Agent", "Agent"),
    (r"central agent", "agent"),
    
    # Test file names will be handled separately
]

# Files to skip
SKIP_FILES = {
    "rename_script.py",  # this script
}

# Extensions to process
EXTENSIONS = {".py", ".md", ".html", ".txt", ".cfg", ".ini", ".yml", ".yaml", ".json", ".toml"}


def should_process(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    if path.suffix.lower() not in EXTENSIONS:
        return False
    # Skip pycache
    if "__pycache__" in path.parts:
        return False
    return True


def process_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  SKIP (read error): {path} - {e}")
        return
    
    original = text
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    
    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"  UPDATED: {path.relative_to(ROOT)}")


def main():
    for path in ROOT.rglob("*"):
        if path.is_file() and should_process(path):
            process_file(path)


if __name__ == "__main__":
    main()
