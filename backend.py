#!/usr/bin/env python3
"""Backend for the interactive quantum web app.

Run:
    python3 backend.py

Then open:
    http://127.0.0.1:8010

If that port is already busy, the server automatically tries the next few ports
and prints the URL it picked.
"""

from __future__ import annotations

import json
import re
import hashlib
import hmac
from html import escape
import math
import mimetypes
import os
import secrets
import ssl
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("QUANTUM_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT") or os.environ.get("QUANTUM_PORT", "8010"))
MAX_PORT_TRIES = 20
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DATA_FILE = ROOT / "app_data.json"
SESSION_COOKIE = "quantum_session"
MAX_JSON_BODY_BYTES = 4_500_000
MAX_IMAGE_DATA_URL_CHARS = 4_200_000
SSL_CONTEXT = None
IMAGE_DATA_URL_RE = re.compile(r"^data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+$")
GPT5_MIN_OUTPUT_TOKENS = 3000
OPENAI_LAST_ERROR = ""

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ModuleNotFoundError:
    # Some macOS Python installs do not ship a working CA bundle. This keeps the
    # local learning app able to reach OpenAI instead of failing every AI call.
    SSL_CONTEXT = ssl._create_unverified_context()


EXPERIMENTS = [
    {
        "id": "double-slit",
        "name": "Double Slit",
        "summary": "One particle at a time builds an interference pattern from two possible paths.",
    },
    {
        "id": "light",
        "name": "Wave + Particle Light",
        "summary": "Light spreads like a wave but arrives as individual photon hits.",
    },
    {
        "id": "two-places",
        "name": "Two Places",
        "summary": "A single quantum state can have probability concentrated in two separated regions.",
    },
    {
        "id": "packet",
        "name": "Wave Packet",
        "summary": "A moving packet spreads, reflects, or tunnels depending on the potential.",
    },
    {
        "id": "dna",
        "name": "DNA Lab",
        "summary": "DNA transcription copies DNA into mRNA, and translation reads codons into amino acids.",
    },
]

DEFAULT_DATA = {
    "users": {},
    "sessions": {},
}


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_data() -> dict[str, object]:
    if not DATA_FILE.exists():
        return json.loads(json.dumps(DEFAULT_DATA))
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.loads(json.dumps(DEFAULT_DATA))
    data.setdefault("users", {})
    data.setdefault("sessions", {})
    return data


def save_data(data: dict[str, object]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 160_000)
    return f"{salt}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), f"{salt}:{digest}")


def public_user(user: dict[str, object]) -> dict[str, object]:
    return {
        "email": user.get("email", ""),
        "name": user.get("name", "Learner"),
        "plan": user.get("plan", "free"),
        "settings": user.get("settings", {}),
    }


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def double_slit_intensity(
    y: float,
    separation: float,
    slit_width: float,
    wavelength: float,
    which_path: bool,
) -> float:
    """Fraunhofer-like double-slit pattern, normalized later by caller."""
    wavelength = max(wavelength, 0.02)
    slit_width = max(slit_width, 0.02)
    separation = max(separation, 0.05)

    beta = math.pi * slit_width * y / wavelength
    envelope = 1.0 if abs(beta) < 1e-9 else (math.sin(beta) / beta) ** 2

    if which_path:
        return envelope

    phase = math.pi * separation * y / wavelength
    interference = math.cos(phase) ** 2
    return envelope * interference


def build_double_slit_payload(query: dict[str, list[str]]) -> dict[str, object]:
    separation = clamp(float(query.get("separation", ["1.8"])[0]), 0.4, 4.0)
    slit_width = clamp(float(query.get("slitWidth", ["0.42"])[0]), 0.08, 1.2)
    wavelength = clamp(float(query.get("wavelength", ["0.58"])[0]), 0.18, 1.4)
    which_path = query.get("whichPath", ["false"])[0].lower() == "true"
    samples = int(clamp(float(query.get("samples", ["220"])[0]), 60, 600))

    points = []
    max_value = 0.0
    for i in range(samples):
        t = i / (samples - 1)
        y = -3.0 + t * 6.0
        value = double_slit_intensity(y, separation, slit_width, wavelength, which_path)
        max_value = max(max_value, value)
        points.append({"y": y, "intensity": value})

    if max_value > 0:
        for point in points:
            point["intensity"] = point["intensity"] / max_value

    return {
        "params": {
            "separation": separation,
            "slitWidth": slit_width,
            "wavelength": wavelength,
            "whichPath": which_path,
        },
        "points": points,
        "explanation": (
            "Which-path detection removes the interference term, leaving a smoother two-slit envelope."
            if which_path
            else "With path information hidden, amplitudes from both slits interfere before detection."
        ),
    }


class QuantumHandler(BaseHTTPRequestHandler):
    server_version = "QuantumWeb/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True})
            return
        if parsed.path == "/api/me":
            user = self.current_user()
            self.send_json({"user": public_user(user) if user else None})
            return
        if parsed.path == "/api/experiments":
            self.send_json({"experiments": EXPERIMENTS})
            return
        if parsed.path == "/api/double-slit":
            self.send_json(build_double_slit_payload(parse_qs(parsed.query)))
            return
        if parsed.path == "/api/explain":
            self.send_json(build_explanation(parse_qs(parsed.query)))
            return
        if parsed.path == "/api/problem":
            problem = build_example_problem(parse_qs(parsed.query))
            status = 200 if problem.get("text") else 503
            self.send_json(problem, status=status)
            return
        if parsed.path == "/api/visual":
            visual = build_visual(parse_qs(parsed.query))
            status = 200 if visual.get("svg") else 503
            self.send_json(visual, status=status)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/api/signup", "/api/login", "/api/logout", "/api/settings", "/api/subscription"}:
            payload = self.read_json_body() if parsed.path != "/api/logout" else {}
            if payload is None:
                self.send_json({"error": "Invalid JSON body"}, status=400)
                return
            if parsed.path == "/api/signup":
                self.handle_signup(payload)
                return
            if parsed.path == "/api/login":
                self.handle_login(payload)
                return
            if parsed.path == "/api/logout":
                self.handle_logout()
                return
            if parsed.path == "/api/settings":
                self.handle_settings(payload)
                return
            if parsed.path == "/api/subscription":
                self.handle_subscription(payload)
                return
        if parsed.path == "/api/chat":
            payload = self.read_json_body()
            if payload is None:
                self.send_json({"error": "Invalid JSON body"}, status=400)
                return
            self.send_json(build_chat_response(payload))
            return
        self.send_json({"error": "Not found"}, status=404)

    def read_json_body(self) -> dict[str, object] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > MAX_JSON_BODY_BYTES:
            return None
        try:
            data = self.rfile.read(length)
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def current_session_id(self) -> str | None:
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            if "=" not in part:
                continue
            key, value = part.strip().split("=", 1)
            if key == SESSION_COOKIE and value:
                return value
        return None

    def current_user(self) -> dict[str, object] | None:
        sid = self.current_session_id()
        if not sid:
            return None
        data = load_data()
        sessions = data["sessions"]
        users = data["users"]
        session = sessions.get(sid) if isinstance(sessions, dict) else None
        if not isinstance(session, dict):
            return None
        if float(session.get("expires", 0)) < time.time():
            sessions.pop(sid, None)
            save_data(data)
            return None
        email = session.get("email")
        user = users.get(email) if isinstance(users, dict) else None
        return user if isinstance(user, dict) else None

    def create_session(self, email: str) -> str:
        data = load_data()
        sid = secrets.token_urlsafe(32)
        data["sessions"][sid] = {"email": email, "expires": time.time() + 60 * 60 * 24 * 14}
        save_data(data)
        return sid

    def send_auth_json(self, payload: dict[str, object], sid: str | None = None, clear: bool = False, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        if sid:
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}={sid}; Path=/; SameSite=Lax; HttpOnly; Max-Age=1209600")
        if clear:
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=; Path=/; SameSite=Lax; HttpOnly; Max-Age=0")
        self.end_headers()
        self.wfile.write(data)

    def handle_signup(self, payload: dict[str, object]) -> None:
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        name = str(payload.get("name", "Learner")).strip()[:60] or "Learner"
        if "@" not in email or len(password) < 8:
            self.send_json({"error": "Use a valid email and a password with at least 8 characters."}, status=400)
            return
        data = load_data()
        users = data["users"]
        if email in users:
            self.send_json({"error": "That email already has an account."}, status=409)
            return
        users[email] = {
            "email": email,
            "name": name,
            "password": hash_password(password),
            "plan": "free",
            "settings": {"theme": "dark", "particles": True, "wave": True},
            "created": time.time(),
        }
        save_data(data)
        sid = self.create_session(email)
        self.send_auth_json({"user": public_user(users[email])}, sid=sid)

    def handle_login(self, payload: dict[str, object]) -> None:
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        data = load_data()
        user = data["users"].get(email)
        if not isinstance(user, dict) or not verify_password(password, str(user.get("password", ""))):
            self.send_json({"error": "Invalid email or password."}, status=401)
            return
        sid = self.create_session(email)
        self.send_auth_json({"user": public_user(user)}, sid=sid)

    def handle_logout(self) -> None:
        sid = self.current_session_id()
        if sid:
            data = load_data()
            data["sessions"].pop(sid, None)
            save_data(data)
        self.send_auth_json({"ok": True}, clear=True)

    def handle_settings(self, payload: dict[str, object]) -> None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "Login required."}, status=401)
            return
        settings = payload.get("settings", {})
        if not isinstance(settings, dict):
            self.send_json({"error": "Invalid settings."}, status=400)
            return
        clean = {
            "theme": "dark" if settings.get("theme") != "bright" else "bright",
            "particles": bool(settings.get("particles", True)),
            "wave": bool(settings.get("wave", True)),
        }
        user["settings"] = clean
        data = load_data()
        data["users"][user["email"]] = user
        save_data(data)
        self.send_json({"user": public_user(user)})

    def handle_subscription(self, payload: dict[str, object]) -> None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "Login required."}, status=401)
            return
        plan = str(payload.get("plan", "free")).lower()
        if plan not in {"free", "pro", "lab"}:
            self.send_json({"error": "Unknown plan."}, status=400)
            return
        user["plan"] = plan
        data = load_data()
        data["users"][user["email"]] = user
        save_data(data)
        self.send_json({"user": public_user(user), "message": "Demo subscription updated. No payment was processed."})

    def serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (ROOT / relative).resolve()
        if ROOT not in target.parents and target != ROOT:
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict[str, object], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", os.environ.get("CORS_ORIGIN", "*"))
        self.send_header("Vary", "Origin")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def build_explanation(query: dict[str, list[str]]) -> dict[str, object]:
    mode = query.get("mode", ["double-slit"])[0]
    show_particles = query.get("particles", ["true"])[0].lower() == "true"
    show_wave = query.get("wave", ["true"])[0].lower() == "true"
    which_path = query.get("whichPath", ["false"])[0].lower() == "true"

    local_text = local_explanation(mode, show_particles, show_wave, which_path)
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if api_key and model:
        ai_text = openai_explanation(api_key, model, mode, show_particles, show_wave, which_path, local_text)
        if ai_text:
            return {"title": "AI Explainer", "text": ai_text, "source": "openai"}
        return {
            "title": "AI Explainer",
            "text": f"OpenAI failed: {OPENAI_LAST_ERROR or 'OpenAI returned no usable explanation.'}",
            "source": "openai-error",
            "note": "No local fallback was used.",
        }

    return {"title": "AI Explainer", "text": local_text, "source": "local"}


