from flask import current_app, has_app_context

_bot_app_instance = None


def set_bot_app(app):
    """Register the active initialized Flask application."""
    global _bot_app_instance
    _bot_app_instance = app


def get_bot_app():
    """
    Return the active Flask application.
    If running within an active Flask app context (such as in automated tests),
    returns the active application (e.g. in-memory test DB).
    Otherwise, returns the cached or lazily initialized standalone bot application.
    """
    global _bot_app_instance
    if has_app_context():
        return current_app._get_current_object()
    if _bot_app_instance is not None:
        return _bot_app_instance
    from app import create_app
    _bot_app_instance = create_app()
    return _bot_app_instance

