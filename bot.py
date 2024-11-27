import logging
import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    InlineQueryHandler,
)
import google.generativeai as genai  # Google Generative AI Library
from flask import Flask, request
import threading
import asyncio

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

# API Keys (Replace with actual keys)
GOOGLE_AI_API_KEY = "AIzaSyDDYYI_AoAEztLU6GyQ09xhXK4g-VBKN9k"
BIBLE_API_ENDPOINT = "https://bible-api.com/random-verse"  # Replace with actual endpoint
TELEGRAM_BOT_TOKEN = "7112230953:AAF4TdvJqCFV7bVXLsU9ITXVeNUik2ZJnSQ"
LOG_CHANNEL_ID = "-1002351224104"
WEBHOOK_URL = "https://godknows-ffu4.onrender.com/webhook"  # Replace with your deployment URL

# Configure Google Generative AI
genai.configure(api_key=GOOGLE_AI_API_KEY)

# Flask app
app = Flask(__name__)

# Fetch a random verse from Bible API
def get_random_verse():
    response = requests.get(BIBLE_API_ENDPOINT)
    if response.status_code == 200:
        data = response.json()
        return data['reference'], data['text']
    return "John 3:16", "For God so loved the world..."

# AI-based explanation using Google Generative AI
def get_ai_explanation(verse_text):
    try:
        response = genai.generate_text(
            model="text-bison-001",  # Use appropriate model
            prompt=f"Explain this Bible verse: {verse_text}",
        )
        return response.candidates[0].output  # Return the explanation from AI
    except Exception as e:
        logging.error(f"Error generating AI explanation: {e}")
        return "Explanation not available."

# Handle user messages
async def handle_message(update: Update, context):
    user_message = update.message.text
    # Log the user message
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"User: {user_message}")
    
    # Fetch a relevant Bible verse
    verse, verse_text = get_random_verse()
    explanation = get_ai_explanation(verse_text)
    
    # Respond to the user
    response = f"📖 *{verse}*\n_{verse_text}_\n\n💡 *Explanation:*\n{explanation}"
    await update.message.reply_text(response, parse_mode="Markdown")
    # Log bot's response
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Bot: {response}")

# Inline Query Handler
async def inline_query(update: Update, context):
    query = update.inline_query.query
    if query == "":
        return
    verse, verse_text = get_random_verse()
    results = [
        InlineQueryResultArticle(
            id="1",
            title=verse,
            input_message_content=InputTextMessageContent(f"📖 *{verse}*\n_{verse_text}_", parse_mode="Markdown")
        )
    ]
    await update.inline_query.answer(results)

# Read Bible Command
async def read_bible(update: Update, context):
    chapter = " ".join(context.args) or "Genesis 1"
    response = requests.get(f"{BIBLE_API_ENDPOINT}/read?chapter={chapter}")
    if response.status_code == 200:
        chapter_text = response.json().get("text", "Chapter not available.")
        await update.message.reply_text(f"📖 *{chapter}*\n{chapter_text}", parse_mode="Markdown")
    else:
        await update.message.reply_text("Could not fetch the requested chapter.")

# Flask webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    logging.info(f"Received webhook: {request.data}")  # Log the webhook data for debugging
    data = request.get_json(force=True)
    application.update_queue.put(Update.de_json(data, application.bot))
    return "OK", 200

@app.route("/")
def home():
    return "Bible Bot is running!"

# Start the bot with asyncio
async def start_bot():
    global application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("read", read_bible))
    application.add_handler(InlineQueryHandler(inline_query))

    # Set webhook (await the coroutine properly)
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logging.info(f"Webhook set to: {WEBHOOK_URL}")

    # Check webhook status (await the coroutine properly)
    status = await application.bot.get_webhook_info()
    logging.info(f"Webhook status: {status}")

# Run Flask app in a separate thread
def run_flask():
    # Start the Flask app without the reloader
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

# Run both bot and Flask
def run():
    # Run Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run the bot with asyncio
    asyncio.run(start_bot())

if __name__ == "__main__":
    run()