def build_example_problem(query: dict[str, list[str]]) -> dict[str, object]:
    mode = query.get("mode", ["double-slit"])[0]
    complexity = query.get("complexity", ["beginner"])[0]
    topic = query.get("topic", [""])[0].strip()[:240]
    settings = {
        "particles": query.get("particles", ["true"])[0],
        "wave": query.get("wave", ["true"])[0],
        "whichPath": query.get("whichPath", ["false"])[0],
        "separation": query.get("separation", [""])[0],
        "wavelength": query.get("wavelength", [""])[0],
        "slitWidth": query.get("slitWidth", [""])[0],
    }
    if is_sat_math_request(topic):
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        if api_key and model:
            problem = openai_sat_math_problem(api_key, model, topic, complexity)
            if problem:
                return {"text": problem, "source": "openai"}
            return {
                "error": f"OpenAI SAT math generation failed: {OPENAI_LAST_ERROR or 'OpenAI returned no usable SAT problem.'}",
                "source": "openai-error",
            }
        return {
            "text": local_sat_math_problem(complexity),
            "source": "local",
            "note": "OpenAI is not connected, so a local SAT math problem was generated.",
        }
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if not api_key or not model:
        return {
            "text": local_example_problem(mode, settings, complexity),
            "source": "local",
            "note": "OpenAI is not connected, so a local example problem was generated.",
        }

    problem = openai_example_problem(api_key, model, mode, settings, complexity)
    if problem:
        return {"text": problem, "source": "openai"}

    return {
        "error": f"OpenAI problem generation failed: {OPENAI_LAST_ERROR or 'OpenAI returned no usable problem.'}",
        "source": "openai-error",
    }


def build_visual(query: dict[str, list[str]]) -> dict[str, object]:
    mode = query.get("mode", ["double-slit"])[0]
    topic = query.get("topic", [""])[0].strip()[:240]
    settings = {
        "particles": query.get("particles", ["true"])[0],
        "wave": query.get("wave", ["true"])[0],
        "whichPath": query.get("whichPath", ["false"])[0],
        "separation": query.get("separation", ["1.8"])[0],
        "wavelength": query.get("wavelength", ["0.58"])[0],
        "slitWidth": query.get("slitWidth", ["0.42"])[0],
        "barrierHeight": query.get("barrierHeight", ["0.55"])[0],
    }
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if is_graph_topic(topic):
        return build_function_graph(topic, api_key, model)
    if not api_key or not model:
        return {
            "error": "OpenAI visual generation is not connected. Add OPENAI_API_KEY to .env and restart the server.",
            "source": "unavailable",
        }
    visual = openai_visual(api_key, model, mode, settings, topic)
    if visual:
        return {**visual, "source": "openai"}
    detail = OPENAI_LAST_ERROR or "OpenAI did not return a usable SVG visual."
    return {
        "error": f"OpenAI visual generation failed: {detail}",
        "source": "openai-error",
    }


def visual_title(mode: str) -> str:
    return {
        "double-slit": "Double-Slit Interference Visual",
        "light": "Wave and Particle Light Visual",
        "two-places": "Two-Places Superposition Visual",
        "packet": "Wave Packet Tunneling Visual",
        "dna": "DNA Transcription and Translation Visual",
    }.get(mode, "Quantum Visual")


def local_visual_caption(mode: str, settings: object) -> str:
    if mode == "double-slit":
        return "Two wave paths overlap after the slits, making bright detection bands where probability is strongest."
    if mode == "light":
        return "Light spreads as wavefronts, but the detector records individual photon-like hits."
    if mode == "two-places":
        return "Before measurement, probability can sit in two separated regions; one detection samples one outcome."
    if mode == "packet":
        return "A wave packet can partly reflect from a barrier while a smaller part tunnels through."
    if mode == "dna":
        return "DNA is transcribed into mRNA, then ribosomes translate codons into an amino-acid chain."
    return "The visual shows probability waves guiding where particle detections are likely."


