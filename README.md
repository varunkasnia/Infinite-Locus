
## Database Schema

### users
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | VARCHAR(120) | |
| email | VARCHAR(255) | UNIQUE, indexed |
| password | VARCHAR(255) | bcrypt hashed |
| role | ENUM | organizer / user |
| created_at | DATETIME | UTC |

### events
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| title | VARCHAR(200) | |
| description | TEXT | |
| location | VARCHAR(300) | |
| event_date | DATETIME | indexed |
| max_capacity | INTEGER | |
| created_by | INTEGER FK | → users.id CASCADE |
| created_at | DATETIME | UTC |

### registrations
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER FK | → users.id CASCADE |
| event_id | INTEGER FK | → events.id CASCADE |
| registered_at | DATETIME | UTC |
| — | UNIQUE | (user_id, event_id) |

### notifications
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| event_id | INTEGER FK UNIQUE | → events.id CASCADE |
| sent_at | DATETIME | UTC |

