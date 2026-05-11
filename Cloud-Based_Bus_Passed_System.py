import sqlite3
import hashlib
import secrets
import json
import threading
import time
import qrcode                 
import io
import base64
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file


# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BusPass")


# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

SECRET_KEY = "CodeAlpha_BusPass_Secret_2024"

ROUTES = {
    "R001": {"from": "Karachi",  "to": "Hyderabad",  "fare": 450,  "seats": 40},
    "R002": {"from": "Lahore",   "to": "Islamabad",  "fare": 900,  "seats": 35},
    "R003": {"from": "Karachi",  "to": "Quetta",     "fare": 1800, "seats": 30},
    "R004": {"from": "Peshawar", "to": "Rawalpindi", "fare": 600,  "seats": 45},
    "R005": {"from": "Multan",   "to": "Faisalabad", "fare": 500,  "seats": 38},
}


# ─────────────────────────────────────────────
#  Auto-Scaling Simulator
# ─────────────────────────────────────────────

class AutoScaler:
    """
    Simulates cloud auto-scaling logic.
    Tracks active request load and adjusts instance count dynamically.
    In a real deployment this would trigger AWS ASG / Azure VMSS / GCP MIG.
    """

    def __init__(self, min_instances=1, max_instances=10, scale_up_at=70, scale_down_at=30):
        self.min_instances   = min_instances
        self.max_instances   = max_instances
        self.scale_up_at     = scale_up_at     # % load threshold
        self.scale_down_at   = scale_down_at
        self.current_instances = min_instances
        self._active_requests  = 0
        self._lock             = threading.Lock()

    def _load_percent(self) -> float:
        capacity = self.current_instances * 50   # 50 req/instance cap
        return min(100.0, (self._active_requests / max(capacity, 1)) * 100)

    def request_start(self):
        with self._lock:
            self._active_requests += 1
            load = self._load_percent()
            if load > self.scale_up_at and self.current_instances < self.max_instances:
                self.current_instances += 1
                logger.info("AUTO-SCALE UP  → %d instances (load=%.1f%%)", self.current_instances, load)

    def request_end(self):
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            load = self._load_percent()
            if load < self.scale_down_at and self.current_instances > self.min_instances:
                self.current_instances -= 1
                logger.info("AUTO-SCALE DOWN → %d instances (load=%.1f%%)", self.current_instances, load)

    def status(self) -> dict:
        return {
            "instances": self.current_instances,
            "active_requests": self._active_requests,
            "load_percent": round(self._load_percent(), 1),
        }


_scaler = AutoScaler()


# ─────────────────────────────────────────────
#  Database
# ─────────────────────────────────────────────

_DB_LOCK = threading.Lock()