def visual_topic_title(topic: str, mode: str) -> str:
    title = re.sub(
        r"\b(generate|make|create|draw|show|visual|diagram|image|picture|illustration|of|with|about|for|a|an|the|please)\b",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\s+", " ", title).strip(" .:-")
    return (title or visual_title(mode))[:120]


def local_topic_visual_caption(topic: str, title: str) -> str:
    lower = topic.lower()
    if "newton" in lower or "law" in lower or "force" in lower:
        return "Newton's laws connect balanced motion, force equals mass times acceleration, and equal-opposite interactions."
    if "energy" in lower:
        return "Energy changes form while the total stays conserved in an ideal closed system."
    if "gravity" in lower:
        return "Gravity pulls masses together and curves paths into falling, orbiting, or escaping motion."
    return f"A simplified science visual for {title}, generated locally when the AI image call was unavailable."


def svg_text(text: str, x: int, y: int, size: int = 18, color: str = "#eef3fb", weight: int = 700) -> str:
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Aptos, Arial, sans-serif" font-size="{size}" font-weight="{weight}">{escape(text)}</text>'


def svg_caption(text: str) -> str:
    words = escape(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > 74 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "".join(
        f'<text x="48" y="{470 + i * 24}" fill="#a8b3c4" font-family="Aptos, Arial, sans-serif" font-size="16">{line}</text>'
        for i, line in enumerate(lines[:3])
    )


GRAPH_ENV = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "pi": math.pi,
    "e": math.e,
}


def is_graph_topic(topic: str) -> bool:
    lower = topic.lower()
    return bool(
        topic
        and (
            re.search(r"\b(graph|plot)\b", lower)
            or re.search(r"\by\s*=", lower)
            or re.search(r"\bf\s*\(\s*x\s*\)\s*=", lower)
        )
    )


def named_graph_expression(topic: str) -> str | None:
    lower = topic.lower()
    if re.search(r"\brational\b", lower):
        return "(x+1)/(x-2)"
    if re.search(r"\b(sq[a-z]{0,6}\s*(root|toot|rt)|sqrt|radical)\b", lower):
        return "sqrt(x)"
    if re.search(r"\b(logarithmic|log\b|ln\b)", lower):
        return "log(x)"
    if re.search(r"\b(parabola|quadratic)\b", lower):
        return "x**2"
    if re.search(r"\b(sine|sinusoidal)\b", lower):
        return "sin(x)"
    if re.search(r"\b(cosine)\b", lower):
        return "cos(x)"
    if re.search(r"\b(exponential)\b", lower):
        return "exp(x)"
    if re.search(r"\b(linear)\b", lower):
        return "2*x+1"
    if re.search(r"\b(cubic)\b", lower):
        return "x**3"
    return None


def extract_graph_expression(topic: str) -> str:
    text = topic.strip()
    named = named_graph_expression(text)
    if named:
        return named
    patterns = [
        r"f\s*\(\s*x\s*\)\s*=\s*([^,.;\n]+)",
        r"y\s*=\s*([^,.;\n]+)",
        r"(?:graph|plot|function)\s+(?:of\s+)?([^,.;\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1)
            named = named_graph_expression(raw)
            return named or clean_graph_expression(raw)
    return named_graph_expression(text) or "x"


def clean_graph_expression(expr: str) -> str:
    expr = expr.strip().replace("π", "pi").replace("^", "**")
    expr = re.sub(r"^(?:a|an|the)\s+", "", expr, flags=re.IGNORECASE)
    expr = re.split(
        r"\b(?:and|then|please|with|show|explain|label|describe|derivative|differentiate|tangent|slope)\b",
        expr,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    expr = re.sub(r"\bsine\b", "sin", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bcosine\b", "cos", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bln\s*\(", "log(", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\s+", "", expr)
    expr = add_implicit_multiplication(expr)
    if not expr:
        return "x"
    return expr[:90]


def add_implicit_multiplication(expr: str) -> str:
    # Let students type math naturally: 2x, 2 sin(x), x(x+1), or (x+1)(x-1).
    expr = re.sub(r"(?<=[0-9)])(?=[A-Za-z_(])", "*", expr)
    expr = re.sub(r"(?<=x)(?=[0-9(])", "*", expr, flags=re.IGNORECASE)
    expr = re.sub(r"(?<=\))(?=[0-9A-Za-z_(])", "*", expr)
    expr = re.sub(r"(?<=pi)(?=[0-9A-Za-z_(])", "*", expr, flags=re.IGNORECASE)
    expr = re.sub(r"(?<![A-Za-z0-9_])e(?=[0-9(])", "e*", expr)
    return expr


def safe_graph_value(expr: str, x: float) -> float | None:
    if not re.fullmatch(r"[0-9A-Za-z_+\-*/().,\s]*", expr):
        return None
    names = set(re.findall(r"[A-Za-z_]+", expr))
    if not names.issubset(set(GRAPH_ENV) | {"x"}):
        return None
    try:
        value = eval(expr, {"__builtins__": {}}, {**GRAPH_ENV, "x": x})
    except (ArithmeticError, ValueError, OverflowError, NameError, SyntaxError, TypeError):
        return None
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if abs(value) > 1_000_000:
        return None
    return float(value)


def wants_derivative_graph(topic: str) -> bool:
    return bool(re.search(r"\b(derivative|differentiate|dy/dx|f'\s*\(|slope\s+curve)\b", topic, flags=re.IGNORECASE))


def wants_tangent_graph(topic: str) -> bool:
    return bool(re.search(r"\b(tangent|tangent\s+line|slope\s+line)\b", topic, flags=re.IGNORECASE))


def extract_tangent_x(topic: str) -> float:
    match = re.search(
        r"\b(?:at|when|where)?\s*x\s*(?:=|is|equals)\s*(-?\d+(?:\.\d+)?)",
        topic,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(r"\btangent(?:\s+line)?\s+at\s+(-?\d+(?:\.\d+)?)", topic, flags=re.IGNORECASE)
    if not match:
        return 1.0
    value = float(match.group(1))
    return max(-10.0, min(10.0, value))


def numerical_derivative(expr: str, x: float) -> float | None:
    h = 1e-4
    left = safe_graph_value(expr, x - h)
    right = safe_graph_value(expr, x + h)
    if left is None or right is None:
        return None
    value = (right - left) / (2 * h)
    return value if math.isfinite(value) and abs(value) <= 1_000_000 else None


def local_graph_explanation(expr: str, y_min: float, y_max: float) -> str:
    return (
        f"The graph plots y = {expr} from x = -10 to x = 10. "
        f"The visible y-values run from about {y_min:.2f} to {y_max:.2f}, so you can see the function's shape, intercepts, and turning points."
    )


def openai_graph_explanation(api_key: str | None, model: str, expr: str) -> str | None:
    if not api_key or not model:
        return None
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": [
            {"role": "system", "content": "Explain graphed math functions clearly and briefly for a student."},
            {
                "role": "user",
                "content": (
                    f"Explain the graph of y = {expr} in 2 short sentences. "
                    "Mention the main shape and what a student should look for. Do not use markdown."
                ),
            },
        ],
        "max_output_tokens": 260,
    }, 900)
    text = openai_response_text(api_key, payload, timeout=20, retry_tokens=1200)
    return text[:360].strip() if text else None


def svg_wrapped_text(text: str, x: int, y: int, width: int, line_height: int, size: int = 16) -> str:
    words = escape(text).split()
    lines: list[str] = []
    current = ""
    max_chars = max(24, width // max(7, size // 2))
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "".join(
        f'<text x="{x}" y="{y + i * line_height}" fill="#a8b3c4" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="{size}">{line}</text>'
        for i, line in enumerate(lines[:3])
    )


def build_function_graph(topic: str, api_key: str | None, model: str) -> dict[str, object]:
    expr = extract_graph_expression(topic)
    show_derivative = wants_derivative_graph(topic)
    show_tangent = wants_tangent_graph(topic)
    tangent_x = extract_tangent_x(topic)
    samples: list[tuple[float, float]] = []
    for i in range(361):
        x = -10 + (20 * i / 360)
        y = safe_graph_value(expr, x)
        if y is not None:
            samples.append((x, y))
    if len(samples) < 8:
        expr = "x"
        samples = [(-10 + (20 * i / 360), -10 + (20 * i / 360)) for i in range(361)]

    derivative_samples: list[tuple[float, float]] = []
    if show_derivative:
        for i in range(361):
            x = -10 + (20 * i / 360)
            slope = numerical_derivative(expr, x)
            if slope is not None:
                derivative_samples.append((x, slope))

    tangent_samples: list[tuple[float, float]] = []
    tangent_y = safe_graph_value(expr, tangent_x)
    tangent_slope = numerical_derivative(expr, tangent_x)
    if show_tangent and tangent_y is not None and tangent_slope is not None:
        tangent_samples = [
            (x, tangent_y + tangent_slope * (x - tangent_x))
            for x in (-10 + (20 * i / 80) for i in range(81))
        ]

    y_values = [y for _, y in samples] + [y for _, y in derivative_samples] + [y for _, y in tangent_samples]
    y_min = min(y_values + [0])
    y_max = max(y_values + [0])
    if math.isclose(y_min, y_max):
        y_min -= 1
        y_max += 1
    pad = max(0.5, (y_max - y_min) * 0.12)
    y_min -= pad
    y_max += pad

    x0, y0, plot_w, plot_h = 72, 82, 756, 340

    def sx(x: float) -> float:
        return x0 + ((x + 10) / 20) * plot_w

    def sy(y: float) -> float:
        return y0 + ((y_max - y) / (y_max - y_min)) * plot_h

    path_parts: list[str] = []
    for x, y in samples:
        px, py = sx(x), sy(y)
        path_parts.append(("M" if not path_parts else "L") + f"{px:.2f} {py:.2f}")

    def make_path(points: list[tuple[float, float]]) -> str:
        parts: list[str] = []
        for px_value, py_value in points:
            px, py = sx(px_value), sy(py_value)
            parts.append(("M" if not parts else "L") + f"{px:.2f} {py:.2f}")
        return " ".join(parts)

    derivative_path = make_path(derivative_samples)
    tangent_path = make_path(tangent_samples)
    x_axis = sy(0) if y_min <= 0 <= y_max else y0 + plot_h
    y_axis = sx(0)
    grid = []
    for tick in range(-10, 11):
        px = sx(tick)
        opacity = ".16" if tick % 2 == 0 else ".08"
        grid.append(f'<path d="M {px:.2f} {y0} V {y0 + plot_h}" stroke="#46c2ff" stroke-opacity="{opacity}"/>')
        grid.append(f'<text x="{px:.2f}" y="{y0 + plot_h + 24}" text-anchor="middle" fill="#7f91a8" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="11">{tick}</text>')
    for i in range(6):
        py = y0 + (plot_h * i / 5)
        val = y_max - ((y_max - y_min) * i / 5)
        grid.append(f'<path d="M {x0} {py:.2f} H {x0 + plot_w}" stroke="#46c2ff" stroke-opacity=".10"/>')
        grid.append(f'<text x="{x0 - 12}" y="{py + 4:.2f}" text-anchor="end" fill="#7f91a8" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="13">{val:.1f}</text>')

    overlay_notes: list[str] = []
    if derivative_path:
        overlay_notes.append("orange: derivative")
    if tangent_path:
        overlay_notes.append(f"yellow: tangent at x = {tangent_x:g}")
    explanation = openai_graph_explanation(api_key, model, expr) or local_graph_explanation(expr, y_min, y_max)
    if overlay_notes:
        explanation = f"{explanation} Added overlays show {', '.join(overlay_notes)}."
    title = f"Graph of y = {expr}"
    if show_derivative and show_tangent:
        title = f"{title} with derivative and tangent"
    elif show_derivative:
        title = f"{title} with derivative"
    elif show_tangent:
        title = f"{title} with tangent"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 540" role="img">'
        '<defs>'
        '<linearGradient id="graphBg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#071a3b"/><stop offset="1" stop-color="#0a254f"/></linearGradient>'
        '<linearGradient id="graphLine" x1="0" x2="1"><stop stop-color="#73e3a4"/><stop offset=".55" stop-color="#46c2ff"/><stop offset="1" stop-color="#ffc857"/></linearGradient>'
        '<filter id="softGlow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>'
        '<rect width="900" height="540" fill="url(#graphBg)"/>'
        f'<text x="450" y="46" text-anchor="middle" fill="#f8fbff" font-family="Orbitron, Oxanium, Aptos, Arial, sans-serif" font-size="25" font-weight="800">{escape(title)}</text>'
        f'<rect x="{x0}" y="{y0}" width="{plot_w}" height="{plot_h}" rx="10" fill="#061832" stroke="#496981" stroke-opacity=".7"/>'
        + "".join(grid)
        + f'<path d="M {x0} {x_axis:.2f} H {x0 + plot_w}" stroke="#dce7f3" stroke-opacity=".55" stroke-width="2"/>'
        + f'<path d="M {y_axis:.2f} {y0} V {y0 + plot_h}" stroke="#dce7f3" stroke-opacity=".55" stroke-width="2"/>'
        + f'<path d="{" ".join(path_parts)}" fill="none" stroke="url(#graphLine)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" filter="url(#softGlow)"/>'
        + (f'<path d="{derivative_path}" fill="none" stroke="#ff7a59" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="8 8"/>' if derivative_path else "")
        + (f'<path d="{tangent_path}" fill="none" stroke="#ffc857" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>' if tangent_path else "")
        + (f'<circle cx="{sx(tangent_x):.2f}" cy="{sy(tangent_y):.2f}" r="6" fill="#ffc857" stroke="#061832" stroke-width="2"/>' if tangent_path and tangent_y is not None else "")
        + f'<text x="{x0 + plot_w - 6}" y="{y0 + plot_h + 52}" text-anchor="end" fill="#a8b3c4" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="15">x axis: -10 to 10</text>'
        + f'<text x="{x0 + 8}" y="{y0 + 26}" fill="#a8b3c4" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="15">y = {escape(expr)}</text>'
        + ('<text x="720" y="108" fill="#ff7a59" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="14">d/dx curve</text>' if derivative_path else "")
        + (f'<text x="720" y="{130 if derivative_path else 108}" fill="#ffc857" font-family="Oxanium, Aptos, Arial, sans-serif" font-size="14">tangent x={tangent_x:g}</text>' if tangent_path else "")
        + svg_wrapped_text(explanation, 72, 488, 760, 22, 16)
        + "</svg>"
    )
    return {
        "title": title[:120],
        "caption": "Function graph generated from your prompt.",
        "explanation": explanation,
        "svg": svg,
        "source": "graph",
    }


def local_visual_svg(mode: str, settings: object, title: str, caption: str) -> str:
    header = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 540" role="img">'
        '<defs>'
        '<linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#092652"/><stop offset="1" stop-color="#061832"/></linearGradient>'
        '<linearGradient id="blue" x1="0" x2="1"><stop stop-color="#46c2ff"/><stop offset="1" stop-color="#73e3a4"/></linearGradient>'
        '<filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>'
        '<rect width="900" height="540" fill="url(#bg)"/>'
        '<path d="M0 80 H900 M0 160 H900 M0 240 H900 M0 320 H900 M0 400 H900 M90 0 V540 M180 0 V540 M270 0 V540 M360 0 V540 M450 0 V540 M540 0 V540 M630 0 V540 M720 0 V540 M810 0 V540" stroke="#46c2ff" stroke-opacity=".08"/>'
        f'{svg_text(title, 48, 58, 24, "#f8fbff", 800)}'
    )
    footer = svg_caption(caption) + "</svg>"
    if mode == "light":
        body = (
            '<circle cx="185" cy="255" r="10" fill="#ffc857" filter="url(#glow)"/>'
            '<circle cx="185" cy="255" r="54" fill="none" stroke="#46c2ff" stroke-width="3" stroke-opacity=".75"/>'
            '<circle cx="185" cy="255" r="96" fill="none" stroke="#46c2ff" stroke-width="3" stroke-opacity=".48"/>'
            '<circle cx="185" cy="255" r="138" fill="none" stroke="#46c2ff" stroke-width="3" stroke-opacity=".28"/>'
            '<path d="M350 180 C420 105 505 330 580 255 S720 210 790 280" fill="none" stroke="url(#blue)" stroke-width="6" filter="url(#glow)"/>'
            '<circle cx="430" cy="310" r="8" fill="#f8fbff"/><circle cx="565" cy="245" r="8" fill="#f8fbff"/><circle cx="705" cy="220" r="8" fill="#f8fbff"/>'
            f'{svg_text("wavefronts", 90, 420, 16, "#a8b3c4", 650)}{svg_text("photon hits", 650, 160, 16, "#a8b3c4", 650)}'
        )
    elif mode == "two-places":
        body = (
            '<ellipse cx="285" cy="260" rx="120" ry="86" fill="#46c2ff" fill-opacity=".28" stroke="#46c2ff" stroke-width="3" filter="url(#glow)"/>'
            '<ellipse cx="615" cy="260" rx="120" ry="86" fill="#73e3a4" fill-opacity=".22" stroke="#73e3a4" stroke-width="3" filter="url(#glow)"/>'
            '<path d="M385 260 C455 188 507 332 585 260" fill="none" stroke="#ffc857" stroke-width="4" stroke-dasharray="10 12"/>'
            '<circle cx="318" cy="245" r="9" fill="#f8fbff"/><circle cx="593" cy="286" r="9" fill="#f8fbff"/>'
            f'{svg_text("possible region A", 205, 390, 16, "#a8b3c4", 650)}{svg_text("possible region B", 535, 390, 16, "#a8b3c4", 650)}'
        )
    elif mode == "packet":
        body = (
            '<rect x="585" y="118" width="52" height="252" rx="8" fill="#ffc857" fill-opacity=".72"/>'
            '<path d="M90 315 C155 315 155 170 220 170 S285 315 350 315 S415 170 480 170 S545 315 610 315" fill="none" stroke="#46c2ff" stroke-width="6" filter="url(#glow)"/>'
            '<path d="M635 315 C675 315 675 238 715 238 S755 315 795 315" fill="none" stroke="#73e3a4" stroke-width="5" stroke-opacity=".75" filter="url(#glow)"/>'
            '<path d="M330 145 L375 145 L375 122 L430 165 L375 208 L375 185 L330 185 Z" fill="#f8fbff" fill-opacity=".82"/>'
            f'{svg_text("incoming packet", 110, 410, 16, "#a8b3c4", 650)}{svg_text("barrier", 584, 405, 16, "#a8b3c4", 650)}{svg_text("tunneled tail", 675, 410, 16, "#a8b3c4", 650)}'
        )
    else:
        body = (
            '<rect x="260" y="120" width="28" height="250" rx="8" fill="#dce7f3" fill-opacity=".75"/>'
            '<rect x="260" y="190" width="28" height="38" rx="10" fill="#061832"/>'
            '<rect x="260" y="276" width="28" height="38" rx="10" fill="#061832"/>'
            '<path d="M90 252 C150 176 205 328 260 252" fill="none" stroke="#46c2ff" stroke-width="5" filter="url(#glow)"/>'
            '<path d="M288 209 C375 128 478 128 565 209 S708 292 810 210" fill="none" stroke="#46c2ff" stroke-width="4" stroke-opacity=".72"/>'
            '<path d="M288 295 C375 376 478 376 565 295 S708 212 810 294" fill="none" stroke="#73e3a4" stroke-width="4" stroke-opacity=".65"/>'
            '<rect x="760" y="130" width="8" height="250" rx="4" fill="#f8fbff" fill-opacity=".55"/>'
            '<circle cx="770" cy="178" r="7" fill="#ffc857"/><circle cx="770" cy="214" r="5" fill="#f8fbff"/><circle cx="770" cy="255" r="8" fill="#ffc857"/><circle cx="770" cy="302" r="5" fill="#f8fbff"/><circle cx="770" cy="340" r="7" fill="#ffc857"/>'
            f'{svg_text("source", 80, 395, 16, "#a8b3c4", 650)}{svg_text("two slits", 235, 395, 16, "#a8b3c4", 650)}{svg_text("detection screen", 690, 395, 16, "#a8b3c4", 650)}'
        )
    return header + body + footer


def local_topic_visual_svg(topic: str, title: str) -> str:
    lower = topic.lower()
    header = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 540" role="img">'
        '<defs>'
        '<linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#092652"/><stop offset="1" stop-color="#061832"/></linearGradient>'
        '<linearGradient id="cyan" x1="0" x2="1"><stop stop-color="#46c2ff"/><stop offset="1" stop-color="#73e3a4"/></linearGradient>'
        '<filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>'
        '<rect width="900" height="540" fill="url(#bg)"/>'
        '<path d="M0 90 H900 M0 180 H900 M0 270 H900 M0 360 H900 M0 450 H900 M90 0 V540 M180 0 V540 M270 0 V540 M360 0 V540 M450 0 V540 M540 0 V540 M630 0 V540 M720 0 V540 M810 0 V540" stroke="#46c2ff" stroke-opacity=".08"/>'
        f'{svg_text(title, 450, 48, 25, "#f8fbff", 850)}'
    )
    if "newton" in lower or "law" in lower or "force" in lower:
        body = (
            '<rect x="54" y="98" width="244" height="330" rx="14" fill="#102542" stroke="#46c2ff" stroke-opacity=".55"/>'
            '<rect x="328" y="98" width="244" height="330" rx="14" fill="#102542" stroke="#73e3a4" stroke-opacity=".55"/>'
            '<rect x="602" y="98" width="244" height="330" rx="14" fill="#102542" stroke="#ffc857" stroke-opacity=".65"/>'
            f'{svg_text("1. Inertia", 176, 134, 19, "#46c2ff", 850)}'
            '<line x1="92" y1="244" x2="260" y2="244" stroke="#a8b3c4" stroke-width="3"/>'
            '<rect x="132" y="190" width="86" height="54" rx="8" fill="#46c2ff" filter="url(#glow)"/>'
            '<circle cx="151" cy="251" r="10" fill="#f8fbff"/><circle cx="199" cy="251" r="10" fill="#f8fbff"/>'
            '<path d="M92 177 H258" stroke="#73e3a4" stroke-width="5" stroke-linecap="round"/>'
            '<path d="M258 177 l-20 -12 v24 z" fill="#73e3a4"/>'
            f'{svg_text("balanced motion", 96, 302, 16, "#f8fbff", 700)}'
            f'{svg_text("stays steady", 112, 328, 15, "#a8b3c4", 650)}'
            f'{svg_text("2. F = ma", 450, 134, 19, "#73e3a4", 850)}'
            '<line x1="366" y1="250" x2="536" y2="250" stroke="#a8b3c4" stroke-width="3"/>'
            '<rect x="410" y="198" width="82" height="52" rx="8" fill="#73e3a4" filter="url(#glow)"/>'
            '<path d="M364 197 H518" stroke="#ffc857" stroke-width="6" stroke-linecap="round"/>'
            '<path d="M518 197 l-22 -13 v26 z" fill="#ffc857"/>'
            '<path d="M410 300 C442 276 476 276 510 300" fill="none" stroke="#46c2ff" stroke-width="5"/>'
            f'{svg_text("bigger force", 362, 334, 16, "#f8fbff", 700)}'
            f'{svg_text("more acceleration", 356, 360, 15, "#a8b3c4", 650)}'
            f'{svg_text("3. Action-Reaction", 724, 134, 19, "#ffc857", 850)}'
            '<circle cx="690" cy="224" r="38" fill="#46c2ff" filter="url(#glow)"/>'
            '<circle cx="760" cy="224" r="38" fill="#ffc857" filter="url(#glow)"/>'
            '<path d="M724 224 H642" stroke="#73e3a4" stroke-width="6" stroke-linecap="round"/>'
            '<path d="M642 224 l20 -12 v24 z" fill="#73e3a4"/>'
            '<path d="M726 224 H808" stroke="#ff8fab" stroke-width="6" stroke-linecap="round"/>'
            '<path d="M808 224 l-20 -12 v24 z" fill="#ff8fab"/>'
            f'{svg_text("equal forces", 648, 302, 16, "#f8fbff", 700)}'
            f'{svg_text("opposite directions", 630, 328, 15, "#a8b3c4", 650)}'
            f'{svg_text("Newton laws describe how forces change motion.", 72, 486, 17, "#dce7f3", 700)}'
        )
    elif "energy" in lower:
        body = (
            '<path d="M90 370 C190 120 310 120 420 370 S650 620 795 170" fill="none" stroke="url(#cyan)" stroke-width="7" filter="url(#glow)"/>'
            '<circle cx="165" cy="260" r="18" fill="#ffc857" filter="url(#glow)"/>'
            '<circle cx="450" cy="370" r="18" fill="#73e3a4" filter="url(#glow)"/>'
            '<circle cx="750" cy="220" r="18" fill="#46c2ff" filter="url(#glow)"/>'
            f'{svg_text("potential", 114, 188, 18, "#ffc857", 800)}'
            f'{svg_text("kinetic", 404, 430, 18, "#73e3a4", 800)}'
            f'{svg_text("energy transfers", 610, 150, 18, "#46c2ff", 800)}'
            f'{svg_text("Total energy is conserved in an ideal closed system.", 72, 486, 17, "#dce7f3", 700)}'
        )
    else:
        body = (
            '<circle cx="450" cy="250" r="92" fill="#46c2ff" fill-opacity=".18" stroke="#46c2ff" stroke-width="4" filter="url(#glow)"/>'
            '<circle cx="450" cy="250" r="14" fill="#ffc857" filter="url(#glow)"/>'
            '<path d="M450 250 C555 145 682 185 738 302" fill="none" stroke="#73e3a4" stroke-width="5"/>'
            '<path d="M735 302 l-24 -7 18 -18 z" fill="#73e3a4"/>'
            '<path d="M450 250 L588 250" stroke="#ff8fab" stroke-width="5" stroke-linecap="round"/>'
            '<path d="M588 250 l-18 -12 v24 z" fill="#ff8fab"/>'
            f'{svg_text("concept", 396, 382, 18, "#46c2ff", 850)}'
            f'{svg_text("relationship", 588, 230, 16, "#f8fbff", 700)}'
            f'{svg_text("Generated from your image request.", 72, 486, 17, "#dce7f3", 700)}'
        )
    return header + body + "</svg>"


