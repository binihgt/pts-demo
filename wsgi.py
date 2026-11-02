from app import create_app
from app.extensions import db

app = create_app()

# Dispose of any database connections opened during startup in master process
# so forked Gunicorn worker processes each establish their own clean SSL connection
with app.app_context():
    db.session.remove()
    try:
        db.engine.dispose()
    except Exception:
        pass

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
