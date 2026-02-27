import csv
import io
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import Event, Registration, User

events_bp = Blueprint("events", __name__, url_prefix="/api/events")


def _organizer_required():
    claims = get_jwt()
    if claims.get("role") != "organizer":
        return jsonify({"error": "Organizer access required"}), 403
    return None



@events_bp.route("/", methods=["GET"])
@jwt_required()
def list_events():
    """All upcoming events (users + organizers)."""
    now = datetime.now(timezone.utc)
    events = (
        Event.query
        .filter(Event.event_date >= now)
        .order_by(Event.event_date.asc())
        .all()
    )
    return jsonify([e.to_dict() for e in events]), 200


@events_bp.route("/<int:event_id>", methods=["GET"])
@jwt_required()
def get_event(event_id):
    event = Event.query.get_or_404(event_id)
    return jsonify(event.to_dict()), 200



@events_bp.route("/", methods=["POST"])
@jwt_required()
def create_event():
    err = _organizer_required()
    if err:
        return err

    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    title        = (data.get("title") or "").strip()
    description  = (data.get("description") or "").strip()
    location     = (data.get("location") or "").strip()
    event_date   = data.get("event_date")
    max_capacity = data.get("max_capacity", 100)

    if not title or not event_date:
        return jsonify({"error": "title and event_date are required"}), 400

    try:
        event_date = datetime.fromisoformat(event_date)
        max_capacity = int(max_capacity)
        if max_capacity < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid event_date or max_capacity"}), 400

    event = Event(
        title=title,
        description=description,
        location=location,
        event_date=event_date,
        max_capacity=max_capacity,
        created_by=user_id,
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"message": "Event created", "event": event.to_dict()}), 201


@events_bp.route("/<int:event_id>", methods=["PUT"])
@jwt_required()
def update_event(event_id):
    err = _organizer_required()
    if err:
        return err

    user_id = int(get_jwt_identity())
    event = Event.query.get_or_404(event_id)

    if event.created_by != user_id:
        return jsonify({"error": "You can only edit your own events"}), 403

    data = request.get_json(silent=True) or {}

    if "title" in data:
        event.title = data["title"].strip()
    if "description" in data:
        event.description = data["description"].strip()
    if "location" in data:
        event.location = data["location"].strip()
    if "event_date" in data:
        try:
            event.event_date = datetime.fromisoformat(data["event_date"])
        except ValueError:
            return jsonify({"error": "Invalid event_date format"}), 400
    if "max_capacity" in data:
        try:
            mc = int(data["max_capacity"])
            if mc < event.registration_count:
                return jsonify({"error": "max_capacity cannot be less than current registrations"}), 400
            event.max_capacity = mc
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid max_capacity"}), 400

    db.session.commit()
    return jsonify({"message": "Event updated", "event": event.to_dict()}), 200


@events_bp.route("/<int:event_id>", methods=["DELETE"])
@jwt_required()
def delete_event(event_id):
    err = _organizer_required()
    if err:
        return err

    user_id = int(get_jwt_identity())
    event = Event.query.get_or_404(event_id)

    if event.created_by != user_id:
        return jsonify({"error": "You can only delete your own events"}), 403

    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Event deleted"}), 200


@events_bp.route("/<int:event_id>/registrations", methods=["GET"])
@jwt_required()
def event_registrations(event_id):
    err = _organizer_required()
    if err:
        return err

    user_id = int(get_jwt_identity())
    event = Event.query.get_or_404(event_id)

    if event.created_by != user_id:
        return jsonify({"error": "Access denied"}), 403

    regs = Registration.query.filter_by(event_id=event_id).all()
    return jsonify({
        "event": event.to_dict(),
        "registrations": [r.to_dict() for r in regs],
        "count": len(regs),
    }), 200


@events_bp.route("/<int:event_id>/registrations/export", methods=["GET"])
@jwt_required()
def export_registrations_csv(event_id):
    err = _organizer_required()
    if err:
        return err

    user_id = int(get_jwt_identity())
    event = Event.query.get_or_404(event_id)

    if event.created_by != user_id:
        return jsonify({"error": "Access denied"}), 403

    regs = Registration.query.filter_by(event_id=event_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "User Name", "Email", "Registered At"])
    for i, r in enumerate(regs, 1):
        writer.writerow([i, r.user.name, r.user.email, r.registered_at.isoformat()])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=event_{event_id}_registrations.csv"},
    )


@events_bp.route("/my", methods=["GET"])
@jwt_required()
def my_events():
    """Organizer's own events."""
    err = _organizer_required()
    if err:
        return err

    user_id = int(get_jwt_identity())
    events = Event.query.filter_by(created_by=user_id).order_by(Event.event_date.asc()).all()
    return jsonify([e.to_dict() for e in events]), 200


@events_bp.route("/analytics/summary", methods=["GET"])
@jwt_required()
def analytics_summary():
    err = _organizer_required()
    if err:
        return err

    from sqlalchemy import func, desc
    from models import User as UserModel

    total_users  = db.session.query(func.count(UserModel.id)).scalar()
    total_events = db.session.query(func.count(Event.id)).scalar()
    total_regs   = db.session.query(func.count(Registration.id)).scalar()

    popular = (
        db.session.query(Event.id, Event.title, func.count(Registration.id).label("reg_count"))
        .join(Registration, Registration.event_id == Event.id)
        .group_by(Event.id, Event.title)
        .order_by(desc("reg_count"))
        .limit(5)
        .all()
    )

    return jsonify({
        "total_users":  total_users,
        "total_events": total_events,
        "total_registrations": total_regs,
        "most_popular_events": [
            {"id": r.id, "title": r.title, "registration_count": r.reg_count}
            for r in popular
        ],
    }), 200