def openai_visual_caption(
    api_key: str,
    model: str,
    mode: str,
    settings: dict[str, str],
    fallback_caption: str,
) -> str | None:
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": [
            {"role": "system", "content": "You write short captions for educational physics diagrams."},
            {
                "role": "user",
                "content": (
                    "Write one clear caption, maximum 24 words, for a generated SVG diagram in a quantum simulator. "
                    f"Mode: {mode}. Settings: {json.dumps(settings)[:800]}. Baseline caption: {fallback_caption}"
                ),
            },
        ],
        "max_output_tokens": 220,
    }, 900)
    text = openai_response_text(api_key, payload, timeout=20, retry_tokens=1600)
    return text[:220].strip() if text else None


def extract_json_object(text: str) -> dict[str, object] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def sanitize_svg(svg: str) -> str | None:
    svg = svg.strip()
    start = svg.find("<svg")
    end = svg.rfind("</svg>")
    if start != -1 and end != -1:
        svg = svg[start : end + len("</svg>")]
    if not svg.startswith("<svg") or "</svg>" not in svg:
        return None
    svg = svg[: svg.rfind("</svg>") + len("</svg>")]
    blocked = ("<script", "javascript:", "onload=", "onclick=", "onerror=", "<foreignObject")
    if any(item.lower() in svg.lower() for item in blocked):
        return None
    if len(svg) > 35_000:
        return None
    if "viewBox" not in svg:
        svg = svg.replace("<svg", '<svg viewBox="0 0 900 540"', 1)
    if "xmlns=" not in svg[:120]:
        svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return svg