def init_db(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")   # WAL mode for concurrent reads
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_ref   TEXT UNIQUE NOT NULL,
            passenger     TEXT NOT NULL,
            phone         TEXT NOT NULL,
            route_id      TEXT NOT NULL,
            travel_date   TEXT NOT NULL,
            seat_number   INTEGER NOT NULL,
            fare_locked   INTEGER NOT NULL,
            token         TEXT UNIQUE NOT NULL,
            token_sig     TEXT NOT NULL,
            status        TEXT DEFAULT 'ACTIVE',
            created_at    TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seat_inventory (
            route_id     TEXT NOT NULL,
            travel_date  TEXT NOT NULL,
            seat_number  INTEGER NOT NULL,
            status       TEXT DEFAULT 'AVAILABLE',
            booking_ref  TEXT,
            PRIMARY KEY (route_id, travel_date, seat_number)
        )
    """)
    conn.commit()
    return conn


_DB = init_db()


def seed_seats(route_id: str, travel_date: str):
    """Ensure seat rows exist for a route/date pair."""
    route    = ROUTES[route_id]
    with _DB_LOCK:
        for seat_no in range(1, route["seats"] + 1):
            _DB.execute(
                "INSERT OR IGNORE INTO seat_inventory (route_id, travel_date, seat_number, status) VALUES (?,?,?,?)",
                (route_id, travel_date, seat_no, "AVAILABLE")
            )
        _DB.commit()


# ─────────────────────────────────────────────
#  Token & Signature
# ─────────────────────────────────────────────

def generate_token(booking_ref: str, route_id: str, seat: int, fare: int, date: str) -> tuple[str, str]:
    """
    Create a cryptographically signed booking token.
    The signature prevents tampering with fare or seat details.
    """
    token = secrets.token_urlsafe(24)
    payload = f"{token}:{booking_ref}:{route_id}:{seat}:{fare}:{date}:{SECRET_KEY}"
    sig = hashlib.sha256(payload.encode()).hexdigest()
    return token, sig


def verify_token(token: str, booking_ref: str, route_id: str, seat: int, fare: int, date: str, sig: str) -> bool:
    """Re-compute signature and compare to detect tampering."""
    payload = f"{token}:{booking_ref}:{route_id}:{seat}:{fare}:{date}:{SECRET_KEY}"
    expected = hashlib.sha256(payload.encode()).hexdigest()
    return secrets.compare_digest(expected, sig)


def generate_qr_base64(data: str) -> str:
    """Generate a QR code PNG and return it as a base64 string."""
    qr     = qrcode.QRCode(version=2, box_size=6, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    img    = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ─────────────────────────────────────────────
#  Booking Logic
# ─────────────────────────────────────────────

def book_ticket(passenger: str, phone: str, route_id: str, travel_date: str) -> dict:
    """
    Thread-safe ticket booking:
      1. Validate route and date
      2. Lock a seat atomically (prevents double-booking)
      3. Lock fare at booking time (prevents price manipulation later)
      4. Generate signed token + QR code
    """
    if route_id not in ROUTES:
        return {"error": f"Route '{route_id}' does not exist."}

    route = ROUTES[route_id]

    # Validate travel date
    try:
        travel_dt = datetime.strptime(travel_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "travel_date must be YYYY-MM-DD."}
    if travel_dt.date() < datetime.utcnow().date():
        return {"error": "Cannot book a ticket for a past date."}

    seed_seats(route_id, travel_date)

    with _DB_LOCK:
        # Find first available seat (atomic under lock)
        row = _DB.execute(
            "SELECT seat_number FROM seat_inventory WHERE route_id=? AND travel_date=? AND status='AVAILABLE' LIMIT 1",
            (route_id, travel_date)
        ).fetchone()

        if not row:
            return {"error": "No seats available on this route/date."}

        seat_number = row[0]
        fare_locked = route["fare"]          # price is locked at booking time — immutable
        booking_ref = f"BP-{secrets.token_hex(5).upper()}"
        token, sig  = generate_token(booking_ref, route_id, seat_number, fare_locked, travel_date)
        now         = datetime.utcnow().isoformat()

        _DB.execute(
            "UPDATE seat_inventory SET status='BOOKED', booking_ref=? WHERE route_id=? AND travel_date=? AND seat_number=?",
            (booking_ref, route_id, travel_date, seat_number)
        )
        _DB.execute(
            """
            INSERT INTO bookings (booking_ref, passenger, phone, route_id, travel_date,
                                  seat_number, fare_locked, token, token_sig, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (booking_ref, passenger, phone, route_id, travel_date,
             seat_number, fare_locked, token, sig, "ACTIVE", now)
        )
        _DB.commit()

    # Generate QR code with embedded verification data
    qr_payload = json.dumps({
        "ref":    booking_ref,
        "token":  token,
        "route":  route_id,
        "seat":   seat_number,
        "fare":   fare_locked,
        "date":   travel_date,
    })
    qr_b64 = generate_qr_base64(qr_payload)

    logger.info("Booking confirmed: %s  seat=%d  fare=%d  route=%s", booking_ref, seat_number, fare_locked, route_id)

    return {
        "booking_ref":   booking_ref,
        "passenger":     passenger,
        "route":         f"{route['from']} → {route['to']}",
        "travel_date":   travel_date,
        "seat_number":   seat_number,
        "fare_locked":   fare_locked,
        "token":         token,
        "status":        "ACTIVE",
        "qr_code_base64": qr_b64,
    }


def validate_ticket(booking_ref: str, token: str) -> dict:
    """
    Validate ticket at boarding:
      - Verify token signature (tamper-proof)
      - Check ticket is ACTIVE and not already used
      - Mark as USED (single-use anti-theft)
    """
    with _DB_LOCK:
        row = _DB.execute(
            "SELECT route_id, travel_date, seat_number, fare_locked, token_sig, status FROM bookings WHERE booking_ref=? AND token=?",
            (booking_ref, token)
        ).fetchone()

        if not row:
            return {"valid": False, "reason": "Booking not found or token mismatch."}

        route_id, travel_date, seat, fare, sig, status = row

        if status == "USED":
            return {"valid": False, "reason": "Ticket has already been used. Possible theft/duplicate detected."}

        if status == "CANCELLED":
            return {"valid": False, "reason": "This ticket has been cancelled."}

        if not verify_token(token, booking_ref, route_id, seat, fare, travel_date, sig):
            return {"valid": False, "reason": "Token signature invalid. Possible tampering detected."}

        # Mark single-use
        _DB.execute("UPDATE bookings SET status='USED' WHERE booking_ref=?", (booking_ref,))
        _DB.commit()

    route = ROUTES[route_id]
    return {
        "valid":       True,
        "booking_ref": booking_ref,
        "route":       f"{route['from']} → {route['to']}",
        "travel_date": travel_date,
        "seat_number": seat,
        "fare_paid":   fare,
        "message":     "Ticket validated. Passenger may board.",
    }


def cancel_ticket(booking_ref: str) -> dict:
    with _DB_LOCK:
        row = _DB.execute(
            "SELECT route_id, travel_date, seat_number, status FROM bookings WHERE booking_ref=?",
            (booking_ref,)
        ).fetchone()

        if not row:
            return {"error": "Booking not found."}

        route_id, travel_date, seat, status = row
        if status in ("USED", "CANCELLED"):
            return {"error": f"Cannot cancel a {status} ticket."}

        _DB.execute("UPDATE bookings SET status='CANCELLED' WHERE booking_ref=?", (booking_ref,))
        _DB.execute(
            "UPDATE seat_inventory SET status='AVAILABLE', booking_ref=NULL WHERE route_id=? AND travel_date=? AND seat_number=?",
            (route_id, travel_date, seat)
        )
        _DB.commit()

    logger.info("Ticket cancelled: %s", booking_ref)
    return {"message": f"Booking {booking_ref} cancelled. Seat released."}


# ─────────────────────────────────────────────
#  Flask API
# ─────────────────────────────────────────────

app = Flask(__name__)


@app.before_request
def on_request_start():
    _scaler.request_start()


@app.teardown_request
def on_request_end(exc):
    _scaler.request_end()


@app.route("/api/routes", methods=["GET"])
def list_routes():
    return jsonify({"routes": ROUTES})


@app.route("/api/availability", methods=["GET"])
def check_availability():
    route_id    = request.args.get("route_id")
    travel_date = request.args.get("date")
    if not route_id or not travel_date:
        return jsonify({"error": "route_id and date are required."}), 400
    if route_id not in ROUTES:
        return jsonify({"error": "Invalid route."}), 404

    seed_seats(route_id, travel_date)
    available = _DB.execute(
        "SELECT COUNT(*) FROM seat_inventory WHERE route_id=? AND travel_date=? AND status='AVAILABLE'",
        (route_id, travel_date)
    ).fetchone()[0]

    return jsonify({
        "route_id":       route_id,
        "date":           travel_date,
        "available_seats": available,
        "fare":           ROUTES[route_id]["fare"],
    })


@app.route("/api/book", methods=["POST"])
def book():
    data = request.get_json()
    required = ["passenger", "phone", "route_id", "travel_date"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    result = book_ticket(
        passenger   = data["passenger"],
        phone       = data["phone"],
        route_id    = data["route_id"],
        travel_date = data["travel_date"],
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/validate", methods=["POST"])
def validate():
    data = request.get_json()
    booking_ref = data.get("booking_ref", "")
    token       = data.get("token", "")
    if not booking_ref or not token:
        return jsonify({"error": "booking_ref and token are required."}), 400
    result = validate_ticket(booking_ref, token)
    code   = 200 if result.get("valid") else 400
    return jsonify(result), code


@app.route("/api/cancel", methods=["POST"])
def cancel():
    data        = request.get_json()
    booking_ref = data.get("booking_ref", "")
    result      = cancel_ticket(booking_ref)
    code        = 400 if "error" in result else 200
    return jsonify(result), code


@app.route("/api/scaling", methods=["GET"])
def scaling_status():
    return jsonify({"auto_scaling": _scaler.status()})


@app.route("/api/bookings", methods=["GET"])
def all_bookings():
    rows = _DB.execute(
        "SELECT booking_ref, passenger, route_id, travel_date, seat_number, fare_locked, status FROM bookings ORDER BY id DESC LIMIT 100"
    ).fetchall()
    bookings = [
        {"ref": r[0], "passenger": r[1], "route": r[2], "date": r[3],
         "seat": r[4], "fare": r[5], "status": r[6]}
        for r in rows
    ]
    return jsonify({"total": len(bookings), "bookings": bookings})


# ─────────────────────────────────────────────
#  CLI Demo
# ─────────────────────────────────────────────

def run_demo():
    print("\n Sunny Lakhwani's Task 3: Cloud-Based Bus Pass System\n")

    print("── Available Routes ────────────────────────────────────────")
    for rid, r in ROUTES.items():
        print(f"  {rid}  {r['from']:<12} → {r['to']:<14}  PKR {r['fare']:>5}  ({r['seats']} seats)")
    print()

    travel_date = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")

    print(f"── Booking Demo  (travel date: {travel_date}) ──────────────")

    # Book 3 tickets
    bookings = []
    for passenger, phone, route in [
        ("Ahmed Raza",    "+92-300-1234567", "R001"),
        ("Sara Khan",     "+92-321-9876543", "R002"),
        ("Bilal Mahmood", "+92-333-5556677", "R001"),
    ]:
        result = book_ticket(passenger, phone, route, travel_date)
        if "error" in result:
            print(f"{passenger}: {result['error']}")
        else:
            bookings.append(result)
            print(f"    {result['booking_ref']}  |  {passenger:<16}  |  {result['route']}")
            print(f"     Seat {result['seat_number']}  |  PKR {result['fare_locked']}  |  Token: {result['token'][:20]}...")
    print()

    # Validate first ticket
    if bookings:
        b = bookings[0]
        print("── Ticket Validation ───────────────────────────────────────")
        v = validate_ticket(b["booking_ref"], b["token"])
        print(f"  {'Yes' if v['valid'] else 'Not'}  {v.get('message', v.get('reason'))}")

        # Try to use the same ticket again (theft simulation)
        v2 = validate_ticket(b["booking_ref"], b["token"])
        print(f"  Re-use attempt: {'Done' if v2['valid'] else 'BLOCKED'}  {v2.get('reason', '')}")
        print()

    # Cancel last booking
    if len(bookings) >= 3:
        c = cancel_ticket(bookings[2]["booking_ref"])
        print("── Cancellation ────────────────────────────────────────────")
        print(f"  {c['message']}")
        print()

    # Auto-scaling status
    print("── Auto-Scaling Status ─────────────────────────────────────")
    s = _scaler.status()
    print(f"  Instances: {s['instances']}  |  Active Requests: {s['active_requests']}  |  Load: {s['load_percent']}%")
    print()
    print("System is cloud-ready. Run with --serve to start the REST API.\n")


if __name__ == "__main__":
    import sys
    if "--serve" in sys.argv:
        print("Starting Bus Pass API on http://0.0.0.0:5001 ...")
        app.run(host="0.0.0.0", port=5001, debug=False)
    else:
        run_demo()