import eventlet
eventlet.monkey_patch()

from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, redirect, url_for
from config import Config
from extensions import db, jwt, socketio, bcrypt, migrate, scheduler


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")

    from routes.auth import auth_bp
    from routes.events import events_bp
    from routes.registrations import registrations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)

    from flask_jwt_extended import exceptions as jwt_exceptions
    from flask import jsonify

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired. Please log in again."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Invalid token. Please log in again."}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "Authentication required."}), 401

    @app.route("/")
    def index():
        return redirect(url_for("pages.login_page"))

    from flask import Blueprint
    pages = Blueprint("pages", __name__)

    @pages.route("/login")
    def login_page():
        return render_template("login.html")

    @pages.route("/signup")
    def signup_page():
        return render_template("signup.html")

    @pages.route("/dashboard/organizer")
    def organizer_dashboard():
        return render_template("organizer_dashboard.html")

    @pages.route("/dashboard/user")
    def user_dashboard():
        return render_template("user_dashboard.html")

    app.register_blueprint(pages)

    @socketio.on("connect")
    def on_connect():
        print("Client connected")

    @socketio.on("disconnect")
    def on_disconnect():
        print("Client disconnected")

    def send_24h_notifications():
        with app.app_context():
            from models import Event, Notification
            now = datetime.now(timezone.utc)
            upper = now + timedelta(hours=24)

            upcoming = (
                Event.query
                .filter(Event.event_date >= now, Event.event_date <= upper)
                .all()
            )
            for event in upcoming:
                already = Notification.query.filter_by(event_id=event.id).first()
                if not already:
                    notif = Notification(event_id=event.id)
                    db.session.add(notif)
                    print(f"[NOTIFY] Event '{event.title}' starts within 24 hours!")
                    socketio.emit("event_reminder", {
                        "event_id": event.id,
                        "title": event.title,
                        "event_date": event.event_date.isoformat(),
                        "location": event.location,
                    })
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    scheduler.add_job(
        send_24h_notifications,
        trigger="interval",
        minutes=30,
        id="notify_24h",
        replace_existing=True,
    )

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"[WARNING] db.create_all() failed: {e}")
            print("  → Make sure DATABASE_URL uses psycopg2, not asyncpg.")
            print("  → e.g.  postgresql+psycopg2://user:pass@localhost/dbname")
            raise

    return app


app = create_app()

if __name__ == "__main__":
    scheduler.start()
    try:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    finally:
        scheduler.shutdown()