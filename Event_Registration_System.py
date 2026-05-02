from flask import Flask, request, jsonify, g
import sqlite3
import jwt
import uuid
import os
from datetime import datetime, timedelta, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────
SECRET_KEY = "codealpha_event_secret_2024"
DB_PATH = "events.db"
TOKEN_EXPIRY_HOURS = 24


# ─────────────────────────────────────────────
#  Database helpers
# ─────────────────────────────────────────────
def get_db():
    """Return a thread-local SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row   # allows dict-like column access
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    """Create tables and seed one admin account on first run."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # Users table (regular users + admins)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',   -- 'user' or 'admin'
            created_at  TEXT NOT NULL
        )
    """)

    # Events table
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id           TEXT PRIMARY KEY,
            title        TEXT NOT NULL,
            description  TEXT,
            location     TEXT,
            event_date   TEXT NOT NULL,
            capacity     INTEGER NOT NULL DEFAULT 50,
            price        REAL NOT NULL DEFAULT 0.0,
            organizer_id TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'active',  -- active / cancelled / completed
            created_at   TEXT NOT NULL,
            FOREIGN KEY (organizer_id) REFERENCES users(id)
        )
    """)

    # Registrations table  (many-to-many: users <-> events)
    c.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            event_id    TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'confirmed',  -- confirmed / cancelled
            registered_at TEXT NOT NULL,
            FOREIGN KEY (user_id)  REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            UNIQUE (user_id, event_id)   -- one registration per user per event
        )
    """)

    # Seed admin account if it doesn't exist yet
    existing = c.execute("SELECT id FROM users WHERE email = 'admin@codealpha.com'").fetchone()
    if not existing:
        c.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                "Admin CodeAlpha",
                "admin@codealpha.com",
                generate_password_hash("Admin@123"),
                "admin",
                datetime.utcnow().isoformat(),
            ),
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  JWT Auth decorators
# ─────────────────────────────────────────────
def token_required(f):
    """Protect a route — any logged-in user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token missing or malformed"}), 401
        token = auth_header.split(" ")[1]
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            g.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired, please login again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Protect a route — admin users only."""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if g.current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def generate_token(user_id, email, role):
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# ─────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────
def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  Auth Routes
# ─────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json()
    name  = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify({"error": "Email already registered"}), 409

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?)",
        (user_id, name, email, generate_password_hash(password), "user", datetime.utcnow().isoformat()),
    )
    db.commit()

    token = generate_token(user_id, email, "user")
    return jsonify({"message": "Registration successful", "token": token, "user": {"id": user_id, "name": name, "email": email, "role": "user"}}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Login and receive a JWT token."""
    data = request.get_json()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    db  = get_db()
    user = row_to_dict(db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user["id"], user["email"], user["role"])
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]},
    })


@app.route("/api/auth/profile", methods=["GET"])
@token_required
def profile():
    """Get currently logged-in user's profile."""
    db   = get_db()
    user = row_to_dict(db.execute("SELECT id,name,email,role,created_at FROM users WHERE id = ?", (g.current_user["user_id"],)).fetchone())
    return jsonify(user)


# ─────────────────────────────────────────────
#  Event Routes
# ─────────────────────────────────────────────
@app.route("/api/events", methods=["GET"])
def list_events():
    """
    Public endpoint — list all active events.
    Supports query params:  ?search=<text>  &  ?upcoming=true
    Each event includes the current number of confirmed registrations.
    """
    search   = request.args.get("search", "").strip()
    upcoming = request.args.get("upcoming", "").lower() == "true"

    query = """
        SELECT e.*, u.name AS organizer_name,
               COUNT(r.id) AS registered_count
        FROM   events e
        JOIN   users u ON u.id = e.organizer_id
        LEFT JOIN registrations r ON r.event_id = e.id AND r.status = 'confirmed'
        WHERE  e.status = 'active'
    """
    params = []

    if search:
        query  += " AND (e.title LIKE ? OR e.description LIKE ? OR e.location LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]

    if upcoming:
        query  += " AND e.event_date >= ?"
        params.append(datetime.utcnow().isoformat())

    query += " GROUP BY e.id ORDER BY e.event_date ASC"

    db     = get_db()
    events = rows_to_list(db.execute(query, params).fetchall())
    return jsonify({"total": len(events), "events": events})


@app.route("/api/events/<event_id>", methods=["GET"])
def get_event(event_id):
    """Get full details of a single event."""
    db = get_db()
    event = row_to_dict(db.execute("""
        SELECT e.*, u.name AS organizer_name,
               COUNT(r.id) AS registered_count
        FROM   events e
        JOIN   users u ON u.id = e.organizer_id
        LEFT JOIN registrations r ON r.event_id = e.id AND r.status = 'confirmed'
        WHERE  e.id = ?
        GROUP BY e.id
    """, (event_id,)).fetchone())

    if not event:
        return jsonify({"error": "Event not found"}), 404

    event["spots_left"] = max(0, event["capacity"] - event["registered_count"])
    return jsonify(event)


@app.route("/api/events", methods=["POST"])
@admin_required
def create_event():
    """Admin only — create a new event."""
    data = request.get_json()
    required = ["title", "event_date"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    event_id = str(uuid.uuid4())
    db = get_db()
    db.execute(
        "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            event_id,
            data["title"].strip(),
            data.get("description", ""),
            data.get("location", ""),
            data["event_date"],
            int(data.get("capacity", 50)),
            float(data.get("price", 0.0)),
            g.current_user["user_id"],
            "active",
            datetime.utcnow().isoformat(),
        ),
    )
    db.commit()
    return jsonify({"message": "Event created successfully", "event_id": event_id}), 201


