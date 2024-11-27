import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler
)
from telegram.ext.filters import TEXT
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.discovery import build

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BIBLE_API_KEY = os.getenv("BIBLE_API_KEY")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# Scheduler
scheduler = BackgroundScheduler()

# Function to fetch Bible verse using Google API
async def get_random_verse():
    # Replace this with actual API integration for fetching Bible verses
    service = build('bibleApi', 'v1', developerKey=BIBLE_API_KEY)
    request = service.verses().random()
    response = request.execute()
    return response.get("text", "No verse found.")

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
    # Log user interaction
    await context.bot.send_message(LOG_CHANNEL_ID, f"User {user.id} started the bot.")

async def send_random_verse(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.context
    verse = await get_random_verse()
    await context.bot.send_message(chat_id=chat_id, text=f"Good morning! 🌞 Here's a verse:\n\n{verse}")

async def schedule_verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    scheduler.add_job(send_random_verse, 'cron', hour=8, args=[context])
    await update.message.reply_text("Daily Bible verses scheduled at 8:00 AM! 🌅")
    # Log the scheduling
    await context.bot.send_message(LOG_CHANNEL_ID, f"User {update.effective_user.id} scheduled daily verses.")

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = " ".join(context.args)
    user_id = update.effective_user.id

    # Example NLP or AI processing logic to fetch a relevant verse (use keywords or Google's AI APIs)
    verse = await get_random_verse()  # Replace this with your custom logic or API call
    explanation = "This verse reminds us to stay hopeful and trust in God."  # Example response

    response = f"Your input: {user_message}\n\n{verse}\n\nExplanation:\n{explanation}"
    await update.message.reply_text(response)

    # Log the user question and bot response
    log_message = f"User {user_id} asked: {user_message}\nBot replied: {response}"
    await context.bot.send_message(LOG_CHANNEL_ID, log_message)

# Inline keyboard example
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This handles inline queries; use for verse lookup or similar quick options
    await update.inline_query.answer([])  # Placeholder for inline options

# Main function
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verse", lambda update, context: update.message.reply_text(get_random_verse())))
    application.add_handler(CommandHandler("ask", ask_question))
    application.add_handler(CommandHandler("schedule", schedule_verse))

    # Scheduler start
    scheduler.start()

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
