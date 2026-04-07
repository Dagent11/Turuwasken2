import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai
from google import genai as genai2
from google.genai import types

# ── Config ──────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
image_client = genai2.Client(api_key=GEMINI_API_KEY)

conversation_history = {}

logging.basicConfig(level=logging.INFO)

# ── Handlers ────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Gemini conectado. Mandame cualquier mensaje.\n\n"
        "Comandos:\n"
        "/imagen [descripción] — genera una imagen\n"
        "/reset — limpiar historial\n"
        "/model — ver modelo activo"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("Historial limpiado.")

async def model_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chat: gemini-2.0-flash\nImágenes: imagen-3.0-generate-002")

async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Usá: /imagen [descripción de la imagen]")
        return

    await update.message.chat.send_action("upload_photo")

    try:
        response = image_client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1)
        )
        image_bytes = response.generated_images[0].image.image_bytes
        await update.message.reply_photo(photo=image_bytes)
    except Exception as e:
        await update.message.reply_text(f"Error generando imagen: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "parts": [{"text": user_text}]
    })

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    await update.message.chat.send_action("typing")

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(conversation_history[user_id])
        reply = response.text

        conversation_history[user_id].append({
            "role": "model",
            "parts": [{"text": reply}]
        })

        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i:i+4000])
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("model", model_info))
    app.add_handler(CommandHandler("imagen", imagen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Gemini corriendo...")
    app.run_polling()
