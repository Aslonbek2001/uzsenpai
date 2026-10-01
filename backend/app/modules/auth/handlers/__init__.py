"""Event subscriptions of the auth module — registered by app/wiring.py."""

from app.core.events import EventBus
from app.modules.auth.handlers.user_lifecycle import forget_sign_in_methods, sign_out_on_deletion_request
from app.modules.users.public import UserDeleted, UserDeletionRequested


def register(bus: EventBus) -> None:
    # Names are stored in core_outbox — never rename while rows may be pending.
    bus.subscribe_durable(UserDeletionRequested, "auth.sign_out_on_deletion_request", sign_out_on_deletion_request)
    bus.subscribe_durable(UserDeleted, "auth.forget_sign_in_methods", forget_sign_in_methods)


__all__ = ["register"]
