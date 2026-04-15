"""Test the monitoring agent to find bugs and issues."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test all imports work correctly."""
    print("Testing imports...")
    try:
        import config
        print("  config: OK")
    except Exception as e:
        print(f"  config: FAILED - {e}")
        return False
    
    try:
        from core import Scheduler, Storage, OpenRouterClient
        print("  core: OK")
    except Exception as e:
        print(f"  core: FAILED - {e}")
        return False
    
    try:
        from analysis import detection
        print("  analysis: OK")
    except Exception as e:
        print(f"  analysis: FAILED - {e}")
        return False
    
    try:
        from sensors import file_sensor, process_sensor, port_sensor
        print("  sensors: OK")
    except Exception as e:
        print(f"  sensors: FAILED - {e}")
        return False
    
    try:
        from skills import risk_assessment, vulnerability_check
        print("  skills: OK")
    except Exception as e:
        print(f"  skills: FAILED - {e}")
        return False
    
    return True


def test_config():
    """Test configuration."""
    print("\nTesting config...")
    import config
    print(f"  LOG_DIR: {config.LOG_DIR}")
    print(f"  POLL_INTERVALS: {config.POLL_INTERVALS}")
    print(f"  WATCH_DIRECTORY: {config.WATCH_DIRECTORY}")
    print(f"  OPENROUTER_API_KEY set: {bool(config.OPENROUTER_API_KEY)}")
    return True


def test_storage():
    """Test storage functionality."""
    print("\nTesting storage...")
    from core import Storage
    storage = Storage()
    
    # Log a test event
    storage.log_event("test_sensor", {"test": "data"})
    print("  log_event: OK")
    
    # Log a test detection
    storage.log_detection("test_rule", "Test detection", {"detail": "value"})
    print("  log_detection: OK")
    
    # Get recent events
    events = storage.get_recent_events(count=5)
    print(f"  get_recent_events: OK ({len(events)} events)")
    
    # Get recent detections
    detections = storage.get_recent_detections(count=5)
    print(f"  get_recent_detections: OK ({len(detections)} detections)")
    
    return True


def test_sensors():
    """Test sensor collection."""
    print("\nTesting sensors...")
    from sensors import file_sensor, process_sensor, port_sensor
    
    context = {}
    
    # Test file sensor
    try:
        result = file_sensor.collect(context)
        print(f"  file_sensor: OK (changes: {result.get('change_count', 0)})")
    except Exception as e:
        print(f"  file_sensor: FAILED - {e}")
    
    # Test process sensor
    try:
        result = process_sensor.collect(context)
        print(f"  process_sensor: OK (count: {result.get('count', 0)})")
    except Exception as e:
        print(f"  process_sensor: FAILED - {e}")
    
    # Test port sensor
    try:
        result = port_sensor.collect(context)
        print(f"  port_sensor: OK (count: {result.get('count', 0)})")
    except Exception as e:
        print(f"  port_sensor: FAILED - {e}")
    
    return True


def test_scheduler():
    """Test scheduler functionality."""
    print("\nTesting scheduler...")
    from core import Scheduler
    
    scheduler = Scheduler()
    
    # Add a simple task
    task_called = []
    def test_task(ctx):
        task_called.append(1)
    
    scheduler.add_task("test_task", 1, test_task)
    print("  add_task: OK")
    
    # Run once
    scheduler.context["_run_once"] = True
    scheduler._running = True
    
    # Manually run the task
    for name, task_info in scheduler._tasks.items():
        task_info["func"](scheduler.context)
    
    print(f"  task executed: {len(task_called)} times")
    
    scheduler.stop()
    print("  stop: OK")
    
    return True


def test_openrouter_client():
    """Test OpenRouter client."""
    print("\nTesting OpenRouter client...")
    from core import OpenRouterClient
    
    client = OpenRouterClient()
    print(f"  api_key set: {bool(client.api_key)}")
    print(f"  base_url: {client.base_url}")
    print(f"  model: {client.model}")
    
    # Test chat completion (will fail without API key)
    if client.api_key:
        result = client.chat_completion([{"role": "user", "content": "Hello"}])
        print(f"  chat_completion: {result[:50] if result else 'None'}")
    else:
        print("  chat_completion: SKIPPED (no API key)")
    
    return True


def test_detection():
    """Test detection logic."""
    print("\nTesting detection...")
    from analysis import detection
    from core import Storage
    
    storage = Storage()
    context = {}
    
    # Add test data that should trigger detection
    context["process_sensor_last"] = {"count": 300, "top_processes": []}
    context["port_sensor_last"] = {"count": 60, "listening": []}
    context["file_sensor_last"] = {"change_count": 150, "added": [], "removed": [], "modified": []}
    
    anomalies = detection.detect(context, storage)
    print(f"  detection: {len(anomalies)} anomalies detected")
    for a in anomalies:
        print(f"    - {a.get('rule')}: {a.get('description')}")
    
    return True


def test_main_function():
    """Test main function initialization."""
    print("\nTesting main function...")
    import main
    
    # Just verify we can create the components
    storage = main.Storage()
    scheduler = main.Scheduler()
    client = main.OpenRouterClient()
    
    print("  Storage created: OK")
    print("  Scheduler created: OK")
    print("  OpenRouterClient created: OK")
    
    # Test make_sensor_task
    task = main.make_sensor_task("process_sensor", storage)
    print("  make_sensor_task: OK")
    
    scheduler.stop()
    
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("MONITORING AGENT TEST SUITE")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_storage,
        test_sensors,
        test_scheduler,
        test_openrouter_client,
        test_detection,
        test_main_function,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"EXCEPTION in {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
