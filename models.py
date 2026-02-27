from datetime import datetime, timezone
import enum
from extensions import db


class UserRole(str, enum.Enum):
    organizer = "organizer"
    user = "user"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.user)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    events = db.relationship("Event", back_populates="organizer", cascade="all, delete-orphan")
    registrations = db.relationship("Registration", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
        }


class Event(db.Model):
    __tablename__ = "events"
    __table_args__ = (
        db.Index("ix_events_event_date", "event_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(300), nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False, default=100)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    organizer = db.relationship("User", back_populates="events")
    registrations = db.relationship("Registration", back_populates="event", cascade="all, delete-orphan")

    @property
    def registration_count(self):
        return len(self.registrations)

    def to_dict(self, include_count=True):
        d = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "event_date": self.event_date.isoformat(),
            "max_capacity": self.max_capacity,
            "created_by": self.created_by,
            "organizer": self.organizer.name if self.organizer else None,
            "created_at": self.created_at.isoformat(),
        }
        if include_count:
            d["registration_count"] = self.registration_count
        return d


class Registration(db.Model):
    __tablename__ = "registrations"
    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="uq_user_event"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    registered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="registrations")
    event = db.relationship("Event", back_populates="registrations")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "user_name": self.user.name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "registered_at": self.registered_at.isoformat(),
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False, unique=True)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))