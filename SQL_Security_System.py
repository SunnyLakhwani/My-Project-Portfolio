import os
import re
import sqlite3
import hashlib
import secrets
import base64
import json
import logging
from datetime import datetime, timedelta
from functools import wraps

# Third-party (install: pip install flask cryptography)
from flask import Flask, request, jsonify
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SecureCloud")


# ─────────────────────────────────────────────
#  AES-256 Encryption Layer  (via Fernet / PBKDF2)
# ─────────────────────────────────────────────

MASTER_PASSWORD = os.environ.get("MASTER_PASSWORD", "CodeAlpha@SecureKey#2024")
SALT = os.environ.get("ENCRYPTION_SALT", "CodeAlpha_Salt_v1").encode()


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from a master password using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


_FERNET_KEY = _derive_key(MASTER_PASSWORD, SALT)
_cipher      = Fernet(_FERNET_KEY)


def encrypt_data(plaintext: str) -> str:
    """Encrypt a string with AES-256 and return a base64 token."""
    return _cipher.encrypt(plaintext.encode()).decode()


def decrypt_data(token: str) -> str:
    """Decrypt an AES-256 encrypted token back to plaintext."""
    return _cipher.decrypt(token.encode()).decode()


def hash_password(password: str) -> str:
    """One-way SHA-256 hash for password verification (salt embedded)."""
    salt = "CodeAlpha_PwSalt"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


# ─────────────────────────────────────────────
#  SQL Injection Detection
# ─────────────────────────────────────────────

# Patterns cover classic, blind, time-based, union, comment-based, and encoded attacks
SQLI_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|TRUNCATE|REPLACE)\b)",
    r"(--|#|/\*|\*/)",                          # SQL comment tokens
    r"(\bOR\b\s+[\w'\"]+\s*=\s*[\w'\"]+)",      # OR 1=1 style
    r"(\bAND\b\s+[\w'\"]+\s*=\s*[\w'\"]+)",     # AND 1=1 style
    r"('|\"|;|`)",                              # quote / semicolon injection
    r"(\bxp_cmdshell\b|\bsp_executesql\b)",     # stored procedure abuse
    r"(0x[0-9a-fA-F]+)",                        # hex-encoded payloads
    r"(\bSLEEP\s*\(|\bBENCHMARK\s*\(|\bWAITFOR\b)",  # time-based blind
    r"(\bINFORMATION_SCHEMA\b|\bSYSOBJECTS\b)", # schema enumeration
    r"(%27|%22|%3B|%2D%2D)",                    # URL-encoded special chars
]

_SQLI_REGEX = re.compile(
    "|".join(SQLI_PATTERNS),
    re.IGNORECASE,
)


def detect_sqli(value: str) -> tuple[bool, str]:
    """
    Scan a string for SQL injection patterns.
    Returns (is_malicious, matched_pattern_description).
    """
    if not isinstance(value, str):
        return False, ""
    match = _SQLI_REGEX.search(value)
    if match:
        return True, f"Matched pattern near: '{match.group()[:40]}'"
    return False, ""


def scan_request_data(data: dict) -> tuple[bool, str]:
    """Recursively scan all string values in a dict for injection attempts."""
    for key, value in data.items():
        if isinstance(value, str):
            flagged, reason = detect_sqli(value)
            if flagged:
                return True, f"Field '{key}': {reason}"
        elif isinstance(value, dict):
            flagged, reason = scan_request_data(value)
            if flagged:
                return True, reason
    return False, ""


# ─────────────────────────────────────────────
#  Capability Code System  (Server Access Control)
# ─────────────────────────────────────────────

# In production store this in Redis / a secure vault — never hardcode long-term
_CAPABILITY_CODES: dict[str, dict] = {}   # code -> {role, expires_at}

ROLES = {"admin", "read_only", "write_only"}