def openai_visual(api_key: str, model: str, mode: str, settings: dict[str, str], topic: str = "") -> dict[str, str] | None:
    global OPENAI_LAST_ERROR
    subject = topic.strip() or f"{visual_title(mode)} for the current simulator mode"
    topic_is_specific = bool(topic.strip())
    context_line = (
        f"Requested visual topic: {subject}. "
        "This requested topic is the complete subject of the image. "
        "Do not replace it with the current simulator mode, double slit, quantum interference, DNA, or any other previous topic unless the request itself asks for that. "
        "Ignore simulator settings for this topic-specific image."
        if topic_is_specific
        else f"Requested visual topic: {subject}. Current simulator mode: {mode}. Settings: {json.dumps(settings)[:1000]}."
    )
    prompt = (
        "Generate one original educational physics diagram as inline SVG. "
        "Return only the complete SVG markup and no markdown, no JSON, no explanation. "
        "The SVG must use viewBox 0 0 900 540, no scripts, no external images, no foreignObject. "
        "Use a professional navy science-app style, labeled parts, and simple shapes. "
        "The diagram must show the real physics concept, not abstract decoration. "
        "Layout rules: keep a 40px safe margin, put the title at x=450 y=44 with text-anchor='middle', "
        "make all labels 15-18px, align label text with text-anchor='middle' or 'start', keep labels away from lines and particles, "
        "use short labels under 22 characters, and avoid any overlapping text. "
        "Use Oxanium, Rajdhani, Aptos, Arial, sans-serif as the font stack. "
        "If you need a longer explanation, place it as 2 short lines at the bottom-left inside the safe margin. "
        f"{context_line}"
    )
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You create safe inline SVG educational science diagrams. Return only SVG markup. "
                    "When the user gives a requested visual topic, that topic is authoritative; do not switch to a simulator, double slit, or previous topic."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": 4600,
    }, 5200)
    text = openai_response_text(api_key, payload, timeout=70, retry_tokens=7000)
    if not text:
        OPENAI_LAST_ERROR = OPENAI_LAST_ERROR or "OpenAI returned no visual text."
        return None
    svg = sanitize_svg(text)
    if not svg:
        preview = re.sub(r"\s+", " ", text).strip()[:220]
        OPENAI_LAST_ERROR = f"OpenAI responded, but not with valid safe SVG. Response started with: {preview}"
        return None
    title = re.sub(r"\b(generate|make|create|draw|show|visual|diagram|image|picture|illustration|of|with|about|for|a|an|the)\b", "", topic, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" .:-") or visual_title(mode)
    return {"title": title[:120], "caption": "OpenAI generated this physics visual from your request.", "svg": svg}


def local_explanation(mode: str, show_particles: bool, show_wave: bool, which_path: bool) -> str:
    if mode == "double-slit":
        if which_path:
            text = (
                "The detector is asking which slit the particle used. That path information destroys "
                "the interference pattern, so the screen becomes two broad bands instead of stripes."
            )
        else:
            text = (
                "Each particle lands as one dot, but the probability wave travels through both slits. "
                "Where the waves add, many dots collect; where they cancel, few dots appear."
            )
    elif mode == "light":
        text = (
            "This view shows light wearing both hats. The expanding rings are wavefronts, while each "
            "bright dot is one photon-like detection. The wave predicts where particles tend to arrive."
        )
    elif mode == "two-places":
        text = (
            "The state has two separated probability lobes. A single detection appears in one place, "
            "but before measurement the model keeps both possible regions active."
        )
    elif mode == "dna":
        text = (
            "The coding DNA strand is copied into mRNA by replacing T with U. "
            "Then the ribosome reads the mRNA three bases at a time; each codon maps to an amino acid until a stop codon ends translation."
        )
    else:
        text = (
            "The packet is a moving probability wave. The barrier changes how much reflects and how "
            "much leaks through, which is the visual version of quantum tunneling."
        )

    if not show_wave and show_particles:
        text += " You hid the wave, so you are seeing only the individual sampled outcomes."
    elif show_wave and not show_particles:
        text += " You hid detections, so the view emphasizes the smooth probability field."

    return text


def prepare_openai_payload(model: str, payload: dict[str, object], minimum_tokens: int) -> dict[str, object]:
    payload = dict(payload)
    payload["max_output_tokens"] = max(int(payload.get("max_output_tokens", 0) or 0), minimum_tokens)
    if model.startswith("gpt-5"):
        payload.setdefault("reasoning", {"effort": "minimal"})
    return payload


def extract_openai_text(data: dict[str, object]) -> str | None:
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()

    chunks: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks).strip() or None


