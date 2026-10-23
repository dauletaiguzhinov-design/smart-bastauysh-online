import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS
    ).hex()

    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, rounds, salt, expected = stored_hash.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        if int(rounds) != ITERATIONS:
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(rounds)
        ).hex()

        return hmac.compare_digest(actual, expected)

    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    saved = hash_password("Test-password-123")

    assert verify_password("Test-password-123", saved)
    assert not verify_password("Wrong-password", saved)

    print("Құпиясөзді тексеру дұрыс жұмыс істейді.")
def register_student(login, password):
    import re
    import sqlite3
    from database import connect_db

    if not isinstance(login, str) or not isinstance(password, str):
        raise ValueError("Логин мен құпиясөз мәтін болуы керек.")

    login = login.strip().lower()

    if not re.fullmatch(r"[a-z0-9_]{3,24}", login):
        raise ValueError(
            "Логин 3–24 таңбадан тұруы керек. "
            "Латын әріптерін, сандарды және _ белгісін қолданыңыз."
        )

    if not 10 <= len(password) <= 128:
        raise ValueError("Құпиясөз 10–128 таңбадан тұруы керек.")

    password_hash = hash_password(password)

    try:
        with connect_db() as connection:
            cursor = connection.execute(
                "INSERT INTO students (login, password_hash) VALUES (?, ?)",
                (login, password_hash)
            )

            student_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        raise ValueError("Бұл логин бос емес. Басқа логин таңдаңыз.") from None

    return {"id": student_id, "login": login}
def authenticate_student(login, password):
    from database import connect_db

    if not isinstance(login, str) or not isinstance(password, str):
        raise ValueError("Логин немесе құпиясөз қате.")

    login = login.strip().lower()

    if not 3 <= len(login) <= 24 or not 10 <= len(password) <= 128:
        raise ValueError("Логин немесе құпиясөз қате.")

    with connect_db() as connection:
        student = connection.execute(
            "SELECT id, login, password_hash FROM students WHERE login = ?",
            (login,)
        ).fetchone()

    if student is None:
        # Аккаунт табылмаса да, хэштеу есебін орындаймыз.
        hash_password(password)
        raise ValueError("Логин немесе құпиясөз қате.")

    if not verify_password(password, student["password_hash"]):
        raise ValueError("Логин немесе құпиясөз қате.")

    return {
        "id": student["id"],
        "login": student["login"]
    }
def create_session(student_id):
    import time
    from database import connect_db

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    expires_at = now + 8 * 60 * 60

    with connect_db() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (now,)
        )
        connection.execute(
            """
            INSERT INTO sessions (token_hash, student_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (token_hash, student_id, expires_at)
        )

    return token


def get_session_student(token):
    import time
    from database import connect_db

    if not isinstance(token, str) or not 20 <= len(token) <= 128:
        return None

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with connect_db() as connection:
        student = connection.execute(
            """
            SELECT students.id, students.login
            FROM sessions
            JOIN students ON students.id = sessions.student_id
            WHERE sessions.token_hash = ?
              AND sessions.expires_at > ?
            """,
            (token_hash, int(time.time()))
        ).fetchone()

    return dict(student) if student else None


def delete_session(token):
    from database import connect_db

    if not isinstance(token, str) or not 20 <= len(token) <= 128:
        return

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with connect_db() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash,)
        )