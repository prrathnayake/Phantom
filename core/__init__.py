"""Core framework for Monica - the security monitoring agent.

This package provides the building blocks used by the agent.  It includes
the scheduler responsible for running recurring tasks, a storage layer for
persisting events and detections, and the `OpenRouterClient` used to
communicate with the OpenRouter LLM API.
"""

from .scheduler import Scheduler  # noqa: F401
from .storage import Storage  # noqa: F401
from .openrouter_client import OpenRouterClient  # noqa: F401
