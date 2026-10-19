# 💬 WhatsApp AI Bot

**Agente de ventas para WhatsApp Business que atiende a tus clientes 24/7 con tu propio catálogo.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![WhatsApp Cloud API](https://img.shields.io/badge/WhatsApp-Cloud_API-25D366?logo=whatsapp&logoColor=white)
![Claude](https://img.shields.io/badge/IA-Claude-D97757)
![Tests](https://img.shields.io/badge/tests-10%20passing-brightgreen)
![Licencia](https://img.shields.io/badge/licencia-MIT-blue)

> Hecho por **[Tecintek S.A.S.](https://github.com/TecintekSAS)** · ¿Lo quieres instalado en tu negocio? [Escríbenos por WhatsApp](https://wa.me/573125620570).

---

## ✨ Funciones

| | |
|---|---|
| 🤖 **Modo IA** | Con `ANTHROPIC_API_KEY`, responde con Claude usando solo tu catálogo (no inventa precios) y recuerda la conversación |
| 📋 **Modo reglas** | Sin API key funciona igual: catálogo, precios, horario, ubicación y paso a asesor |
| 🛡️ **Respaldo** | Si la IA falla, responde con reglas: el cliente nunca queda sin respuesta |
| 🔐 **Seguridad** | Verificación del webhook y validación de la firma `X-Hub-Signature-256` de Meta |
| 🔤 **Entiende tildes y mayúsculas** | "dotación", "DOTACION" y "dotacion" funcionan igual |
| 🐳 **Docker** | Listo para desplegar en Railway, Render, Fly.io o un VPS |

## 🏗️ Cómo funciona

```
Cliente WhatsApp ──► Meta Cloud API ──► POST /webhook (este bot)
                                            │
                              ┌─────────────┴─────────────┐
                              │ ¿ANTHROPIC_API_KEY?        │
                              ├── sí → Claude + catálogo   │
                              └── no → reglas + catálogo   │
                                            │
Cliente WhatsApp ◄── Meta Cloud API ◄── respuesta
```

## 🚀 Instalación

```bash
git clone https://github.com/TecintekSAS/whatsapp-ai-bot.git
cd whatsapp-ai-bot
pip install -r requirements.txt
cp .env.example .env          # completa tus datos
export $(grep -v '^#' .env | xargs)
uvicorn bot:app --host 0.0.0.0 --port 8000
```

Sin credenciales de WhatsApp el bot funciona en **modo simulado** (imprime las respuestas en consola), ideal para probar.

### Conectar con WhatsApp

1. Crea una app en [developers.facebook.com](https://developers.facebook.com/) y agrega el producto **WhatsApp**.
2. Copia el **Phone Number ID** y el **token de acceso** en tu `.env`.
3. Publica el bot con HTTPS (Railway/Render, o `ngrok http 8000` para pruebas).
4. En *WhatsApp → Configuración → Webhook* pon `https://TU-DOMINIO/webhook` y tu `WHATSAPP_VERIFY_TOKEN`.
5. Suscríbete al campo **messages**. ¡Listo!

### Docker

```bash
docker build -t whatsapp-ai-bot .
docker run -p 8000:8000 --env-file .env whatsapp-ai-bot
```

## 🛍️ Personaliza tu catálogo

Edita `catalog.json` con tu negocio, horario y productos (`nombre`, `precio`, `descripcion`, `palabras_clave`). No hay que tocar código. Los precios incluidos son de ejemplo.

## 🧪 Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

## 🗺️ Próximas mejoras

- [ ] Registro de pedidos en Google Sheets
- [ ] Botones y listas interactivas
- [ ] Envío de imágenes de productos
- [ ] Panel de conversaciones

## 📫 Contacto

**Tecintek S.A.S.** · Facatativá, Colombia · ✉️ tecintek@gmail.com · 💬 [+57 312 562 0570](https://wa.me/573125620570)

Licencia MIT.