@app.route("/api/events/<event_id>", methods=["PUT"])
@admin_required
def update_event(event_id):
    """Admin only — update an event."""
    db    = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    data = request.get_json()
    fields = ["title", "description", "location", "event_date", "capacity", "price", "status"]
    updates, params = [], []

    for field in fields:
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])

    if not updates:
        return jsonify({"error": "No fields to update"}), 400

    params.append(event_id)
    db.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    return jsonify({"message": "Event updated successfully"})


@app.route("/api/events/<event_id>", methods=["DELETE"])
@admin_required
def delete_event(event_id):
    """Admin only — cancel/delete an event."""
    db = get_db()
    if not db.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone():
        return jsonify({"error": "Event not found"}), 404

    db.execute("UPDATE events SET status = 'cancelled' WHERE id = ?", (event_id,))
    db.commit()
    return jsonify({"message": "Event cancelled successfully"})


# ─────────────────────────────────────────────
#  Registration Routes
# ─────────────────────────────────────────────
@app.route("/api/events/<event_id>/register", methods=["POST"])
@token_required
def register_for_event(event_id):
    """Authenticated user registers for an event."""
    db    = get_db()
    event = row_to_dict(db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone())

    if not event:
        return jsonify({"error": "Event not found"}), 404
    if event["status"] != "active":
        return jsonify({"error": "This event is not accepting registrations"}), 400

    # Check capacity
    registered = db.execute(
        "SELECT COUNT(*) as cnt FROM registrations WHERE event_id = ? AND status = 'confirmed'",
        (event_id,)
    ).fetchone()["cnt"]

    if registered >= event["capacity"]:
        return jsonify({"error": "Event is fully booked"}), 400

    user_id = g.current_user["user_id"]

    # Check duplicate
    existing = db.execute(
        "SELECT * FROM registrations WHERE user_id = ? AND event_id = ?",
        (user_id, event_id)
    ).fetchone()

    if existing:
        if existing["status"] == "confirmed":
            return jsonify({"error": "You are already registered for this event"}), 409
        # re-activate a cancelled registration
        db.execute(
            "UPDATE registrations SET status = 'confirmed', registered_at = ? WHERE user_id = ? AND event_id = ?",
            (datetime.utcnow().isoformat(), user_id, event_id)
        )
        db.commit()
        return jsonify({"message": "Registration re-activated successfully"})

    reg_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO registrations VALUES (?,?,?,?,?)",
        (reg_id, user_id, event_id, "confirmed", datetime.utcnow().isoformat())
    )
    db.commit()
    return jsonify({"message": "Successfully registered for the event", "registration_id": reg_id}), 201


@app.route("/api/events/<event_id>/cancel-registration", methods=["DELETE"])
@token_required
def cancel_registration(event_id):
    """Authenticated user cancels their registration."""
    db      = get_db()
    user_id = g.current_user["user_id"]
    reg     = db.execute(
        "SELECT * FROM registrations WHERE user_id = ? AND event_id = ? AND status = 'confirmed'",
        (user_id, event_id)
    ).fetchone()

    if not reg:
        return jsonify({"error": "Active registration not found"}), 404

    db.execute(
        "UPDATE registrations SET status = 'cancelled' WHERE user_id = ? AND event_id = ?",
        (user_id, event_id)
    )
    db.commit()
    return jsonify({"message": "Registration cancelled successfully"})


@app.route("/api/my-registrations", methods=["GET"])
@token_required
def my_registrations():
    """Get all registrations for the logged-in user."""
    db      = get_db()
    user_id = g.current_user["user_id"]
    regs    = rows_to_list(db.execute("""
        SELECT r.id AS registration_id, r.status AS registration_status,
               r.registered_at,
               e.id AS event_id, e.title, e.event_date, e.location, e.price
        FROM   registrations r
        JOIN   events e ON e.id = r.event_id
        WHERE  r.user_id = ?
        ORDER BY r.registered_at DESC
    """, (user_id,)).fetchall())
    return jsonify({"total": len(regs), "registrations": regs})


# ─────────────────────────────────────────────
#  Admin Panel Routes
# ─────────────────────────────────────────────
@app.route("/api/admin/events/<event_id>/registrations", methods=["GET"])
@admin_required
def admin_event_registrations(event_id):
    """Admin — view all registrations for a specific event."""
    db = get_db()
    regs = rows_to_list(db.execute("""
        SELECT r.id, r.status, r.registered_at,
               u.id AS user_id, u.name AS user_name, u.email AS user_email
        FROM   registrations r
        JOIN   users u ON u.id = r.user_id
        WHERE  r.event_id = ?
        ORDER BY r.registered_at ASC
    """, (event_id,)).fetchall())
    return jsonify({"event_id": event_id, "total": len(regs), "registrations": regs})


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_list_users():
    """Admin — list all registered users."""
    db    = get_db()
    users = rows_to_list(db.execute("SELECT id, name, email, role, created_at FROM users").fetchall())
    return jsonify({"total": len(users), "users": users})


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    """Admin — dashboard statistics."""
    db = get_db()
    stats = {
        "total_users":         db.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        "total_events":        db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "active_events":       db.execute("SELECT COUNT(*) FROM events WHERE status='active'").fetchone()[0],
        "total_registrations": db.execute("SELECT COUNT(*) FROM registrations WHERE status='confirmed'").fetchone()[0],
    }
    return jsonify(stats)


# ─────────────────────────────────────────────
#  Root health check
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "system":  "CodeAlpha — Event Registration System",
        "status":  "running",
        "version": "1.0.0",
    })


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("=" * 55)
    print("  CodeAlpha Task 2 — Event Registration System")
    print("  Server: http://localhost:5000")
    print("  Admin:  admin@codealpha.com  /  Admin@123")
    print("=" * 55)
    app.run(debug=True, port=5000)