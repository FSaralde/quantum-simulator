# Quantum Lab Web App

Run the backend and frontend:

```bash
cd /Users/frank/Documents/Codex/2026-07-01/ma
.venv/bin/python outputs/quantum_web_app/backend.py
```

Open:

```text
http://127.0.0.1:8010
```

The app now includes:

- Home page
- Simulator
- Local login/signup
- Settings
- Demo subscription plans
- AI explainer popup
- Chatbot

The subscription plans are demo-only. No Stripe or card payment is processed yet.

## Enable OpenAI AI Explainer

Create this file:

```text
/Users/frank/Documents/Codex/2026-07-01/ma/outputs/quantum_web_app/.env
```

Put this inside it:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5-mini
```

Restart the backend with the venv Python. The terminal should say:

```text
OpenAI explainer enabled with model: gpt-5-mini
```

## Deploying

Deploy as a Python web service, not as a static-only site. Static hosts like plain Netlify/Vercel static pages will show the frontend but `/api/chat` will not work unless you also deploy the Python backend.

If your deploy root is this folder, `outputs/quantum_web_app`, use:

```bash
pip install -r requirements.txt
python3 backend.py
```

If your deploy root is the parent workspace folder, use:

```bash
pip install -r requirements.txt
python3 outputs/quantum_web_app/backend.py
```

On Render/Railway/Fly/etc, set these environment variables:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5-mini
```

The backend now reads the platform `PORT` variable automatically.

Test your deployed backend by opening:

```text
https://your-domain.com/api/health
```

It should show:

```json
{"ok": true}
```

If `/api/health` does not show that, the backend is not running or the domain is pointed at the wrong service.

If you deploy the frontend separately from the backend, open Settings in the app and paste your backend URL into `Backend URL`, for example:

```text
https://your-backend.onrender.com
```

Then reload the page. The chatbot will call that backend instead of `/api` on the frontend site.
