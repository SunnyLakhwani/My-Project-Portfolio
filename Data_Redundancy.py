import sqlite3
import hashlib
import json
import re
from datetime import datetime
from difflib import SequenceMatcher


# ─────────────────────────────────────────────
#  Database Setup
# ─────────────────────────────────────────────

def init_db(db_path="cloud_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Main data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            phone       TEXT,
            city        TEXT,
            data_hash   TEXT UNIQUE NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)

    # Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            action      TEXT NOT NULL,
            record_data TEXT,
            reason      TEXT,
            timestamp   TEXT NOT NULL
        )
    """)

    conn.commit()
    return conn


# ─────────────────────────────────────────────
#  Hashing & Similarity
# ─────────────────────────────────────────────

def compute_hash(record: dict) -> str:
    """Generate a SHA-256 fingerprint for a record (case-insensitive, stripped)."""
    normalized = {
        "name":  record.get("name", "").strip().lower(),
        "email": record.get("email", "").strip().lower(),
        "phone": re.sub(r"\D", "", record.get("phone", "")),
        "city":  record.get("city", "").strip().lower(),
    }
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def similarity_score(a: str, b: str) -> float:
    """Return string similarity ratio between 0 and 1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ─────────────────────────────────────────────
#  Validation
# ─────────────────────────────────────────────

def validate_record(record: dict) -> tuple[bool, str]:
    """Check that required fields are present and properly formatted."""
    name  = record.get("name", "").strip()
    email = record.get("email", "").strip()
    phone = record.get("phone", "").strip()

    if not name or len(name) < 2:
        return False, "Name is missing or too short."

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, f"Email '{email}' is not valid."

    if phone and not re.match(r"^\+?[\d\s\-]{7,15}$", phone):
        return False, f"Phone '{phone}' has an invalid format."

    return True, "OK"


# ─────────────────────────────────────────────
#  Core Logic
# ─────────────────────────────────────────────

def is_exact_duplicate(conn, data_hash: str) -> bool:
    """Exact duplicate check via SHA-256 hash."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM records WHERE data_hash = ?", (data_hash,))
    return cursor.fetchone() is not None


def is_fuzzy_duplicate(conn, record: dict, threshold: float = 0.85) -> tuple[bool, str]:
    """
    Near-duplicate check using name + email similarity.
    Returns (is_duplicate, reason_message).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name, email FROM records")
    rows = cursor.fetchall()

    new_name  = record.get("name", "").strip()
    new_email = record.get("email", "").strip()

    for (existing_name, existing_email) in rows:
        name_sim  = similarity_score(new_name, existing_name)
        email_sim = similarity_score(new_email, existing_email)

        if email_sim >= 0.95:
            return True, f"Email '{new_email}' closely matches existing '{existing_email}' (sim={email_sim:.2f})."

        if name_sim >= threshold and email_sim >= 0.70:
            return True, (
                f"Record '{new_name}' / '{new_email}' is near-duplicate of "
                f"'{existing_name}' / '{existing_email}' "
                f"(name_sim={name_sim:.2f}, email_sim={email_sim:.2f})."
            )

    return False, ""


