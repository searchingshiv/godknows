import logging
import requests
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token
TELEGRAM_TOKEN = '7112230953:AAF4TdvJqCFV7bVXLsU9ITXVeNUik2ZJnSQ'

# Gemini API (Google's AI API) setup
GEMINI_API_KEY = 'AIzaSyDDYYI_AoAEztLU6GyQ09xhXK4g-VBKN9k'  # API Key for Google Gemini

# Function to call Gemini API for text analysis (NLP)
def get_explanation_from_gemini(text):
    url = "https://gemini.googleapis.com/v1/ai/response"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GEMINI_API_KEY}',
    }
    data = {
        "query": text,
        "model": "text-davinci-003",  # Specify model (you can change based on your requirements)
    }
    response = requests.post(url, json=data, headers=headers)
    explanation = response.json().get("response", "Sorry, I couldn't understand that.")
    return explanation

# Function to get a random Bible verse (using Bible.com API)
def get_random_bible_verse():
    url = 'https://bible.com/api/v1/verses/random'
    response = requests.get(url)
    verse = response.json()
    return verse['verse']['text']

# Function to handle user messages (dynamic without chat_id)
def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text
    explanation = get_explanation_from_gemini(user_text)  # AI-based explanation from Gemini
    verse = get_random_bible_verse()  # Get a random Bible verse
    update.message.reply_text(f"Here's a random Bible verse for you:\n{verse}\n\nExplanation (from AI):\n{explanation}")

# Logging user messages and bot replies (optional)
def log_to_channel(update: Update, context: CallbackContext):
    user_message = update.message.text
    bot_reply = context.bot.send_message(chat_id=update.message.chat_id, text=user_message)
    channel_id = '-1002351224104'  # Replace with your channel ID
    context.bot.send_message(chat_id=channel_id, text=f"User: {user_message}\nBot: {bot_reply.text}")

# Command for starting the bot
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(f"Hello {user.first_name}! I'm your Bible Bot. How can I help you today?")
    context.bot.send_message(chat_id=update.message.chat_id, text="You can ask me for a verse, or tell me your feelings!")

# Command for asking for a random verse
def random_verse(update: Update, context: CallbackContext):
    verse = get_random_bible_verse()
    update.message.reply_text(f"Here's a random verse for you: {verse}")

# Inline button example (for additional options)
def inline_options(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Send me a random verse", callback_data='random_verse')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Here are your options:", reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == 'random_verse':
        verse = get_random_bible_verse()
        query.edit_message_text(f"Random verse: {verse}")

# Main function to start the bot
def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    
    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("random_verse", random_verse))
    
    # Message handler for user input (dynamic)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Inline button handler
    dp.add_handler(CallbackQueryHandler(button))
    
    # Logging handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, log_to_channel))

    # Start the bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
