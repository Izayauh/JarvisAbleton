"""
Context Management for Jarvis AI Audio Engineer

Tracks session state, project context, user preferences, and crash recovery.
"""

from context.session_manager import session_manager, SessionManager, SessionState
from context.session_persistence import get_session_persistence, SessionPersistence
from context.crash_recovery import get_crash_recovery, CrashRecoveryManager, with_crash_recovery

__all__ = [
    # Session management
    "session_manager",
    "SessionManager",
    "SessionState",
    # Persistence
    "get_session_persistence",
    "SessionPersistence",
    # Crash recovery
    "get_crash_recovery",
    "CrashRecoveryManager",
    "with_crash_recovery",
]