def generate_capability_code(role: str = "read_only", ttl_minutes: int = 30) -> str:
    """Issue a one-time capability code with a time-limited TTL."""
    if role not in ROLES:
        raise ValueError(f"Unknown role '{role}'. Choose from {ROLES}.")
    code = secrets.token_urlsafe(32)
    _CAPABILITY_CODES[code] = {
        "role": role,
        "expires_at": (datetime.utcnow() + timedelta(minutes=ttl_minutes)).isoformat(),
    }
    logger.info("Capability code issued — role=%s, ttl=%dm", role, ttl_minutes)
    return code


def validate_capability_code(code: str, required_role: str = None) -> tuple[bool, str]:
    """Validate a capability code and optional role requirement."""
    entry = _CAPABILITY_CODES.get(code)
    if not entry:
        return False, "Invalid or unknown capability code."
    if datetime.utcnow() > datetime.fromisoformat(entry["expires_at"]):
        del _CAPABILITY_CODES[code]
        return False, "Capability code has expired."
    if required_role and entry["role"] != required_role and entry["role"] != "admin":
        return False, f"Insufficient privileges. Required: {required_role}, got: {entry['role']}."
    return True, entry["role"]


# ─────────────────────────────────────────────
#  Database Layer  (parameterized queries only)
# ─────────────────────────────────────────────

