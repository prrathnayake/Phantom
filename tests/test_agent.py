"""Test the Phantom agent - new architecture."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test all imports work correctly."""
    print("Testing imports...")
    import config
    print("  config: OK")
    from core import Storage, OpenRouterClient
    print("  core: OK")
    from agent import Agent
    print("  agent: OK")
    from gateway import ScheduleManager, Gateway
    print("  gateway: OK")
    from diagnostics import file_sensor, process_sensor, port_sensor
    print("  diagnostics: OK")
    from analysis import detection
    print("  analysis: OK")
    from skills import risk_assessment, vulnerability_check
    print("  skills: OK")


def test_config():
    """Test configuration."""
    print("\nTesting config...")
    import config
    print(f"  LOG_DIR: {config.LOG_DIR}")
    print(f"  POLL_INTERVALS: {config.POLL_INTERVALS}")
    print(f"  WATCH_DIRECTORY: {config.WATCH_DIRECTORY}")
    print(f"  OPENROUTER_API_KEY set: {bool(config.OPENROUTER_API_KEY)}")
    assert config.LOG_DIR is not None


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
    
    assert len(events) > 0


def test_diagnostics():
    """Test diagnostic collection."""
    print("\nTesting diagnostics...")
    from diagnostics import file_sensor, process_sensor, port_sensor
    
    context = {}
    
    result = file_sensor.collect(context)
    print(f"  file_sensor: OK (changes: {result.get('change_count', 0)})")
    assert isinstance(result, dict)
    
    result = process_sensor.collect(context)
    print(f"  process_sensor: OK (count: {result.get('count', 0)})")
    assert isinstance(result, dict)
    
    result = port_sensor.collect(context)
    print(f"  port_sensor: OK (count: {result.get('count', 0)})")
    assert isinstance(result, dict)


def test_gateway():
    """Test Gateway components."""
    print("\nTesting gateway...")
    from gateway import ScheduleManager, Gateway
    
    mgr = ScheduleManager()
    print("  ScheduleManager: OK")
    assert mgr is not None
    
    gw = Gateway(autonomous=False)
    print("  Gateway: OK")
    assert gw is not None


def test_agent():
    """Test Agent."""
    print("\nTesting agent...")
    from agent import Agent
    
    agent = Agent()
    print("  Agent: OK")
    assert agent is not None
    
    payload = {"source": "test", "data": {"key": "value"}}
    result = agent.analyze(payload, session_id="test-session")
    print(f"  analyze: OK (session: {result.session_id})")
    assert result.session_id == "test-session"


def test_openrouter_client():
    """Test OpenRouter client."""
    print("\nTesting OpenRouter client...")
    from core import OpenRouterClient
    
    client = OpenRouterClient()
    print(f"  api_key set: {bool(client.api_key)}")
    print(f"  base_url: {client.base_url}")
    print(f"  model: {client.model}")
    
    assert client.base_url is not None


def test_detection():
    """Test detection logic."""
    print("\nTesting detection...")
    from analysis import detection
    from core import Storage
    import config
    
    storage = Storage()
    context = {}
    
    context["process_sensor_last"] = {"count": 500, "top_processes": []}
    context["port_sensor_last"] = {"count": 150, "listening": []}
    context["file_sensor_last"] = {"change_count": 600, "added": [], "removed": [], "modified": []}
    
    anomalies = detection.detect(context, storage)
    print(f"  detection: {len(anomalies)} anomalies detected")
    
    assert len(anomalies) > 0


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
        test_agent,
        test_openrouter_client,
        test_detection,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"ASSERTION FAILED in {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"EXCEPTION in {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)