def openai_response_text(api_key: str, payload: dict[str, object], timeout: int, retry_tokens: int) -> str | None:
    global OPENAI_LAST_ERROR
    OPENAI_LAST_ERROR = ""

    def send(current_payload: dict[str, object]) -> dict[str, object] | None:
        global OPENAI_LAST_ERROR
        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(current_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                raw = error.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                message = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else ""
                OPENAI_LAST_ERROR = f"HTTP {error.code}: {message or raw[:400]}"
            except Exception:
                OPENAI_LAST_ERROR = f"HTTP {error.code}: {error.reason}"
            return None
        except TimeoutError:
            OPENAI_LAST_ERROR = "The OpenAI request timed out."
            return None
        except URLError as error:
            OPENAI_LAST_ERROR = f"Network error: {error.reason}"
            return None
        except OSError as error:
            OPENAI_LAST_ERROR = f"Connection error: {error}"
            return None
        except json.JSONDecodeError:
            OPENAI_LAST_ERROR = "OpenAI returned a response that was not valid JSON."
            return None

    data = send(payload)
    if not data:
        return None
    text = extract_openai_text(data)
    if text:
        return text

    incomplete = isinstance(data.get("incomplete_details"), dict)
    reason = data.get("incomplete_details", {}).get("reason") if incomplete else ""
    if data.get("status") == "incomplete" and reason == "max_output_tokens":
        retry_payload = dict(payload)
        retry_payload["max_output_tokens"] = max(int(payload.get("max_output_tokens", 0) or 0) * 2, retry_tokens)
        retry_data = send(retry_payload)
        if retry_data:
            return extract_openai_text(retry_data)
    OPENAI_LAST_ERROR = OPENAI_LAST_ERROR or "OpenAI returned no text content."
    return None


def openai_explanation(
    api_key: str,
    model: str,
    mode: str,
    show_particles: bool,
    show_wave: bool,
    which_path: bool,
    fallback_text: str,
) -> str | None:
    if mode == "dna":
        prompt = (
            "Explain this DNA transcription and translation simulator screen in 2-3 short beginner-friendly sentences. "
            "Do not mention quantum waves, particles, probability, or tunneling. "
            f"Baseline explanation: {fallback_text}"
        )
    else:
        prompt = (
            "Explain this quantum simulator screen in 2-3 short beginner-friendly sentences. "
            "Avoid hype and avoid saying the visualization is exact quantum mechanics. "
            f"Mode: {mode}. Wave visible: {show_wave}. Particles visible: {show_particles}. "
            f"Which-path detector: {which_path}. Baseline explanation: {fallback_text}"
        )
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": "You are a careful physics tutor explaining an educational simulator.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": 900,
    }, 1600)
    return openai_response_text(api_key, payload, timeout=20, retry_tokens=GPT5_MIN_OUTPUT_TOKENS)


def wants_example_problem_request(message: str) -> bool:
    lower = message.lower()
    example_words = ("example", "practice", "sample")
    problem_words = ("problem", "question", "exercise")
    simulator_words = (
        "this",
        "current",
        "simulator",
        "simulation",
        "experiment",
        "mode",
        "double slit",
        "wave packet",
        "light mode",
        "dna lab",
    )
    return (
        any(word in lower for word in example_words)
        and any(word in lower for word in problem_words)
        and any(word in lower for word in simulator_words)
    )


def is_schrodinger_request(text: str) -> bool:
    return bool(re.search(r"\bsch(?:r[oö]?|o)?d(?:i|in|ing|inge|inger|enger|ro)?g?er\b|\bschrodinger\b", text, flags=re.IGNORECASE))


def normalize_learning_topic(message: str) -> str:
    return re.sub(
        r"\bsch(?:r[oö]?|o)?d(?:i|in|ing|inge|inger|enger|ro)?g?er\b|\bschrodinger\b",
        "Schrodinger",
        message,
        flags=re.IGNORECASE,
    )


def is_sat_math_request(message: str) -> bool:
    lower = message.lower()
    return bool(
        re.search(r"\bsat\b", lower)
        and any(word in lower for word in ("math", "question", "problem", "practice", "algebra", "geometry", "probability"))
    )


def local_sat_math_problem(complexity: str = "beginner") -> str:
    if "complex" in complexity.lower() or "advanced" in complexity.lower() or "hard" in complexity.lower():
        return (
            "Problem:\n"
            "A rectangle has perimeter 46 units. Its length is 5 units more than twice its width. "
            "What is the area of the rectangle?\n\n"
            "Hint:\n"
            "Use P = 2L + 2W, and write L = 2W + 5.\n\n"
            "Answer:\n"
            "46 = 2(2W + 5) + 2W = 6W + 10, so 36 = 6W and W = 6. "
            "Then L = 2(6) + 5 = 17. The area is A = LW = 17 x 6 = 102 square units."
        )
    return (
        "Problem:\n"
        "A bag has 5 red marbles, 3 blue marbles, and 2 green marbles. If one marble is chosen at random, "
        "what is the probability that it is blue?\n\n"
        "Hint:\n"
        "Probability = favorable outcomes / total outcomes.\n\n"
        "Answer:\n"
        "There are 5 + 3 + 2 = 10 marbles total. There are 3 blue marbles, so the probability is 3/10."
    )


def local_schrodinger_problem() -> str:
    return (
        "Problem:\n"
        "A particle is trapped in a one-dimensional infinite square well of length L. "
        "Write the time-independent Schrodinger equation inside the well and find the allowed energy levels.\n\n"
        "Hint:\n"
        "Inside the well, V(x) = 0, so solve -(hbar^2 / 2m) d^2 psi/dx^2 = E psi with boundary conditions psi(0)=0 and psi(L)=0.\n\n"
        "Answer:\n"
        "The wavefunction must be zero at both walls, so the allowed standing waves are psi_n(x) = sqrt(2/L) sin(n pi x / L), where n = 1, 2, 3, ... . "
        "The allowed energies are E_n = n^2 pi^2 hbar^2 / (2mL^2). "
        "This means the particle cannot have just any energy; confinement makes the energy quantized."
    )


def local_example_problem(mode: str, settings: object, complexity: str = "beginner") -> str:
    complex_requested = "complex" in complexity.lower() or "advanced" in complexity.lower()
    if mode == "double-slit":
        if complex_requested:
            return (
                "Problem:\n"
                "In a simplified double-slit setup, the slit separation is d = 1.8 mm and the light wavelength is "
                "lambda = 600 nm. A screen is L = 2.0 m away. Estimate the distance from the center bright band to "
                "the third bright band. Then explain what would happen to the stripe pattern if a which-path detector "
                "were turned on.\n\n"
                "Hint:\n"
                "Use d sin(theta) = m lambda and, for small angles, y approximately equals L theta.\n\n"
                "Answer:\n"
                "For the third bright band, m = 3. With small angles, y = L m lambda / d. Convert units: "
                "d = 1.8 x 10^-3 m and lambda = 600 x 10^-9 m. "
                "y = (2.0)(3)(600 x 10^-9) / (1.8 x 10^-3) = 0.002 m = 2.0 mm. "
                "Turning on which-path detection removes the interference information, so the clear bright/dark bands fade "
                "into a smoother particle distribution."
            )
        return (
            "Problem:\n"
            "In the double-slit simulator, what happens to the detection pattern when the wavelength gets larger?\n\n"
            "Hint:\n"
            "Larger wavelength makes the wave spread more, so the interference bands move farther apart.\n\n"
            "Answer:\n"
            "The bright bands spread out. The app shows this as wider spacing between the places where particle dots collect."
        )
    if mode == "packet":
        if complex_requested:
            return (
                "Problem:\n"
                "A wave packet moves toward a barrier. In this simulator, raising the barrier height increases reflection. "
                "Describe what should happen to the reflected part and transmitted part when the barrier height changes from "
                "0.25 to 0.85. Then explain why some probability can still appear past the barrier.\n\n"
                "Hint:\n"
                "Think of the packet as probability amplitude. A higher barrier usually reflects more amplitude, but a quantum "
                "packet can still have a small tail through the barrier.\n\n"
                "Answer:\n"
                "At height 0.25, more of the packet should pass through and less should reflect. At height 0.85, more should "
                "reflect and less should transmit. The probability past the barrier represents tunneling: the wavefunction can "
                "extend into and sometimes beyond a barrier even when a classical particle would not cross."
            )
        return (
            "Problem:\n"
            "What should happen when you increase the barrier height in the wave-packet mode?\n\n"
            "Hint:\n"
            "Compare reflection and transmission.\n\n"
            "Answer:\n"
            "More of the packet reflects, and less passes through. A small part may still appear beyond the barrier because the "
            "simulator is showing tunneling."
        )
    if mode == "light":
        return (
            "Problem:\n"
            "The light mode shows rings and dots at the same time. Which part represents wave behavior, and which part "
            "represents particle behavior?\n\n"
            "Hint:\n"
            "Waves spread smoothly; particles arrive as single detections.\n\n"
            "Answer:\n"
            "The rings represent the wave-like spreading of light. The dots represent photon-like detections, where energy is "
            "recorded in individual hits."
        )
    if mode == "dna":
        return (
            "Problem:\n"
            "Given the coding DNA strand ATGGCCATTGTA, transcribe it into mRNA and translate the complete codons into amino acids.\n\n"
            "Hint:\n"
            "For a coding strand, replace T with U to make mRNA, then read the mRNA in groups of three bases.\n\n"
            "Answer:\n"
            "mRNA: AUG GCC AUU GUA. Translation: AUG -> Met, GCC -> Ala, AUU -> Ile, GUA -> Val. "
            "Protein chain: Met - Ala - Ile - Val."
        )
    return (
        "Problem:\n"
        "In the two-places mode, why can the simulator show two bright regions before a detection but only one dot when a "
        "particle is detected?\n\n"
        "Hint:\n"
        "Separate probability before measurement from the outcome after measurement.\n\n"
        "Answer:\n"
        "Before detection, the state has probability in both regions. When a detection happens, the app samples one outcome, "
        "so the dot appears in one place even though the earlier probability pattern had two likely regions."
    )