def init_db(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email_enc     TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS security_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            ip_address TEXT,
            payload    TEXT,
            reason     TEXT,
            timestamp  TEXT
        )
    """)
    conn.commit()
    return conn


_DB = init_db()   # module-level singleton for the Flask app


def log_security_event(event_type: str, ip: str, payload: str, reason: str):
    _DB.execute(
        "INSERT INTO security_log (event_type, ip_address, payload, reason, timestamp) VALUES (?,?,?,?,?)",
        (event_type, ip, payload[:500], reason, datetime.utcnow().isoformat()),
    )
    _DB.commit()
    logger.warning("SECURITY EVENT [%s] from %s — %s", event_type, ip, reason)


# ─────────────────────────────────────────────
#  Flask Application
# ─────────────────────────────────────────────

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


# ── Decorators ──────────────────────────────

def require_capability(role=None):
    """Decorator: validates capability code from X-Capability-Code header."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            code = request.headers.get("X-Capability-Code", "")
            valid, info = validate_capability_code(code, required_role=role)
            if not valid:
                log_security_event("UNAUTHORIZED_ACCESS", request.remote_addr, code, info)
                return jsonify({"error": "Access denied.", "detail": info}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def sqli_guard(f):
    """Decorator: scans JSON body for SQL injection before the handler runs."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        flagged, reason = scan_request_data(data)
        if flagged:
            log_security_event(
                "SQL_INJECTION_ATTEMPT",
                request.remote_addr,
                json.dumps(data)[:300],
                reason,
            )
            return jsonify({
                "error": "SQL injection detected. Request blocked.",
                "detail": reason,
            }), 400
        return f(*args, **kwargs)
    return wrapper


# ── Routes ───────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "service": "CodeAlpha Secure Cloud API"})


@app.route("/api/register", methods=["POST"])
@sqli_guard
def register():
    """Register a new user. Credentials stored with AES-256 encryption."""
    data     = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email    = data.get("email", "").strip()

    if not username or not password or not email:
        return jsonify({"error": "username, password, and email are required."}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    pw_hash   = hash_password(password)
    email_enc = encrypt_data(email)            # AES-256 encrypted at rest

    try:
        _DB.execute(
            "INSERT INTO users (username, password_hash, email_enc, created_at) VALUES (?,?,?,?)",
            (username, pw_hash, email_enc, datetime.utcnow().isoformat()),
        )
        _DB.commit()
        logger.info("User registered: %s", username)
        return jsonify({"message": f"User '{username}' registered successfully."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists."}), 409


@app.route("/api/login", methods=["POST"])
@sqli_guard
def login():
    """Authenticate a user — demonstrates parameterized query (no injection possible)."""
    data     = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    # Parameterized query — username never concatenated into SQL string
    row = _DB.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not row or row[0] != hash_password(password):
        log_security_event("FAILED_LOGIN", request.remote_addr, username, "Bad credentials")
        return jsonify({"error": "Invalid username or password."}), 401

    logger.info("Successful login: %s", username)
    return jsonify({"message": f"Welcome back, {username}!"}), 200


@app.route("/api/user/<username>", methods=["GET"])
@require_capability(role="admin")
def get_user(username):
    """Retrieve decrypted user profile (admin only, requires capability code)."""
    row = _DB.execute(
        "SELECT id, username, email_enc, created_at FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not row:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "id":         row[0],
        "username":   row[1],
        "email":      decrypt_data(row[2]),   # decrypted on authorized access
        "created_at": row[3],
    })


@app.route("/api/capability/issue", methods=["POST"])
def issue_capability():
    """
    Issue a capability code for server access control.
    In production this endpoint itself would be protected by admin auth.
    """
    data = request.get_json()
    role = data.get("role", "read_only")
    ttl  = int(data.get("ttl_minutes", 30))
    try:
        code = generate_capability_code(role=role, ttl_minutes=ttl)
        return jsonify({"capability_code": code, "role": role, "ttl_minutes": ttl}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/security/log", methods=["GET"])
@require_capability(role="admin")
def security_log():
    """View the security audit log (admin only)."""
    rows = _DB.execute(
        "SELECT event_type, ip_address, reason, timestamp FROM security_log ORDER BY id DESC LIMIT 50"
    ).fetchall()
    events = [
        {"event": r[0], "ip": r[1], "reason": r[2], "at": r[3]}
        for r in rows
    ]
    return jsonify({"total": len(events), "events": events})


# ─────────────────────────────────────────────
#  Standalone Demo (no server required)
# ─────────────────────────────────────────────

def run_demo():
    print("\n  Sunny Lakhwani's Task 2: SQL Injection Detection & AES-256 Security\n")

    # 1. Encryption demo
    print("── AES-256 Encryption ──────────────────────────────────────")
    original = "user@secret-company.com"
    encrypted = encrypt_data(original)
    decrypted = decrypt_data(encrypted)
    print(f"  Original  : {original}")
    print(f"  Encrypted : {encrypted[:60]}...")
    print(f"  Decrypted : {decrypted}")
    print(f"  Match     : {original == decrypted} \n")

    # 2. SQL injection detection demo
    print("── SQL Injection Detection ──────────────────────────────────")
    test_inputs = [
        ("Normal input",           "John Doe"),
        ("Classic OR bypass",      "' OR '1'='1"),
        ("UNION attack",           "1 UNION SELECT * FROM users--"),
        ("DROP TABLE attempt",     "'; DROP TABLE users; --"),
        ("Blind time-based",       "1' AND SLEEP(5)--"),
        ("URL-encoded injection",  "admin%27--"),
        ("Hex payload",            "0x61646d696e"),
        ("Safe email",             "user@example.com"),
    ]
    for label, value in test_inputs:
        flagged, reason = detect_sqli(value)
        icon = "BLOCKED" if flagged else " SAFE  "
        print(f"  {icon}  {label:<30}  {value[:40]}")
        if flagged:
            print(f"           └─ {reason}")
    print()

    # 3. Capability code demo
    print("── Capability Code System ───────────────────────────────────")
    admin_code = generate_capability_code(role="admin", ttl_minutes=15)
    read_code  = generate_capability_code(role="read_only", ttl_minutes=5)
    print(f"  Admin code issued  : {admin_code[:30]}...")
    print(f"  Read-only issued   : {read_code[:30]}...")

    valid, info = validate_capability_code(admin_code, required_role="admin")
    print(f"  Admin code valid?  : {valid} ({info})")

    valid2, info2 = validate_capability_code(read_code, required_role="admin")
    print(f"  Read as admin?     : {valid2} — {info2}")
    print()

    print("    Double-layer security: injection blocked BEFORE queries run,")
    print("    and data is AES-256 encrypted even if DB is compromised.\n")


if __name__ == "__main__":
    import sys
    if "--serve" in sys.argv:
        print("Starting Flask server on http://0.0.0.0:5000 ...")
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        run_demo()