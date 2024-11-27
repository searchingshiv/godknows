import logging
import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    InlineQueryHandler,
)
import schedule
import time
import threading

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# API Keys (Replace with actual keys)
GOOGLE_AI_API_KEY = "AIzaSyDDYYI_AoAEztLU6GyQ09xhXK4g-VBKN9k"
BIBLE_API_ENDPOINT = "https://api.bible.com/random-verse"  # Replace with actual endpoint
TELEGRAM_BOT_TOKEN = "7112230953:AAF4TdvJqCFV7bVXLsU9ITXVeNUik2ZJnSQ"
LOG_CHANNEL_ID = "-1002351224104"

# Fetch a random verse from Bible API
def get_random_verse():
    response = requests.get(BIBLE_API_ENDPOINT)
    if response.status_code == 200:
        data = response.json()
        return data['verse'], data['text']
    return "John 3:16", "For God so loved the world..."

# AI-based explanation
def get_ai_explanation(verse_text):
    url = "https://generative-ai-api-url.com"
    headers = {"Authorization": f"Bearer {GOOGLE_AI_API_KEY}"}
    payload = {"input": f"Explain this Bible verse: {verse_text}"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("explanation", "Explanation not available.")
    return "Failed to fetch explanation."

# Handle user messages
def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    # Log the user message
    context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"User: {user_message}")
    
    # Fetch a relevant Bible verse
    verse, verse_text = get_random_verse()  # Add keyword filtering if API allows
    explanation = get_ai_explanation(verse_text)
    
    # Respond to the user
    response = f"📖 *{verse}*\n_{verse_text}_\n\n💡 *Explanation:*\n{explanation}"
    update.message.reply_text(response, parse_mode="Markdown")
    # Log bot's response
    context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Bot: {response}")

# Send a scheduled verse
def scheduled_verse_job(context: CallbackContext):
    verse, verse_text = get_random_verse()
    context.bot.send_message(
        chat_id="@all-users-channel",  # Replace with dynamic user list if needed
        text=f"🌅 Good Morning!\n\n📖 *{verse}*\n_{verse_text}_",
        parse_mode="Markdown"
    )

# Command to read the Bible
def read_bible(update: Update, context: CallbackContext):
    chapter = " ".join(context.args) or "Genesis 1"  # Default to Genesis 1
    response = requests.get(f"{BIBLE_API_ENDPOINT}/read?chapter={chapter}")
    if response.status_code == 200:
        chapter_text = response.json().get("text", "Chapter not available.")
        update.message.reply_text(f"📖 *{chapter}*\n{chapter_text}", parse_mode="Markdown")
    else:
        update.message.reply_text("Could not fetch the requested chapter.")

# Inline Query Handler
def inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query
    if query == "":
        return
    verse, verse_text = get_random_verse()  # Placeholder for actual inline functionality
    results = [
        InlineQueryResultArticle(
            id="1",
            title=verse,
            input_message_content=InputTextMessageContent(f"📖 *{verse}*\n_{verse_text}_", parse_mode="Markdown")
        )
    ]
    update.inline_query.answer(results)

# Schedule daily verses
def run_scheduler(updater):
    job_queue = updater.job_queue
    job_queue.run_daily(scheduled_verse_job, time=time(8, 0))  # 8:00 AM

# Deploy with Flask
from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
    return "Bible Bot is running!"

def start_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler("read", read_bible))
    dispatcher.add_handler(InlineQueryHandler(inline_query))
    
    # Start the scheduler in a separate thread
    threading.Thread(target=run_scheduler, args=(updater,)).start()
    
    # Start polling
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    start_bot()
