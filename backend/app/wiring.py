"""app/wiring.py — event subscriptions shared by both composition roots (API in main.py, worker in worker.py).

The API publishes durable events and must know which durable handlers exist (one outbox row per handler);
the worker must be able to run them. Both call `wire_events()`, so the two lists can never drift apart.
"""

from app.core.events import bus
from app.core.outbox_tasks import kick
from app.modules.auth.handlers import register as register_auth

_wired = False


def wire_events() -> None:
    global _wired
    if _wired:  # create_app() may run many times (tests); subscriptions must be registered once
        return
    _wired = True
    bus.on_outbox_committed = kick
    # One line per module that reacts to events
    register_auth(bus)
