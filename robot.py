import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import requests

# Load Config
def load_config():
    config_path = "telegram/config.json"
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
            return {
                "bot_token": config.get("bot-token", ""),
                "base_url": config.get("base-url", ""),
                "api_key": config.get("api-key", ""),
            }
    except FileNotFoundError:
        print(f"Error: Configuration file {config_path} not found.")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {config_path}. {e}")
        raise

# Load Configuration
config = load_config()
API_BASE_URL = config["base_url"]
TELEGRAM_BOT_TOKEN = config["bot_token"]
API_KEY = config["api_key"]

# Helper Function to Handle API Requests
def api_request(endpoint, method="GET", data=None):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        if method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, json=data, headers=headers)
        else:
            response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Main Menu
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = "Welcome to the WireGuard Manager Bot. Please choose an option below:"
    keyboard = [
        [InlineKeyboardButton("Peers", callback_data="peers_menu")],
        [InlineKeyboardButton("Metrics", callback_data="metrics")],
        [InlineKeyboardButton("Peer Status", callback_data="peer_status")],
        [InlineKeyboardButton("Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("Backup", callback_data="backup_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Peers Menu
async def peers_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = "Peer Management Options:"
    keyboard = [
        [InlineKeyboardButton("Create Peer", callback_data="create_peer")],
        [InlineKeyboardButton("Edit Peer", callback_data="edit_peer")],
        [InlineKeyboardButton("Delete Peer", callback_data="delete_peer")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Metrics
async def metrics(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = api_request("api/metrics")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"Error: {data['error']}")
        return

    message = (
        f"💻 System Metrics:\n"
        f"CPU Usage: {data.get('cpu', 'N/A')}%\n"
        f"RAM Usage: {data.get('ram', 'N/A')}%\n"
        f"Disk Usage: {data.get('disk', {}).get('used', 'N/A')} / {data.get('disk', {}).get('total', 'N/A')}\n"
        f"Uptime: {data.get('uptime', 'N/A')}\n"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Peer Status
async def peer_status(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = api_request("api/available-ips")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"Error: {data['error']}")
        return

    message = "🌐 Peer Status:\n"
    for peer_ip, status in data.get("ip_status", {}).items():
        message += f"Peer IP: {peer_ip} - Status: {'🟢 Active' if status == 'active' else '🔴 Banned'}\n"

    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Settings Menu
async def settings_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = "Settings Options:"
    keyboard = [
        [InlineKeyboardButton("Update WireGuard Config", callback_data="update_wireguard")],
        [InlineKeyboardButton("Update Username & Password", callback_data="update_user")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Backup Menu
async def backup_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = "Backup Management:"
    keyboard = [
        [InlineKeyboardButton("Create Backup", callback_data="create_backup")],
        [InlineKeyboardButton("List Backups", callback_data="list_backups")],
        [InlineKeyboardButton("Restore Backup", callback_data="restore_backup")],
        [InlineKeyboardButton("Delete Backup", callback_data="delete_backup")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Back Button Handler
async def handle_back(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == "main_menu":
        await start(update, context)
    elif query.data == "peers_menu":
        await peers_menu(update, context)
    elif query.data == "settings_menu":
        await settings_menu(update, context)
    elif query.data == "backup_menu":
        await backup_menu(update, context)

# Initialize Bot
def main():
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(start, pattern="main_menu"))
        # Add other handlers as necessary

        print("Bot is running...")
        application.run_polling()
    except Exception as e:
        print(f"Error starting the bot: {e}")

if __name__ == "__main__":
    main()
