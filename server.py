import os
import hmac
import secrets
import time
from threading import Lock
from http.cookies import SimpleCookie, CookieError
from database import init_db
from auth import (
    register_student,
    authenticate_student,
    create_session,
    get_session_student,
    delete_session,
)
import json
import urllib.request
import urllib.error

from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
PUBLIC_ORIGIN = os.environ.get(
    "PUBLIC_ORIGIN",
    f"http://{HOST}:{PORT}"
).rstrip("/")

COOKIE_SECURE = (
    "; Secure" if PUBLIC_ORIGIN.startswith("https://") else ""
)

MODEL = "qwen2.5:7b"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "")
TEACHER_SESSIONS = {}
TEACHER_LOGIN_ATTEMPTS = {}
TEACHER_LOCK = Lock()
TEACHER_SESSION_SECONDS = 1800

PUBLIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/style.css": "style.css",
    "/engine.js": "engine.js",
    "/app.js": "app.js"
}

EXAMPLES = {
    "Қосу және азайту": (
        "240 + 130 = 370. "
        "200 + 100 = 300. "
        "40 + 30 = 70. "
        "300 + 70 = 370."
    ),
    "Көбейту және бөлу": (
        "6 × 3 = 18. "
        "6 + 6 + 6 = 18. "
        "18 ÷ 3 = 6."
    ),
    "Мәтінді есеп": (
        "3 қораптың әрқайсысында 6 қарындаш бар. "
        "Барлығы: 3 × 6 = 18 қарындаш."
    )
}


class SmartHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, status, data, cookie=None):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

        if cookie is not None:
            self.send_header("Set-Cookie", cookie)

        self.end_headers()
        self.wfile.write(content)
    def get_session_token(self):
        cookies = SimpleCookie()

        try:
            cookies.load(self.headers.get("Cookie", ""))
        except CookieError:
            return ""

        session = cookies.get("smart_session")
        return session.value if session else ""

    def current_student(self):
        token = self.get_session_token()
        return get_session_student(token)
    def current_teacher(self):
        cookies = SimpleCookie()

        try:
            cookies.load(self.headers.get("Cookie", ""))
        except CookieError:
            return False

        cookie = cookies.get("smart_teacher")
        if cookie is None:
            return False

        token = cookie.value

        with TEACHER_LOCK:
            expires = TEACHER_SESSIONS.get(token, 0)

            if expires <= time.monotonic():
                TEACHER_SESSIONS.pop(token, None)
                return False

        return True

    def select_file(self):
        path = self.path.split("?", 1)[0]
        if path not in PUBLIC_FILES:
            self.send_error(404)
            return False
        self.path = "/" + PUBLIC_FILES[path]
        return True

    def do_GET(self):
        if self.path == "/api/teacher/me":
            self.send_json(200, {
                "teacher": self.current_teacher()
            })
            return

        if self.path == "/api/me":
            student = self.current_student()
            self.send_json(200, {"student": student})
            return

        if self.select_file():
            super().do_GET()

    def do_HEAD(self):
        if self.select_file():
            super().do_HEAD()
    def handle_auth_post(self):
        if self.headers.get("Origin") != PUBLIC_ORIGIN:
            self.send_json(403, {"error": "Сұрауға рұқсат жоқ."})
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError()

            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "Сұрау дұрыс берілмеген."})
            return

        if self.path == "/api/logout":
            delete_session(self.get_session_token())
            self.send_json(
                200,
                {"message": "Аккаунттан шықтыңыз."},
                cookie=(
                    "smart_session=; Path=/; HttpOnly; "
                    "SameSite=Strict; Max-Age=0"
                )
            )
            return

        login = data.get("login")
        password = data.get("password")

        try:
            if self.path == "/api/register":
                student = register_student(login, password)
            else:
                student = authenticate_student(login, password)
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return

        delete_session(self.get_session_token())
        token = create_session(student["id"])

        self.send_json(
            200,
            {"student": student},
            cookie=(
                f"smart_session={token}; Path=/; HttpOnly; "
                f"SameSite=Strict; Max-Age=28800{COOKIE_SECURE}"
            )
        )
    def handle_teacher_login(self):
        if self.headers.get("Origin") != PUBLIC_ORIGIN:
            self.send_json(403, {"error": "Сұрауға рұқсат жоқ."})
            return

        if not TEACHER_PASSWORD:
            self.send_json(503, {
                "error": "Мұғалім құпиясөзі серверде орнатылмаған."
            })
            return

        now = time.monotonic()
        address = self.client_address[0]

        with TEACHER_LOCK:
            for key, (_, until) in list(TEACHER_LOGIN_ATTEMPTS.items()):
                if until <= now:
                    del TEACHER_LOGIN_ATTEMPTS[key]

            count, until = TEACHER_LOGIN_ATTEMPTS.get(
                address, (0, now + 300)
            )
            blocked = count >= 5

            if not blocked:
                TEACHER_LOGIN_ATTEMPTS[address] = (count + 1, until)

        if blocked:
            self.send_json(429, {
                "error": "Кіру әрекеті тым көп. 5 минуттан кейін қайталаңыз."
            })
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError()

            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()

            password = data.get("password")
            if not isinstance(password, str):
                raise ValueError()
        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "Сұрау дұрыс берілмеген."})
            return

        if not hmac.compare_digest(
            password.encode("utf-8"),
            TEACHER_PASSWORD.encode("utf-8")
        ):
            self.send_json(401, {"error": "Құпиясөз қате."})
            return

        token = secrets.token_urlsafe(32)

        with TEACHER_LOCK:
            for key, expires in list(TEACHER_SESSIONS.items()):
                if expires <= now:
                    del TEACHER_SESSIONS[key]

            TEACHER_SESSIONS[token] = now + TEACHER_SESSION_SECONDS
            TEACHER_LOGIN_ATTEMPTS.pop(address, None)

        self.send_json(
            200,
            {"teacher": True},
            cookie=(
                f"smart_teacher={token}; Path=/; HttpOnly; "
                f"SameSite=Strict; Max-Age={TEACHER_SESSION_SECONDS}"
                f"{COOKIE_SECURE}"
            )
        )

    def handle_teacher_logout(self):
        if self.headers.get("Origin") != PUBLIC_ORIGIN:
            self.send_json(403, {"error": "Сұрауға рұқсат жоқ."})
            return

        cookies = SimpleCookie()

        try:
            cookies.load(self.headers.get("Cookie", ""))
        except CookieError:
            cookies = SimpleCookie()

        cookie = cookies.get("smart_teacher")

        if cookie is not None:
            with TEACHER_LOCK:
                TEACHER_SESSIONS.pop(cookie.value, None)

        self.send_json(
            200,
            {"teacher": False},
            cookie=(
                "smart_teacher=; Path=/; HttpOnly; "
                f"SameSite=Strict; Max-Age=0{COOKIE_SECURE}"
            )
        )

    def do_POST(self):
        if self.path == "/api/teacher/logout":
            self.handle_teacher_logout()
            return

        if self.path == "/api/teacher/login":
            self.handle_teacher_login()
            return



        if self.path in ("/api/register", "/api/login", "/api/logout"):
            self.handle_auth_post()
            return

        if self.path != "/api/explain":
            self.send_json(404, {"error": "Сұрау жолы табылмады."})
            return

        origin = self.headers.get("Origin")
        if origin and origin != PUBLIC_ORIGIN:
            self.send_json(403, {"error": "Сұрауға рұқсат жоқ."})
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError()

            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()

            topic = data.get("topic")
            if not isinstance(topic, str) or topic not in EXAMPLES:
                raise ValueError()

            action = data.get("action", "explain")
            if action not in ("explain", "tasks"):
                raise ValueError()

            level = data.get("level", 1)
            if type(level) is not int or level not in (1, 2, 3):
                raise ValueError()

        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "Тақырып дұрыс берілмеген."})
            return

        if not self.current_teacher():
            self.send_json(401, {
                 "error": "Алдымен мұғалім құпиясөзімен кіріңіз."
            })
            return

        prompt = (
            "Сен бастауыш сыныптың математика мұғалімісің.\n"
            "Оқушыға қазақ тілінде қысқа түсіндірме жаз.\n"
            "Үлгі: 20 + 30 = 50. "
            "2 ондыққа 3 ондықты қоссақ, 5 ондық шығады. "
            "Сондықтан жауап — 50.\n"
            f"Тақырып: {topic}\n"
            f"Түсіндіретін мысал: {EXAMPLES[topic]}\n"
            "Осы үлгіге ұқсас үш сөйлемдік түсіндірме:"
        )
        if action == "tasks":
            requirements = {
                1: "Бір амалдық жеңіл есептер. Сандар 100-ден аспасын.",
                2: "Екі амалдық есептер. Сандар 1000-нан аспасын.",
                3: "Екі немесе үш амалдық күрделірек есептер. "
                   "Сандар 1000-нан аспасын."
            }

            prompt = (
                "3-сынып математикасынан қазақ тілінде "
                "бір-біріне ұқсамайтын 3 жаңа есеп құрастыр.\n"
                f"Тақырып: {topic}\n"
                f"Деңгей: {level}\n"
                f"Талап: {requirements[level]}\n"
                "Көбейту мен бөлуде көбейту кестесін қолдан. "
                "Бөлу қалдықсыз болсын. "
                "Әр жауап теріс емес бүтін сан болсын. "
                "Сұрақ мәтінінде дайын жауапты көрсетпе. "
                "hint өрісіне жауапты ашпайтын көмек жаз.\n"
                "Тек JSON объектісін қайтар, Markdown қолданба. "
                'Құрылымы: {"tasks": ['
                '{"q": "Есептің сұрағы", '
                '"answer": 12, "hint": "Көмек"}'
                "]}. tasks ішінде дәл 3 есеп болсын."
            )
        if action == "tasks":
            prompt += (
                "\nӘр есепке visual өрісін қос. "
                "Егер мәтінді есепте бірдей топтар саны және "
                "әр топтағы заттар саны беріліп, жалпы саны сұралса, "
                "visual объектісін бер. "
                "Тек алма, қарындаш, кітап немесе доп қолдан. "
                "Құрылымы: "
                '{"kind": "equal_groups", "item": "pencil", '
                '"groups": 3, "perGroup": 6}. '
                "item мәндері: apple, pencil, book, ball. "
                "groups — 1-ден 6-ға дейінгі бүтін сан. "
                "perGroup — 1-ден 10-ға дейінгі бүтін сан. "
                "Бұл сандар есептің шартында дәл берілсін. "
                "Сызбаға белгісіз жауапты енгізбе. "
                "Бөлу, қосу, азайту немесе бірнеше амалдық "
                "есептерде visual: null бер. "
                "Сәйкес сызба жасау мүмкін болмаса да "
                "visual: null бер. "
                "Есептің тақырыбы мен деңгейін сақтау маңызды."
            )

        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        request = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-3.5-flash-lite:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            },
            method="POST"
        )

        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({})
            )

            with opener.open(request, timeout=120) as response:
                result = json.load(response)

            if not isinstance(result, dict):
                raise ValueError()

            candidates = result.get("candidates") or []
            answer = ""

            if candidates:
                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []
                answer = "".join(
                    part["text"]
                    for part in parts
                    if isinstance(part, dict)
                    and isinstance(part.get("text"), str)
                    and not part.get("thought", False)
                )
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError()
            if action == "tasks":
                generated = json.loads(answer)
                if not isinstance(generated, dict):
                    raise ValueError()

                tasks = generated.get("tasks")
                if not isinstance(tasks, list) or len(tasks) != 3:
                    raise ValueError()

                checked = []
                questions = set()

                for task in tasks:
                    if not isinstance(task, dict):
                        raise ValueError()

                    q = task.get("q")
                    value = task.get("answer")
                    hint = task.get("hint")

                    if not isinstance(q, str) or not 5 <= len(q.strip()) <= 600:
                        raise ValueError()
                    if type(value) is not int or not 0 <= value <= 10000:
                        raise ValueError()
                    if not isinstance(hint, str) or not 1 <= len(hint.strip()) <= 400:
                        raise ValueError()
                    if q.strip() in questions:
                        raise ValueError()

                    questions.add(q.strip())
                    visual = None
                    candidate = task.get("visual")

                    if (
                        topic == "Мәтінді есеп"
                        and isinstance(candidate, dict)
                        and candidate.get("kind") == "equal_groups"
                        and candidate.get("item") in (
                            "apple", "pencil", "book", "ball"
                        )
                    ):
                        groups = candidate.get("groups")
                        per_group = candidate.get("perGroup")

                        if (
                            type(groups) is int
                            and type(per_group) is int
                            and 1 <= groups <= 6
                            and 1 <= per_group <= 10
                            and groups * per_group == value
                        ):
                            visual = {
                                "kind": "equal_groups",
                                "item": candidate["item"],
                                "groups": groups,
                                "perGroup": per_group
                            }

                    checked.append({
                        "q": q.strip(),
                        "answer": value,
                        "hint": hint.strip(),
                        "topic": list(EXAMPLES).index(topic),
                        "level": level,
                        "visual": visual
                    })

                self.send_json(200, {"tasks": checked})
                return
            self.send_json(200, {
                "text": answer.strip(),
                "source": "ЖИ жауабы. Мұғалім тексеруі қажет."
            })

        except urllib.error.HTTPError as error:
            message = (
                "ЖИ моделі табылмады."
                if error.code == 404
                else "ЖИ қызметі сұрауды орындай алмады."
            )
            self.send_json(503, {"error": message})

        except (OSError, ValueError):
            self.send_json(503, {
                "error": (
                    "ЖИ жауабы алынбады. "
                    "Ollama іске қосылғанын тексеріңіз."
                )
            })


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), SmartHandler)
    print(f"Сайт: http://{HOST}:{PORT}")
    print("Тоқтату үшін Ctrl + C басыңыз.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер тоқтатылды.")
    finally:
        server.server_close()