"""
WhatsApp AI Bot — Tecintek S.A.S.

Agente de ventas para WhatsApp Business (Cloud API de Meta) que responde
preguntas de clientes usando el catálogo del negocio. Funciona en dos modos:

* Modo IA: si defines ANTHROPIC_API_KEY, responde con Claude usando el catálogo como contexto.
* Modo reglas: sin API key, responde con reglas (saludo, catálogo, precios, horario, asesor).

Ejecutar:  uvicorn bot:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import unicodedata
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("whatsapp-ai-bot")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "cambia-este-token")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")  # opcional: valida la firma de Meta
GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
CATALOG_PATH = Path(os.getenv("CATALOG_PATH", Path(__file__).with_name("catalog.json")))
HISTORY_SIZE = 10

app = FastAPI(title="WhatsApp AI Bot", version="1.0.0")
historial: dict[str, deque] = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))


# ----------------------------------------------------------------- catálogo
def cargar_catalogo(ruta: Path = CATALOG_PATH) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def cop(valor: float) -> str:
    return "$" + f"{valor:,.0f}".replace(",", ".")


def texto_catalogo(cat: dict) -> str:
    return "\n".join(f"• {p['nombre']}: {cop(p['precio'])} — {p['descripcion']}" for p in cat["productos"])


# ------------------------------------------------------------ modo reglas
def responder_reglas(mensaje: str, cat: dict) -> str:
    m = normalizar(mensaje)
    negocio = cat["negocio"]

    encontrados = [
        p for p in cat["productos"]
        if any(normalizar(k) in m for k in p.get("palabras_clave", []) + [p["nombre"]])
    ]
    if encontrados:
        lineas = [f"*{p['nombre']}* — {cop(p['precio'])}\n{p['descripcion']}" for p in encontrados[:3]]
        return "\n\n".join(lineas) + "\n\n¿Te gustaría hacer el pedido o recibir una cotización formal? 🙌"

    if any(k in m for k in ("catalogo", "productos", "servicios", "que venden", "que ofrecen", "precio", "cuanto")):
        return f"Este es nuestro catálogo 📋\n\n{texto_catalogo(cat)}\n\nEscríbeme el nombre de lo que te interesa."
    if any(k in m for k in ("horario", "hora", "abren", "atienden", "direccion", "ubicacion", "donde")):
        return f"🕐 {negocio['horario']}\n📍 {negocio['direccion']}"
    if any(k in m for k in ("asesor", "humano", "persona", "llamar", "hablar con")):
        return f"Con gusto te comunico con un asesor 👤. También puedes llamar al {negocio['telefono_asesor']}."
    if any(k in m for k in ("gracias", "listo", "perfecto")):
        return "¡Con mucho gusto! Aquí estoy para lo que necesites 😊"
    return (
        f"¡Hola! 👋 Soy el asistente virtual de *{negocio['nombre']}*.\n"
        "Puedo ayudarte con:\n1️⃣ Catálogo y precios\n2️⃣ Horario y ubicación\n3️⃣ Hablar con un asesor\n\n"
        "¿Qué necesitas?"
    )


# --------------------------------------------------------------- modo IA
def prompt_sistema(cat: dict) -> str:
    n = cat["negocio"]
    return (
        f"Eres el asistente de ventas por WhatsApp de {n['nombre']}. Responde en español colombiano, "
        "amable, breve (máximo 5 líneas) y con formato de WhatsApp (*negrita*). "
        "Usa SOLO la información del catálogo; si no sabes algo, ofrece comunicar con un asesor "
        f"al {n['telefono_asesor']}. Nunca inventes precios ni productos.\n\n"
        f"Horario: {n['horario']}\nDirección: {n['direccion']}\n\nCatálogo:\n{texto_catalogo(cat)}"
    )


async def responder_ia(usuario: str, mensaje: str, cat: dict) -> str:
    hist = historial[usuario]
    hist.append({"role": "user", "content": mensaje})
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 400,
                "system": prompt_sistema(cat),
                "messages": list(hist),
            },
        )
        r.raise_for_status()
        texto = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    hist.append({"role": "assistant", "content": texto})
    return texto


async def generar_respuesta(usuario: str, mensaje: str) -> str:
    cat = cargar_catalogo()
    if ANTHROPIC_API_KEY:
        try:
            return await responder_ia(usuario, mensaje, cat)
        except Exception as e:  # si la IA falla, el cliente igual recibe respuesta
            log.warning("IA no disponible (%s); usando reglas", e)
            historial[usuario].clear()
    return responder_reglas(mensaje, cat)


# ------------------------------------------------------------- WhatsApp
async def enviar_whatsapp(para: str, texto: str) -> None:
    if not (ACCESS_TOKEN and PHONE_NUMBER_ID):
        log.info("[simulado] -> %s: %s", para, texto)
        return
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={"messaging_product": "whatsapp", "to": para, "type": "text", "text": {"body": texto}},
        )
        if r.status_code >= 400:
            log.error("Error enviando WhatsApp %s: %s", r.status_code, r.text)


def firma_valida(cuerpo: bytes, firma: str | None) -> bool:
    if not APP_SECRET:
        return True
    if not firma or not firma.startswith("sha256="):
        return False
    esperado = hmac.new(APP_SECRET.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, firma.removeprefix("sha256="))


def extraer_mensajes(payload: dict) -> list[tuple[str, str]]:
    """Devuelve [(telefono, texto)] de los mensajes de texto entrantes."""
    salida = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []) or []:
                if msg.get("type") == "text":
                    salida.append((msg["from"], msg["text"]["body"]))
                elif msg.get("type") == "interactive":
                    inter = msg.get("interactive", {})
                    titulo = (inter.get("button_reply") or inter.get("list_reply") or {}).get("title")
                    if titulo:
                        salida.append((msg["from"], titulo))
    return salida


@app.get("/")
def salud() -> dict:
    return {"estado": "ok", "modo": "ia" if ANTHROPIC_API_KEY else "reglas"}


@app.get("/webhook", response_class=PlainTextResponse)
def verificar(request: Request) -> str:
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == VERIFY_TOKEN:
        return q.get("hub.challenge", "")
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@app.post("/webhook")
async def recibir(request: Request) -> dict:
    cuerpo = await request.body()
    if not firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="Firma inválida")
    payload = json.loads(cuerpo or b"{}")
    for telefono, texto in extraer_mensajes(payload):
        log.info("<- %s: %s", telefono, texto)
        respuesta = await generar_respuesta(telefono, texto)
        await enviar_whatsapp(telefono, respuesta)
    return {"ok": True}
