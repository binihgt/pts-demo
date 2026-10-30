from flask import current_app, has_app_context
from app import create_app

_bot_app_instance = None


def get_bot_app():
    """
    Return the active Flask application.
    If running within an active Flask app context (such as in automated tests),
    returns the active application (e.g. in-memory test DB).
    Otherwise, returns the lazily initialized standalone bot application.
    """
    global _bot_app_instance
    if has_app_context():
        return current_app._get_current_object()
    if _bot_app_instance is None:
        _bot_app_instance = create_app()
    return _bot_app_instance
