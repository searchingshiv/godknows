import os
import openai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize the bot application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
job_queue = application.job_queue  # Initialize the JobQueue

# Log user messages and bot responses to a channel
LOG_CHANNEL = '-1002351224104'

def log_to_channel(message, reply):
    """Logs the user message and bot reply to the channel"""
    bot = application.bot
    log_message = f"User: {message}\nBot: {reply}"
    bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

# Send a random Bible verse
def get_random_bible_verse():
    bible_verses = [
        "John 3:16 - For God so loved the world...",
        "Philippians 4:13 - I can do all things through Christ who strengthens me.",
    ]
    return random.choice(bible_verses)

# Get Bible verse explanation using OpenAI
def get_bible_explanation(verse):
    prompt = f"Explain the meaning of the Bible verse: {verse}"
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"].strip()

# Handle text messages
async def handle_message(update: Update, context):
    user_message = update.message.text
    bot = context.bot
    user_id = update.message.chat_id

    if user_message.lower() in ["happy", "sad", "confused"]:
        verse = get_random_bible_verse()
        explanation = get_bible_explanation(verse)
        reply = f"Feeling {user_message}? Here's a verse for you: {verse}\nExplanation: {explanation}"
    else:
        verse = get_random_bible_verse()
        explanation = get_bible_explanation(verse)
        reply = f"Here's a verse for you: {verse}\nExplanation: {explanation}"

    await bot.send_message(chat_id=user_id, text=reply)
    log_to_channel(user_message, reply)

# Send a scheduled Bible verse every morning
async def send_morning_verse(context):
    bot = context.bot
    chat_id = context.job.context
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    await bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse: {verse}\nExplanation: {explanation}")

# Start command handler
async def start(update: Update, context):
    user_id = update.message.chat_id
    job_queue.run_daily(send_morning_verse, time=time(7, 0, 0), context=user_id)
    await update.message.reply_text("Welcome! I will send you a Bible verse every morning.")

# Random verse command handler
async def random_verse(update: Update, context):
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    await update.message.reply_text(f"Here's a random Bible verse: {verse}\nExplanation: {explanation}")

# Add handlers to the application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("randomverse", random_verse))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Start the bot
if __name__ == "__main__":
    application.run_polling()
