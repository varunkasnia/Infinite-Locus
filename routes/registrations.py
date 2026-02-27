from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy.exc import IntegrityError
from extensions import db, socketio
from models import Event, Registration

registrations_bp = Blueprint("registrations", __name__, url_prefix="/api/registrations")


def _user_required():
    claims = get_jwt()
    if claims.get("role") != "user":
        return jsonify({"error": "This action is for users only"}), 403
    return None


@registrations_bp.route("/<int:event_id>", methods=["POST"])
@jwt_required()
def register_for_event(event_id):
    err = _user_required()
    if err:
        return err

    user_id = int(get_jwt_identity())

    try:
        event = db.session.query(Event).with_for_update().get(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404

        current_count = db.session.query(Registration).filter_by(event_id=event_id).count()
        if current_count >= event.max_capacity:
            return jsonify({"error": "Event is at full capacity"}), 409

        registration = Registration(user_id=user_id, event_id=event_id)
        db.session.add(registration)
        db.session.commit()

        new_count = current_count + 1

        socketio.emit("update_count", {
            "event_id": event_id,
            "new_count": new_count,
            "max_capacity": event.max_capacity,
        })

        return jsonify({
            "message": "Successfully Registered",
            "registration": registration.to_dict(),
            "new_count": new_count,
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "You are already registered for this event"}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@registrations_bp.route("/my", methods=["GET"])
@jwt_required()
def my_registrations():
    user_id = int(get_jwt_identity())
    regs = Registration.query.filter_by(user_id=user_id).all()
    return jsonify([r.to_dict() for r in regs]), 200


@registrations_bp.route("/<int:event_id>", methods=["DELETE"])
@jwt_required()
def cancel_registration(event_id):
    user_id = int(get_jwt_identity())
    reg = Registration.query.filter_by(user_id=user_id, event_id=event_id).first()
    if not reg:
        return jsonify({"error": "Registration not found"}), 404

    db.session.delete(reg)
    db.session.commit()

    new_count = Registration.query.filter_by(event_id=event_id).count()
    event = Event.query.get(event_id)
    socketio.emit("update_count", {
        "event_id": event_id,
        "new_count": new_count,
        "max_capacity": event.max_capacity if event else 0,
    })

    return jsonify({"message": "Registration Cancelled"}), 200