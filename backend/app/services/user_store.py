"""
Thread-safe user registry with optional SQLite persistence, token revocation tracking,
sliding-window rate limiter, and security audit event log for ProcessLens authentication.
"""

import time
import uuid
import sqlite3
import threading
import hashlib
import hmac
from typing import Optional, Dict, List, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.auth import hash_password
from app.schemas.auth import UserRole, AuditEvent


class UserStoreUnavailable(RuntimeError):
    """Raised when durable auth state cannot be checked or persisted."""

@dataclass
class UserRecord:
    id: str
    email: str
    name: str
    password_hash: str
    role: str
    created_at: str

def mask_email(email: str) -> str:
    """Mask email for non-sensitive audit logging (e.g. j***@domain.com)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***" if local else "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"

class UserStore:
    """
    Thread-safe user repository supporting in-memory and durable SQLite storage.
    Initialized with environment-configured developer and customer seed accounts.
    """
    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._users_by_email: Dict[str, UserRecord] = {}
        self._users_by_id: Dict[str, UserRecord] = {}
        self._revoked_tokens: Set[str] = set()
        self._audit_events: List[AuditEvent] = []
        self._login_attempts: Dict[str, List[float]] = {}
        self.db_path = db_path if db_path is not None else settings.USER_STORE_DB_PATH
        
        if self.db_path:
            self._init_sqlite()
        self._seed_default_accounts()

    def _init_sqlite(self) -> None:
        """Initialize SQLite database tables for durable storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    jti TEXT PRIMARY KEY,
                    revoked_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_attempts (
                    key_hash TEXT NOT NULL,
                    attempted_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_key_time ON rate_limit_attempts(key_hash, attempted_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_expiry ON rate_limit_attempts(attempted_at)")
            conn.commit()

        # Load existing users from SQLite into memory cache
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, email, name, password_hash, role, created_at FROM users")
            for row in cursor.fetchall():
                user = UserRecord(id=row[0], email=row[1], name=row[2], password_hash=row[3], role=row[4], created_at=row[5])
                self._users_by_email[user.email] = user
                self._users_by_id[user.id] = user

    def _seed_default_accounts(self) -> None:
        """Seed initial developer and customer accounts from settings if not present."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Developer Administrator Account
        dev_email = settings.DEV_ADMIN_EMAIL.strip().lower()
        if dev_email not in self._users_by_email:
            dev_user = UserRecord(
                id=f"usr_dev_{uuid.uuid4().hex[:8]}",
                email=dev_email,
                name="System Developer",
                password_hash=hash_password(settings.DEV_ADMIN_PASSWORD),
                role=UserRole.DEVELOPER,
                created_at=now,
            )
            self._users_by_email[dev_email] = dev_user
            self._users_by_id[dev_user.id] = dev_user
            if self.db_path:
                dev_user = self._save_user_to_db(dev_user)
                self._users_by_email[dev_email] = dev_user
                self._users_by_id[dev_user.id] = dev_user

        # Customer Account
        cust_email = settings.DEMO_CUSTOMER_EMAIL.strip().lower()
        if cust_email not in self._users_by_email:
            cust_user = UserRecord(
                id=f"usr_cust_{uuid.uuid4().hex[:8]}",
                email=cust_email,
                name="Operations Lead",
                password_hash=hash_password(settings.DEMO_CUSTOMER_PASSWORD),
                role=UserRole.CUSTOMER,
                created_at=now,
            )
            self._users_by_email[cust_email] = cust_user
            self._users_by_id[cust_user.id] = cust_user
            if self.db_path:
                cust_user = self._save_user_to_db(cust_user)
                self._users_by_email[cust_email] = cust_user
                self._users_by_id[cust_user.id] = cust_user

    def _save_user_to_db(self, user: UserRecord) -> UserRecord:
        """Persist a seed and return the canonical row if another worker won the race."""
        with sqlite3.connect(self.db_path, timeout=5) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, name, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user.id, user.email, user.name, user.password_hash, user.role, user.created_at)
            )
            row = conn.execute(
                "SELECT id, email, name, password_hash, role, created_at FROM users WHERE email = ?",
                (user.email,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise UserStoreUnavailable("Seed account could not be loaded from durable storage.")
        return UserRecord(id=row[0], email=row[1], name=row[2], password_hash=row[3], role=row[4], created_at=row[5])

    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        """Lookup user by case-insensitive email."""
        clean_email = email.strip().lower()
        with self._lock:
            user = self._users_by_email.get(clean_email)
            if not user and self.db_path:
                # Query DB directly in case another worker inserted it
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT id, email, name, password_hash, role, created_at FROM users WHERE email = ?",
                        (clean_email,)
                    )
                    row = cursor.fetchone()
                    if row:
                        user = UserRecord(id=row[0], email=row[1], name=row[2], password_hash=row[3], role=row[4], created_at=row[5])
                        self._users_by_email[clean_email] = user
                        self._users_by_id[user.id] = user
            return user

    def get_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        """Lookup user by ID."""
        with self._lock:
            user = self._users_by_id.get(user_id)
            if not user and self.db_path:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT id, email, name, password_hash, role, created_at FROM users WHERE id = ?",
                        (user_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        user = UserRecord(id=row[0], email=row[1], name=row[2], password_hash=row[3], role=row[4], created_at=row[5])
                        self._users_by_email[user.email] = user
                        self._users_by_id[user_id] = user
            return user

    def create_customer_user(self, email: str, name: str, password: str) -> UserRecord:
        """
        Register a new user. Role is strictly enforced as CUSTOMER on the server.
        Enforces transactional email uniqueness across threads and worker processes.
        """
        clean_email = email.strip().lower()
        clean_name = name.strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("A valid email address is required.")
        if not clean_name:
            raise ValueError("Name cannot be empty.")
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long.")

        with self._lock:
            if clean_email in self._users_by_email:
                raise ValueError("An account with this email address already exists.")

            user = UserRecord(
                id=f"usr_cust_{uuid.uuid4().hex[:8]}",
                email=clean_email,
                name=clean_name,
                password_hash=hash_password(password),
                role=UserRole.CUSTOMER,  # Never allow public registration of developer role
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            if self.db_path:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "INSERT INTO users (id, email, name, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (user.id, user.email, user.name, user.password_hash, user.role, user.created_at)
                        )
                        conn.commit()
                except sqlite3.IntegrityError:
                    raise ValueError("An account with this email address already exists.")

            self._users_by_email[clean_email] = user
            self._users_by_id[user.id] = user
            return user

    # -------------------------------------------------------------
    # Token Revocation Management
    # -------------------------------------------------------------
    def revoke_token(self, jti: str) -> None:
        """Mark a token ID as revoked (e.g. upon user logout)."""
        if not jti:
            return
        with self._lock:
            if self.db_path:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "INSERT OR IGNORE INTO revoked_tokens (jti, revoked_at) VALUES (?, ?)",
                            (jti, time.time())
                        )
                        conn.commit()
                except sqlite3.Error as exc:
                    raise UserStoreUnavailable("Session state storage is unavailable.") from exc
            self._revoked_tokens.add(jti)

    def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been explicitly revoked."""
        if not jti:
            return False
        with self._lock:
            if jti in self._revoked_tokens:
                return True
            if self.db_path:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.execute("SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,))
                        if cursor.fetchone():
                            self._revoked_tokens.add(jti)
                            return True
                except sqlite3.Error as exc:
                    raise UserStoreUnavailable("Session state storage is unavailable.") from exc
            return False

    # -------------------------------------------------------------
    # Rate Limiting (Sliding Window)
    # -------------------------------------------------------------
    def _rate_limit_key_hash(self, key: str) -> str:
        """Hash identifiers before persistence so raw emails and IPs are not stored."""
        return hmac.new(
            settings.AUTH_SECRET_KEY.encode("utf-8"),
            key.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def consume_rate_limit(self, key: str, max_attempts: int = 5, window_seconds: int = 300) -> bool:
        """Atomically record one attempt if the sliding-window budget allows it."""
        now = time.time()
        if self.db_path:
            key_hash = self._rate_limit_key_hash(key)
            # BEGIN IMMEDIATE serializes check-and-insert across worker processes
            # sharing this local SQLite database.
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.execute("BEGIN IMMEDIATE")
                # Bound retained history while keeping enough time for the longest current window.
                conn.execute("DELETE FROM rate_limit_attempts WHERE attempted_at <= ?", (now - 86400,))
                conn.execute(
                    "DELETE FROM rate_limit_attempts WHERE key_hash = ? AND attempted_at <= ?",
                    (key_hash, now - window_seconds),
                )
                count = conn.execute(
                    "SELECT COUNT(*) FROM rate_limit_attempts WHERE key_hash = ? AND attempted_at > ?",
                    (key_hash, now - window_seconds),
                ).fetchone()[0]
                if count >= max_attempts:
                    conn.commit()
                    return False
                conn.execute(
                    "INSERT INTO rate_limit_attempts (key_hash, attempted_at) VALUES (?, ?)",
                    (key_hash, now),
                )
                conn.commit()
                return True

        with self._lock:
            attempts = [t for t in self._login_attempts.get(key, []) if now - t < window_seconds]
            if len(attempts) >= max_attempts:
                self._login_attempts[key] = attempts
                return False
            attempts.append(now)
            self._login_attempts[key] = attempts
            return True

    def is_rate_limited(self, key: str, max_attempts: int = 5, window_seconds: int = 300) -> bool:
        """Check whether an identifier has exhausted its sliding-window budget."""
        now = time.time()
        if self.db_path:
            key_hash = self._rate_limit_key_hash(key)
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM rate_limit_attempts WHERE key_hash = ? AND attempted_at > ?",
                    (key_hash, now - window_seconds),
                ).fetchone()[0]
            return count >= max_attempts

        with self._lock:
            attempts = [t for t in self._login_attempts.get(key, []) if now - t < window_seconds]
            self._login_attempts[key] = attempts
            return len(attempts) >= max_attempts

    def record_failed_attempt(self, key: str) -> None:
        """Record a failed attempt for legacy callers; use consume_rate_limit for request gates."""
        now = time.time()
        if self.db_path:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.execute(
                    "INSERT INTO rate_limit_attempts (key_hash, attempted_at) VALUES (?, ?)",
                    (self._rate_limit_key_hash(key), now),
                )
                conn.commit()
            return
        with self._lock:
            self._login_attempts.setdefault(key, []).append(now)

    def reset_attempts(self, key: str) -> None:
        """Clear an identifier's budget after successful authentication."""
        if self.db_path:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.execute(
                    "DELETE FROM rate_limit_attempts WHERE key_hash = ?",
                    (self._rate_limit_key_hash(key),),
                )
                conn.commit()
            return
        with self._lock:
            self._login_attempts.pop(key, None)

    # -------------------------------------------------------------
    # Audit Events
    # -------------------------------------------------------------
    def record_audit_event(self, event_type: str, email: str, client_ip: str, details: Optional[str] = None) -> None:
        """Record a sanitized operational audit event."""
        event = AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            email_masked=mask_email(email),
            client_ip=client_ip,
            details=details,
        )
        with self._lock:
            self._audit_events.append(event)
            if len(self._audit_events) > 100:
                self._audit_events = self._audit_events[-100:]

    def get_recent_audit_events(self, limit: int = 50) -> List[AuditEvent]:
        """Return recent audit events in reverse chronological order."""
        with self._lock:
            return list(reversed(self._audit_events[-limit:]))

    def reset_for_tests(self) -> None:
        """Reset the store to initial seed state for test isolation."""
        with self._lock:
            self._users_by_email.clear()
            self._users_by_id.clear()
            self._revoked_tokens.clear()
            self._audit_events.clear()
            self._login_attempts.clear()
            if self.db_path:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("DELETE FROM users")
                        conn.execute("DELETE FROM revoked_tokens")
                        conn.execute("DELETE FROM rate_limit_attempts")
                        conn.commit()
                except Exception:
                    pass
            self._seed_default_accounts()

# Global user repository instance
user_store = UserStore()