def openai_example_problem(
    api_key: str,
    model: str,
    mode: str,
    settings: dict[str, str],
    complexity: str = "beginner",
) -> str | None:
    complex_requested = "complex" in complexity.lower() or "advanced" in complexity.lower()
    prompt = (
        f"Create one {'more complex multi-step' if complex_requested else 'beginner-friendly'} practice problem for a science simulator. "
        "Use the current mode and settings. Include exactly these labeled sections:\n"
        "Problem:\nHint:\nAnswer:\n"
        "Keep it accurate and solvable. If math is useful, include equations and show the calculation in the answer. "
        f"Current mode: {mode}. Current settings: {json.dumps(settings)[:1000]}."
    )
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": "You are a careful physics tutor creating short practice problems for a learning app.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": 1800 if complex_requested else 1400,
    }, 2600)
    return openai_response_text(api_key, payload, timeout=45, retry_tokens=4200)


def openai_sat_math_problem(api_key: str, model: str, topic: str, complexity: str = "beginner") -> str | None:
    complex_requested = "complex" in complexity.lower() or "advanced" in complexity.lower() or "hard" in complexity.lower()
    prompt = (
        f"Create one {'harder multi-step' if complex_requested else 'standard'} SAT Math practice question based on this request: {topic}. "
        "Use only SAT Math topics: algebra, linear equations, systems, quadratics, functions, geometry, basic trigonometry, ratios, percentages, statistics, data analysis, or probability. "
        "Do not use calculus, limits, derivatives, integrals, differential equations, partial derivatives, or college math. "
        "Include exactly these labeled sections:\n"
        "Problem:\n"
        "Choices:\n"
        "Hint:\n"
        "Answer:\n"
        "Make the answer choices A-D and show a clear SAT-level solution or make it free response."

    )
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": "You write SAT Math practice only. Never use calculus for SAT Math questions.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": 1700,
    }, 2600)
    return openai_response_text(api_key, payload, timeout=45, retry_tokens=4200)


def build_chat_response(payload: dict[str, object]) -> dict[str, object]:
    message = str(payload.get("message", "")).strip()
    mode = str(payload.get("mode", "double-slit")).strip() or "double-slit"
    settings = payload.get("settings", {})
    history = payload.get("history", [])
    image = payload.get("image")

    valid_image = normalize_chat_image(image)
    if image and not valid_image:
        return {
            "reply": "I could not read that photo. Use a PNG, JPG, or WEBP image under 3 MB.",
            "source": "local",
        }

    if not message and not valid_image:
        return {
            "reply": "Ask me something about the current quantum experiment and I will explain what is happening.",
            "source": "local",
        }

    if valid_image and not message:
        message = "Solve this physics or calculus homework problem step by step."
    message = normalize_learning_topic(message[:1200])
    safe_history = []
    if isinstance(history, list):
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "user"))
            content = str(item.get("content", ""))[:700]
            if role in {"user", "assistant"} and content:
                safe_history.append({"role": role, "content": content})

    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if api_key and model:
        ai_reply = openai_chat(api_key, model, message, mode, settings, safe_history, valid_image)
        if ai_reply:
            return {"reply": ai_reply, "source": "openai"}
        return {
            "reply": f"OpenAI failed: {OPENAI_LAST_ERROR or 'OpenAI returned no usable answer.'}",
            "source": "openai-error",
            "note": "No local fallback was used.",
        }

    source = "local"
    if valid_image:
        note = "OpenAI is required to solve photo homework. Check your API key, billing, and connection."
        return {"reply": note, "source": source, "note": note}
    if wants_example_problem_request(message):
        complexity = "complex" if any(word in message.lower() for word in ("complex", "advanced", "hard", "multi-step", "multistep")) else "beginner"
        note = "OpenAI unavailable; local example problem generated." if api_key else "No API key; local example problem generated."
        return {
            "reply": local_example_problem(mode, settings, complexity),
            "source": source,
            "note": note,
        }
    note = "OpenAI unavailable; local fallback used." if api_key else "No API key; local fallback used."
    return {"reply": local_chat_reply(message, mode, settings), "source": source, "note": note}


def normalize_chat_image(image: object) -> dict[str, str] | None:
    if not isinstance(image, dict):
        return None
    data_url = str(image.get("dataUrl", "")).strip()
    mime_type = str(image.get("type", "")).strip()
    name = str(image.get("name", "attached photo")).strip()[:80] or "attached photo"
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        return None
    if len(data_url) > MAX_IMAGE_DATA_URL_CHARS:
        return None
    if not IMAGE_DATA_URL_RE.match(data_url):
        return None
    return {"dataUrl": data_url, "type": mime_type, "name": name}


def local_chat_reply(message: str, mode: str, settings: object) -> str:
    message = normalize_learning_topic(message)
    lower = message.lower()
    simulator_words = (
        "experiment",
        "simulation",
        "simulator",
        "mode",
        "control",
        "slider",
        "particle",
        "wave",
        "interference",
        "slit",
        "photon",
        "superposition",
        "tunnel",
        "barrier",
        "dna",
        "mrna",
        "codon",
        "transcription",
        "translation",
    )
    general_learning_words = (
        "topic",
        "subject",
        "rational",
        "logarithmic",
        "log",
        "square root",
        "sqrt",
        "radical",
        "function",
        "calculus",
        "algebra",
        "schrodinger",
        "quantum mechanics",
        "chemistry",
        "biology",
        "history",
        "black hole",
        "planet",
        "gravity",
        "linear algebra"
    )
    if is_schrodinger_request(lower) and "problem" in lower:
        return local_schrodinger_problem()
    if is_sat_math_request(lower):
        complexity = "complex" if any(word in lower for word in ("complex", "advanced", "hard", "multi-step", "multistep")) else "beginner"
        return local_sat_math_problem(complexity)
    if re.search(r"\b(rational|logarithmic|log\b|ln\b|square\s*root|sqrt|radical)\b", lower) and re.search(r"\b(solve|explain|give|example|function)\b", lower):
        return (
            "Example function work:\n"
            "1. Rational: f(x) = (x + 1) / (x - 2). Domain: x != 2. Vertical asymptote: x = 2. Horizontal asymptote: y = 1. Zero: x = -1.\n"
            "2. Logarithmic: f(x) = log(x). Domain: x > 0. Vertical asymptote: x = 0. It crosses the x-axis at x = 1.\n"
            "3. Square root: f(x) = sqrt(x). Domain: x >= 0. Range: y >= 0. It starts at (0, 0) and increases slowly.\n"
            "To graph one, type something like: graph rational function, graph log(x), or graph sqrt(x) with tangent at x=4."
        )
    asks_general_topic = any(word in lower for word in general_learning_words) and not any(word in lower for word in simulator_words)
    if asks_general_topic:
        return (
            "OpenAI is needed for a full answer about that separate topic. "
            "The current experiment should not control this answer; ask the same question again after checking the API key or connection."
        )
    wants_equations = any(
        word in lower
        for word in (
            "equation",
            "equations",
            "formula",
            "formulas",
            "math",
            "schrodinger",
            "wavefunction",
            "probability",
            "interference",
        )
    )
    if wants_equations:
        return (
            "Here are useful equations for this simulator:\n"
            "1. Born rule: P(x) = |psi(x)|^2. This means the wave height squared becomes detection probability.\n"
            "2. Schrodinger equation: i hbar dpsi/dt = H psi. This is the rule for how a quantum state changes.\n"
            "3. Free particle Hamiltonian: H = -(hbar^2 / 2m) d^2/dx^2 + V(x).\n"
            "4. Double-slit spacing: bright bands happen near d sin(theta) = m lambda.\n"
            "5. Double-slit intensity: I(theta) is roughly cos^2(pi d sin(theta) / lambda), with a slit-width envelope.\n"
            "The app simplifies these so you can see the idea: waves add, and particles land more often where |psi|^2 is large."
        )
    wants_calculus = any(
        word in lower
        for word in (
            "partial derivative",
            "partial derivatives",
            "double integral",
            "double integrals",
            "gradient",
            "differentiate",
            "integrate",
            "calculus",
            "tripple integral",
            "tripple integrals"
        )
    )
    if wants_calculus:
        return (
            "OpenAI can solve calculus problems step by step when it is connected. "
            "For partial derivatives, treat the other variables as constants and differentiate with respect to the requested variable. "
            "For double integrals, first identify the region, choose an order such as dy dx or dx dy, set the bounds, "
            "integrate the inner variable first, then integrate the outer variable. "
            "Attach a photo or type the exact problem for a full solution."
        )
    wants_code = any(
        word in lower
        for word in (
            "code",
            "coding",
            "program",
            "python",
            "javascript",
            "loop",
            "loops",
            "if statement",
            "if statements",
            "data structure",
            "data structures",
            "array",
            "list",
            "dictionary",
            "dict",
        )
    )
    if wants_code:
        return (
            "OpenAI can write and format code when it is connected. "
            "For data structures, ask for lists, dictionaries, arrays, stacks, queues, or maps. "
            "For loops and if statements, ask for a small program and a language. "
            "For Python, it can include input() so the user can type values when the program runs. "
            "For F = ma, ask for a calculator that takes mass and acceleration inputs, uses if statements to validate them, "
            "and prints force in newtons. For E = mc^2, ask for a calculator that takes mass input, validates it, "
            "uses c = 299792458, and prints energy in joules."
        )
    if "double" in lower or "slit" in lower or mode == "double-slit":
        return (
            "In the double-slit demo, the wave field represents probability amplitude from both openings. "
            "The dots are individual detections; over time they pile up where the combined wave is strongest."
        )
    if "light" in lower or "photon" in lower or mode == "light":
        return (
            "The light demo separates the two ideas: rings show wavefronts spreading out, while the dots show "
            "photon-like arrivals. The wave guides the pattern, but each detection is discrete."
        )
    if "two" in lower or "superposition" in lower or mode == "two-places":
        return (
            "The two-place view is a superposition sketch. Before detection, the state has two likely regions; "
            "when you sample it, a dot appears in one region or the other."
        )
    if "packet" in lower or "tunnel" in lower or "barrier" in lower or mode == "packet":
        return (
            "The wave packet is a moving probability bump. At the barrier, part can reflect and part can leak "
            "through, which is the simplified tunneling effect shown in the app."
        )
    if "dna" in lower or "mrna" in lower or "codon" in lower or "transcription" in lower or "translation" in lower or mode == "dna":
        dna = settings.get("dna", {}) if isinstance(settings, dict) else {}
        if isinstance(dna, dict) and dna.get("codingStrand"):
            mutation = dna.get("mutation")
            mutation_text = ""
            if isinstance(mutation, dict):
                mutation_text = (
                    f" Mutation detected at base {mutation.get('position')}: "
                    f"{mutation.get('from')} -> {mutation.get('to')} in codon {mutation.get('codonNumber')}."
                )
            return (
                f"DNA coding strand: {dna.get('codingStrand')}\n"
                f"mRNA: {dna.get('mrna')}\n"
                f"Codons: {' '.join(dna.get('codons', [])) if isinstance(dna.get('codons'), list) else ''}\n"
                f"Protein: {' - '.join(dna.get('protein', [])) if isinstance(dna.get('protein'), list) else ''}\n"
                f"{mutation_text}\n"
                "This uses the coding-strand rule: transcription changes T to U, then translation reads mRNA codons in groups of three."
            )
        return (
            "In DNA Lab, transcription copies the DNA coding strand into mRNA by changing T to U. "
            "Translation reads the mRNA in three-letter codons, and each codon maps to an amino acid such as AUG -> Met. "
            "Stop codons end the protein chain."
        )
    return (
        "I can explain the active mode, the controls, quantum waves, particle detections, DNA transcription, or codon translation. "
        "Try asking about interference, photons, superposition, tunneling, mRNA, codons, or proteins."
    )


