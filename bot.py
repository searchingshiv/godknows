import os
import asyncio  # Fix for NameError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler
)
from telegram.ext.filters import TEXT
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.discovery import build
import requests

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BIBLE_API_KEY = os.getenv("BIBLE_API_KEY")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# Scheduler
scheduler = BackgroundScheduler()

# Function to fetch Bible verse using Google API


def get_random_verse():
    url = "https://bible-api.com/random"
    response = requests.get(url)
    verse = response.json()
    return verse['text']  # Extract the verse text from the response

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = (
        f"Welcome, {user.first_name}! 🙏\n"
        "This bot sends daily Bible verses and answers your spiritual questions.\n\n"
        "Commands:\n"
        "/verse - Get a random Bible verse\n"
        "/ask [your question or feeling] - Receive a relevant verse with an explanation\n"
        "/schedule - Schedule daily Bible verses"
    )
    await update.message.reply_text(welcome_message)
    await context.bot.send_message(LOG_CHANNEL_ID, f"User {user.id} started the bot.")

async def send_random_verse(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.context
    verse = await get_random_verse()
    await context.bot.send_message(chat_id=chat_id, text=f"Good morning! 🌞 Here's a verse:\n\n{verse}")

async def schedule_verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    scheduler.add_job(send_random_verse, 'cron', hour=8, args=[context])
    await update.message.reply_text("Daily Bible verses scheduled at 8:00 AM! 🌅")
    await context.bot.send_message(LOG_CHANNEL_ID, f"User {update.effective_user.id} scheduled daily verses.")

async def get_verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = await get_random_verse()  # Await instead of using asyncio.run
    await update.message.reply_text(f"Here's a random Bible verse:\n\n{verse}")

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = " ".join(context.args)
    user_id = update.effective_user.id

    verse = await get_random_verse()
    explanation = "This verse reminds us to stay hopeful and trust in God."
    response = f"Your input: {user_message}\n\n{verse}\n\nExplanation:\n{explanation}"
    await update.message.reply_text(response)
    log_message = f"User {user_id} asked: {user_message}\nBot replied: {response}"
    await context.bot.send_message(LOG_CHANNEL_ID, log_message)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verse", get_verse))  # Updated handler
    application.add_handler(CommandHandler("ask", ask_question))
    application.add_handler(CommandHandler("schedule", schedule_verse))

    # Scheduler start
    scheduler.start()

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
