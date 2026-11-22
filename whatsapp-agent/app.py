"""WhatsApp AI agent: Meta WhatsApp Cloud API + Claude.

Farriin ka timaadda WhatsApp -> /webhook -> Claude (agent loop + tools) -> jawaab WhatsApp.
"""

import hashlib
import hmac
import os
import threading

import anthropic
import requests
from flask import Flask, request

app = Flask(__name__)
client = anthropic.Anthropic()  # wuxuu akhriyaa ANTHROPIC_API_KEY

WA_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_ID = os.environ["WHATSAPP_PHONE_ID"]
VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]
APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
# Ka soo qaado version-ka ku qoran bogga "API Setup" ee Meta dashboard-kaaga.
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v21.0")

SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "Waxaad tahay caawiye WhatsApp ah. Ku jawaab luqadda qofku ku qoray "
    "(badanaa Soomaali), si gaaban oo cad. Ha samayn wax aadan hubin.",
)
MAX_HISTORY = 20   # inta farriimood ee hore ee Claude loo diro (kharashka ayay xaddidaa)
MAX_STEPS = 10     # inta wareeg ee ugu badan ee agent-ku tools isticmaali karo

conversations: dict[str, list] = {}  # lambar -> wada hadal (RAM: way lumaysaa marka la dib u kiciyo)
seen_ids: set[str] = set()            # Meta mararka qaar farriin labo jeer ayay soo dirtaa
locks: dict[str, threading.Lock] = {}

# ---------------------------------------------------------------- tools
# Halkan ku dar tools-ka agent-kaaga. Tusaalahan waa tijaabo oo keliya.
TOOLS = [
    {
        "name": "get_weather",
        "description": "Soo celi cimilada hadda ee magaalo.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Magaalada, tusaale Muqdisho"}},
            "required": ["city"],
        },
    },
]


def execute_tool(name: str, args: dict) -> tuple[str, bool]:
    """Fuli tool. Waxay soo celisaa (natiijo, is_error)."""
    try:
        if name == "get_weather":
            return f"{args['city']}: 31°C, qorrax (xog tijaabo ah)", False
        return f"Tool aan la aqoon: {name}", True
    except Exception as e:  # khaladka Claude u celi si uu isu saxo
        return f"Khalad: {e}", True


# ---------------------------------------------------------------- agent
def trim_history(messages: list) -> list:
    """Kaliya farriimihii u dambeeyay, kana bilow farriin qoraal ah oo isticmaale ka timid."""
    recent = messages[-MAX_HISTORY:]
    while recent and not (recent[0]["role"] == "user" and isinstance(recent[0]["content"], str)):
        recent = recent[1:]
    return recent


def run_agent(user_id: str, text: str) -> str:
    history = conversations.setdefault(user_id, [])
    history.append({"role": "user", "content": text})
    messages = trim_history(history)

    for _ in range(MAX_STEPS):
        response = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            reply = "Waan ka xumahay, codsigan kuma caawin karo."
            break
        if response.stop_reason != "tool_use":
            reply = "".join(b.text for b in response.content if b.type == "text").strip()
            break

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output, is_error = execute_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                })
        messages.append({"role": "user", "content": results})
    else:
        reply = "Hawshu way dheeraatay. Fadlan si kale u qor su'aashaada."

    conversations[user_id] = messages
    return reply or "..."


# ---------------------------------------------------------------- WhatsApp
def send_whatsapp(to: str, text: str) -> None:
    r = requests.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text[:4096]},
        },
        timeout=30,
    )
    if r.status_code >= 400:
        print("WhatsApp khalad:", r.status_code, r.text, flush=True)


def handle(user_id: str, text: str) -> None:
    lock = locks.setdefault(user_id, threading.Lock())
    with lock:  # hal qof farriimihiisa midba mar
        try:
            send_whatsapp(user_id, run_agent(user_id, text))
        except Exception as e:
            print("Khalad:", repr(e), flush=True)
            send_whatsapp(user_id, "Cillad ayaa dhacday. Fadlan mar kale isku day.")


def signature_ok() -> bool:
    if not APP_SECRET:
        return True  # digniin: ku dar WHATSAPP_APP_SECRET production-ka
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), request.get_data(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, request.headers.get("X-Hub-Signature-256", ""))


@app.get("/")
def health():
    return "WhatsApp agent wuu shaqeynayaa", 200


@app.get("/webhook")
def verify():
    if (request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == VERIFY_TOKEN):
        return request.args.get("hub.challenge", ""), 200
    return "Forbidden", 403


@app.post("/webhook")
def incoming():
    if not signature_ok():
        return "Bad signature", 403
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if msg.get("id") in seen_ids:
                    continue
                seen_ids.add(msg["id"])
                if msg.get("type") != "text":
                    threading.Thread(target=send_whatsapp, args=(
                        msg["from"], "Hadda qoraal oo keliya ayaan akhrin karaa.")).start()
                    continue
                # Isla markiiba 200 u celi Meta; agent-ku gadaal ha ka shaqeeyo
                threading.Thread(target=handle, args=(msg["from"], msg["text"]["body"])).start()
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
