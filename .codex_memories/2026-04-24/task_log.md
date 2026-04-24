# Task Log - 2026-04-24

## Task: Improve CLI Applications

### Changes Made

#### 1. `phantom` (Docker Management CLI)
- **Added Docker auto-start**: New `start_docker()` and `ensure_docker()` helpers that attempt to start Docker Desktop on Windows/macOS or the Docker service on Linux before failing. Waits up to 60 seconds for the daemon to become available.
- **Fixed `cmd_exec`**: Removed `-it` (interactive TTY) flags for non-interactive scripted commands to avoid tty allocation errors. Added fallback from `sh` to `bash`.
- **Fixed `cmd_shell`**: Tries `bash` first, then `sh`, and handles exit codes properly (130 = Ctrl+D/C exit).
- **Fixed `cmd_restart`**: Now uses `docker compose restart <svc>` instead of raw `docker restart phantom-<svc>` for consistency with compose lifecycle.
- **Fixed `cmd_logs`**: Now captures output and prints it, with proper error handling if the container doesn't exist.
- **Added platform detection**: `_IS_WINDOWS`, `_IS_MACOS`, `_IS_LINUX` for OS-aware logic.
- **Improved pre-flight checks**: `ensure_docker()` is called for all commands except `config`, `version`, and `help`.

#### 2. `cli/main.py` (Agent Local CLI)
- **Fixed OS-friendly background process handling**: `cmd_start` now uses `subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW` on Windows, and `start_new_session=True` on Unix/Linux. Previously `start_new_session=True` would crash on Windows.
- **Fixed stdout/stderr pipe deadlock**: Redirected stdout/stderr/stdin to `os.devnull` instead of `subprocess.PIPE`. Previously the child could hang when buffers filled because no one was reading them.
- **Fixed `cmd_stop`**: Now uses `proc.terminate()` first, waits up to 5 seconds, then `proc.kill()` if needed. Previously it force-killed immediately.
- **Fixed `cmd_run` module name logic**: Accepts both `process` and `process_sensor` as input. Previously passing `process_sensor` would produce an invalid module name `_sensor`.
- **Fixed dependency check**: `python-dotenv` now checks for `dotenv` instead of the invalid `python_dotenv`.
- **Fixed `setup_config` template path**: Changed `Path(CLI_DIR.parent, "cli", ".env.template")` to `CLI_DIR / ".env.template"`.
- **Added Docker auto-start helper**: `_ensure_docker()` and `_start_docker()` available, invoked when `--docker` flag is passed to `start`/`stop`/`status`.
- **Improved exception handling**: Replaced bare `except:` with specific `except (psutil.NoSuchProcess, psutil.AccessDenied):` and other targeted catches.
- **Fixed `is_running`**: Handles `ValueError` and `OSError` when reading PID file.

### Bugs Fixed
1. `cli/main.py` `cmd_start` crashed on Windows due to Unix-only `start_new_session=True`.
2. `cli/main.py` `cmd_start` could deadlock due to unread stdout/stderr pipes.
3. `cli/main.py` `cmd_stop` force-killed processes instead of graceful terminate.
4. `cli/main.py` `cmd_run` broke when diagnostic name already ended with `_sensor`.
5. `cli/main.py` `check_dependencies` incorrectly tried to import `python_dotenv`.
6. `cli/main.py` `setup_config` looked for `.env.template` in the wrong directory.
7. `phantom` `cmd_exec` used `-it` flags which fail in non-interactive environments.
8. `phantom` `cmd_restart` bypassed docker compose lifecycle.
9. Both CLIs did not attempt to start Docker when it was stopped.

### Testing Notes
- Run `./phantom status` on Windows/Linux/macOS to verify Docker auto-start.
- Run `./agent start` on Windows to verify background process creation.
- Run `./agent run process_sensor` and `./agent run process` to verify module resolution.
- Run `./agent onboard` to verify dependency checks and path fixes.
