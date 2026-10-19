import hashlib
import hmac
import json
from unittest import mock

from fastapi.testclient import TestClient

import bot

client = TestClient(bot.app)
CAT = bot.cargar_catalogo()


def payload(texto, de="573001112233"):
    return {"entry": [{"changes": [{"value": {"messages": [
        {"from": de, "type": "text", "text": {"body": texto}}]}}]}]}


def test_salud():
    assert client.get("/").json()["estado"] == "ok"


def test_verificacion_ok():
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": bot.VERIFY_TOKEN,
                                       "hub.challenge": "12345"})
    assert r.status_code == 200 and r.text == "12345"


def test_verificacion_falla():
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "malo"})
    assert r.status_code == 403


def test_reglas_producto_sin_tildes():
    r = bot.responder_reglas("Quiero un CHATBOT para mi negocio", CAT)
    assert "Chatbot de WhatsApp con IA" in r and "$1.200.000" in r


def test_reglas_dotacion_con_tilde():
    assert "Dotaciones" in bot.responder_reglas("necesito dotación", CAT)


def test_reglas_catalogo_horario_saludo():
    assert "catálogo" in bot.responder_reglas("¿Qué servicios tienen?", CAT)
    assert "🕐" in bot.responder_reglas("a qué hora abren", CAT)
    assert "asistente virtual" in bot.responder_reglas("hola", CAT)


def test_webhook_responde_en_modo_reglas():
    with mock.patch.object(bot, "ANTHROPIC_API_KEY", ""), \
            mock.patch.object(bot, "enviar_whatsapp", new=mock.AsyncMock()) as env:
        r = client.post("/webhook", json=payload("precio de la pagina web"))
    assert r.status_code == 200
    env.assert_awaited_once()
    para, texto = env.await_args.args
    assert para == "573001112233" and "Página web profesional" in texto


def test_ia_falla_usa_reglas():
    with mock.patch.object(bot, "ANTHROPIC_API_KEY", "x"), \
            mock.patch.object(bot, "responder_ia", new=mock.AsyncMock(side_effect=RuntimeError)), \
            mock.patch.object(bot, "enviar_whatsapp", new=mock.AsyncMock()) as env:
        client.post("/webhook", json=payload("hola"))
    assert "asistente virtual" in env.await_args.args[1]


def test_firma():
    cuerpo = json.dumps(payload("hola")).encode()
    with mock.patch.object(bot, "APP_SECRET", "secreto"), \
            mock.patch.object(bot, "enviar_whatsapp", new=mock.AsyncMock()):
        malo = client.post("/webhook", content=cuerpo, headers={"X-Hub-Signature-256": "sha256=000"})
        firma = "sha256=" + hmac.new(b"secreto", cuerpo, hashlib.sha256).hexdigest()
        bueno = client.post("/webhook", content=cuerpo, headers={"X-Hub-Signature-256": firma})
    assert malo.status_code == 401 and bueno.status_code == 200


def test_ignora_estados_sin_mensajes():
    assert bot.extraer_mensajes({"entry": [{"changes": [{"value": {"statuses": [{}]}}]}]}) == []