def log_action(conn, action: str, record: dict, reason: str = ""):
    """Append an entry to the audit log."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (action, record_data, reason, timestamp) VALUES (?, ?, ?, ?)",
        (action, json.dumps(record), reason, datetime.utcnow().isoformat())
    )
    conn.commit()


def add_record(conn, record: dict) -> dict:
    """
    Full pipeline:
      1. Validate fields
      2. Exact-duplicate check (hash)
      3. Fuzzy-duplicate check
      4. Insert unique data
    Returns a result dict with status and message.
    """
    # Step 1 – Validate
    valid, msg = validate_record(record)
    if not valid:
        log_action(conn, "REJECTED_INVALID", record, msg)
        return {"status": "rejected", "reason": f"Validation failed: {msg}"}

    data_hash = compute_hash(record)

    # Step 2 – Exact duplicate
    if is_exact_duplicate(conn, data_hash):
        reason = "Exact duplicate detected via hash comparison."
        log_action(conn, "REJECTED_EXACT_DUPLICATE", record, reason)
        return {"status": "duplicate", "reason": reason}

    # Step 3 – Fuzzy duplicate
    fuzzy, fuzzy_reason = is_fuzzy_duplicate(conn, record)
    if fuzzy:
        log_action(conn, "REJECTED_FUZZY_DUPLICATE", record, fuzzy_reason)
        return {"status": "false_positive", "reason": fuzzy_reason}

    # Step 4 – Insert unique record
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO records (name, email, phone, city, data_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            record["name"].strip(),
            record["email"].strip().lower(),
            record.get("phone", "").strip(),
            record.get("city", "").strip(),
            data_hash,
            datetime.utcnow().isoformat(),
        )
    )
    conn.commit()
    log_action(conn, "INSERTED", record, "Unique record added successfully.")
    return {"status": "inserted", "reason": "Record is unique and has been added."}


# ─────────────────────────────────────────────
#  Reporting
# ─────────────────────────────────────────────

def print_table(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone, city, created_at FROM records")
    rows = cursor.fetchall()
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║                  DATABASE RECORDS (Unique)                  ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    if not rows:
        print("║  (no records yet)                                            ║")
    for row in rows:
        print(f"║  [{row[0]:>2}] {row[1]:<18} {row[2]:<25} {row[5][:10]} ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")


def print_audit(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT action, record_data, reason, timestamp FROM audit_log ORDER BY id")
    rows = cursor.fetchall()
    print("\n═══════════════════════  AUDIT LOG  ═══════════════════════")
    for row in rows:
        rec  = json.loads(row[1])
        name = rec.get("name", "?")
        print(f"  [{row[3][:19]}]  {row[0]:<30}  {name}")
        if row[2] and row[2] != "Unique record added successfully.":
            print(f"    └─ Reason: {row[2]}")
    print("═══════════════════════════════════════════════════════════\n")


# ─────────────────────────────────────────────
#  Demo / Entry Point
# ─────────────────────────────────────────────

def main():
    print("\n Sunny Lakhwani's Task 1: Data Redundancy Removal System\n")

    conn = init_db(":memory:")   # use ":memory:" for demo; swap to a file path in production

    # Sample incoming records (as if arriving from a cloud API)
    incoming_records = [
        {"name": "Alice Johnson",  "email": "alice@example.com",   "phone": "+1-800-555-0101", "city": "New York"},
        {"name": "Bob Smith",      "email": "bob.smith@mail.com",   "phone": "555-0202",        "city": "Chicago"},
        {"name": "Alice Johnson",  "email": "alice@example.com",   "phone": "+1-800-555-0101", "city": "New York"},  # exact dup
        {"name": "alice johnson",  "email": "alice@example.com",   "phone": "18005550101",     "city": "new york"},  # exact dup (normalized)
        {"name": "Alicia Johnson", "email": "alice@example.com",   "phone": "+1-800-555-0101", "city": "New York"},  # fuzzy dup (email match)
        {"name": "Charlie Brown",  "email": "charlie@domain.org",  "phone": "555-0303",        "city": "Houston"},
        {"name": "",               "email": "noemail",             "phone": "abc",             "city": ""},          # invalid
        {"name": "Diana Prince",   "email": "diana@hero.net",      "phone": "+44-20-7946-0958","city": "London"},
        {"name": "Bob  Smith",     "email": "bob.smith@mail.com",  "phone": "555 0202",        "city": "Chicago"},   # near-dup
        {"name": "Eve Torres",     "email": "eve@example.com",     "phone": "555-0505",        "city": "Miami"},
    ]

    print("Processing incoming records...\n")
    for record in incoming_records:
        result = add_record(conn, record)
        icon = {"inserted": "[ADDED]" , "duplicate": "[DUPLICATED]" , "false_positive": "[SIMILAR]" , "rejected": "[Invalid]" }.get(result["status"], "?")
        print(f"  {icon}  [{result['status'].upper():<15}]  {record.get('name', '?'):<20}  {result['reason']}")

    print_table(conn)
    print_audit(conn)

    conn.close()


if __name__ == "__main__":
    main()