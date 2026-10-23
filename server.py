import os
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
    def select_file(self):
        path = self.path.split("?", 1)[0]
        if path not in PUBLIC_FILES:
            self.send_error(404)
            return False
        self.path = "/" + PUBLIC_FILES[path]
        return True

    def do_GET(self):
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
    def do_POST(self):
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

        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "Тақырып дұрыс берілмеген."})
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

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }

        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
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

            answer = result.get("response", "")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError()

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