def openai_chat(
    api_key: str,
    model: str,
    message: str,
    mode: str,
    settings: object,
    history: list[dict[str, str]],
    image: dict[str, str] | None = None,
) -> str | None:
    dna_context = ""
    if mode == "dna" and isinstance(settings, dict) and isinstance(settings.get("dna"), dict):
        dna = settings["dna"]
        mutation = dna.get("mutation")
        mutation_line = "No mutation is currently marked."
        if isinstance(mutation, dict):
            mutation_line = (
                f"Marked mutation: base {mutation.get('position')} changed "
                f"from {mutation.get('from')} to {mutation.get('to')} in codon {mutation.get('codonNumber')}."
            )
        dna_context = (
            "\nCurrent DNA Lab state:\n"
            f"Coding DNA strand: {dna.get('codingStrand', '')}\n"
            f"mRNA transcript: {dna.get('mrna', '')}\n"
            f"Codons: {', '.join(dna.get('codons', [])) if isinstance(dna.get('codons'), list) else ''}\n"
            f"Protein chain: {' - '.join(dna.get('protein', [])) if isinstance(dna.get('protein'), list) else ''}\n"
            f"Start codon index: {dna.get('startCodonIndex')} (0-based, -1 means none).\n"
            f"Stop codon index: {dna.get('stopCodonIndex')} (0-based, -1 means none).\n"
            f"{mutation_line}\n"
            "Use this exact DNA state when answering DNA questions."
        )
    context = (
        "You are the AI tutor inside a beginner science simulator web app with quantum physics and DNA biology modes. "
        "You can also solve physics, biology, calculus, math, and beginner coding homework from text or an attached photo. "
        "You can answer or create practice problems for any school topic the user names, including math, science, history, English, coding, chemistry, biology, astronomy, and physics. "
        "When the user names a topic, that named topic is the target. Do not swap it for the current simulator experiment. "
        "For homework, read the problem carefully, restate the goal, list knowns and unknowns when relevant, "
        "choose equations or methods, show steps, include units when the problem has units, and end with a final answer. "
        " If the user doesent ask for an answer let them solve it themselves"
        "If the user asks for a Schrodinger problem, Schrodinger equation problem, or misspells it like 'schodinger', "
        "create or solve a Schrodinger-equation quantum mechanics problem directly; do not replace it with the current simulator experiment. "
        "If the user asks for SAT math, SAT questions, SAT practice, or SAT-style math problems, stay at SAT Math level only: "
        "use algebra, linear equations, systems, quadratics, functions, geometry, trigonometry basics, ratios, percentages, data analysis, statistics, or probability. "
        "Do not use calculus, limits, derivatives, integrals, differential equations, partial derivatives, or advanced college math in SAT math questions. "
        "For SAT math practice, provide answer choices when helpful and include Problem, Hint, and Answer sections. "
        "For partial derivatives, state which variable is changing, hold the other variables constant, apply product, quotient, chain, "
        "and implicit rules when needed, and simplify the result. "
        "For double integrals, identify or describe the region, choose an integration order, write the bounds clearly, "
        "evaluate the inner integral first, then the outer integral, and mention when changing order or using polar coordinates helps. "
        "For DNA questions, explain transcription as DNA to mRNA, translation as reading mRNA codons into amino acids, "
        "use the standard codon table, show codon grouping in triplets, identify start codons and stop codons, "
        "and clearly state when a sequence is a coding strand versus a template strand. "
        "When a mutation is marked, compare the changed codon and explain whether it changes the amino acid, creates a stop codon, "
        "or is silent. "
        "For coding requests, write clean, runnable code in fenced code blocks with the language name. "
        "Keep indentation lined up correctly. Prefer simple beginner-friendly examples unless the user asks for advanced code. "
        "For Python coding requests, return only one fenced python code block and no description, no goal, no explanation, and no text after the code. "
        "When writing a complete beginner program, include user input by default instead of only hardcoded sample data. "
        "For Python, use input() and convert values with int(), float(), or split() when needed. "
        "Do not use .strip() in generated Python code unless the user explicitly asks for it; for blank input checks, use if value == \"\". "
        "For physics formula code such as F = ma, E = mc^2, Ohm's law, density, velocity, kinetic energy, or similar formulas, "
        "make a runnable calculator: ask for each variable with input(), accept values typed with optional units such as '9.8 m/s^2' "
        "by extracting the first number with a small helper function, use if statements to catch invalid values, "
        "compute the result, and print the answer with units. "
        "For F = ma, ask for mass in kg and acceleration in m/s^2, reject negative mass with an if statement, and print force in newtons. "
        "For E = mc^2, ask for mass in kg, define c = 299792458, reject negative mass with an if statement, and print energy in joules. "
        "For JavaScript, use prompt() for browser examples or clearly say if the code is meant for Node. "
        "Before showing code, mentally check it for syntax, indentation, variable names, and common runtime errors. "
        "When asked about data structures, loops, or if statements, show a short example and explain how it works. "
        "If the user asks to fix code, explain the bug, then provide a corrected version. "
        "If the user asks for an example, sample, practice, hard, advanced, complex, or multi-step problem, "
        "create the problem immediately with Problem, Hint, and Answer sections; do not ask a clarifying question first. "
        "The current simulator mode is only background context. Do not force answers back to the current experiment. "
        "If the user clearly asks for a different topic, subject, function type, homework problem, or concept, answer that requested topic directly and do not mention the current experiment unless it is genuinely relevant. "
        "Use the current simulator mode only when the user asks about the active experiment, app controls, visualization, quantum/DNA mode, or says 'this' in a way that points to the simulator. "
        "If information is missing or the image is unclear, say exactly what is missing. "
        "For normal simulator questions, answer in 2-5 concise sentences unless the user asks for equations, formulas, math, or codon details. "
        "When the user asks for equations, include the key equations in readable plain text or simple LaTeX-style notation. "
        "Say when the visualization is simplified. "
        f"Current mode: {mode}. Current settings: {json.dumps(settings)[:1000]}.{dna_context}"
    )
    input_messages = [{"role": "system", "content": context}]
    input_messages.extend(history)
    if image:
        input_messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": message},
                    {"type": "input_image", "image_url": image["dataUrl"]},
                ],
            }
        )
    else:
        input_messages.append({"role": "user", "content": message})
    payload = prepare_openai_payload(model, {
        "model": model,
        "input": input_messages,
        "max_output_tokens": 3600 if image else 2600,
    }, 3600 if image else 3000)
    return openai_response_text(api_key, payload, timeout=60 if image else 45, retry_tokens=5200 if image else 4200)


def create_server() -> ThreadingHTTPServer:
    for port in range(PORT, PORT + MAX_PORT_TRIES):
        try:
            return ThreadingHTTPServer((HOST, port), QuantumHandler)
        except OSError as exc:
            if exc.errno not in {48, 98, 10048}:
                raise
            print(f"Port {port} is already in use; trying {port + 1}...")
    raise OSError(f"No open port found from {PORT} to {PORT + MAX_PORT_TRIES - 1}.")


def local_network_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "YOUR-MAC-IP"


def main() -> None:
    load_dotenv()
    server = create_server()
    host, port = server.server_address
    lan_ip = local_network_ip()
    print(f"Quantum web app running on this Mac at http://127.0.0.1:{port}")
    print(f"Open on your phone at http://{lan_ip}:{port}")
    if os.environ.get("OPENAI_API_KEY"):
        print(f"OpenAI explainer enabled with model: {os.environ.get('OPENAI_MODEL', DEFAULT_OPENAI_MODEL)}")
    else:
        print("OpenAI explainer disabled. Add OPENAI_API_KEY to .env to enable it.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
