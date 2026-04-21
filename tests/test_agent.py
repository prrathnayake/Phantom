"""Test the Phantom agent - new architecture."""
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
        from core import Storage, OpenRouterClient
        print("  core: OK")
    except Exception as e:
        print(f"  core: FAILED - {e}")
        return False
    
    try:
        from central_agent import CentralAgent
        print("  central_agent: OK")
    except Exception as e:
        print(f"  central_agent: FAILED - {e}")
        return False
    
    try:
        from gateway import ScheduleManager, Gateway
        print("  gateway: OK")
    except Exception as e:
        print(f"  gateway: FAILED - {e}")
        return False
    
    try:
        from diagnostics import file_sensor, process_sensor, port_sensor
        print("  diagnostics: OK")
    except Exception as e:
        print(f"  diagnostics: FAILED - {e}")
        return False
    
    try:
        from analysis import detection
        print("  analysis: OK")
    except Exception as e:
        print(f"  analysis: FAILED - {e}")
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
    
    storage.log_event("test_sensor", {"test": "data"})
    print("  log_event: OK")
    
    storage.log_detection("test_rule", "Test detection", {"detail": "value"})
    print("  log_detection: OK")
    
    events = storage.get_recent_events(count=5)
    print(f"  get_recent_events: OK ({len(events)} events)")
    
    detections = storage.get_recent_detections(count=5)
    print(f"  get_recent_detections: OK ({len(detections)} detections)")
    
    return True


def test_diagnostics():
    """Test diagnostic collection."""
    print("\nTesting diagnostics...")
    from diagnostics import file_sensor, process_sensor, port_sensor
    
    context = {}
    
    result = file_sensor.collect(context)
    print(f"  file_sensor: OK (changes: {result.get('change_count', 0)})")
    
    result = process_sensor.collect(context)
    print(f"  process_sensor: OK (count: {result.get('count', 0)})")
    
    result = port_sensor.collect(context)
    print(f"  port_sensor: OK (count: {result.get('count', 0)})")
    
    return True


def test_gateway():
    """Test Gateway components."""
    print("\nTesting gateway...")
    from gateway import ScheduleManager, Gateway
    
    mgr = ScheduleManager()
    print("  ScheduleManager: OK")
    
    gw = Gateway(autonomous=False)
    print("  Gateway: OK")
    
    return True


def test_central_agent():
    """Test Central Agent."""
    print("\nTesting central_agent...")
    from central_agent import CentralAgent
    
    agent = CentralAgent()
    print("  CentralAgent: OK")
    
    payload = {"source": "test", "data": {"key": "value"}}
    result = agent.analyze(payload, session_id="test-session")
    print(f"  analyze: OK (session: {result.session_id})")
    
    return True


def test_openrouter_client():
    """Test OpenRouter client."""
    print("\nTesting OpenRouter client...")
    from core import OpenRouterClient
    
    client = OpenRouterClient()
    print(f"  api_key set: {bool(client.api_key)}")
    print(f"  base_url: {client.base_url}")
    print(f"  model: {client.model}")
    
    return True


def test_detection():
    """Test detection logic."""
    print("\nTesting detection...")
    from analysis import detection
    from core import Storage
    
    storage = Storage()
    context = {}
    
    context["process_sensor_last"] = {"count": 300, "top_processes": []}
    context["port_sensor_last"] = {"count": 60, "listening": []}
    context["file_sensor_last"] = {"change_count": 150, "added": [], "removed": [], "modified": []}
    
    anomalies = detection.detect(context, storage)
    print(f"  detection: {len(anomalies)} anomalies detected")
    
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("SURAKSHA AGENT TEST SUITE")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_storage,
        test_diagnostics,
        test_gateway,
        test_central_agent,
        test_openrouter_client,
        test_detection,
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