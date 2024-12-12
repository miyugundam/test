import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import ConversationHandler, MessageHandler
from telegram.ext import filters
PEER_NAME, PEER_IP, DATA_LIMIT, EXPIRY, CONFIG_FILE, DNS, CONFIRMATION = range(7)
import requests

# Load Config
def load_config():
    config_path = "/root/wire/src/telegram/config.json"
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

async def create_peer(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Enter a name for the peer (letters, numbers, and underscores only):")
    return PEER_NAME

async def collect_peer_name(update: Update, context: CallbackContext):
    peer_name = update.message.text
    if not peer_name or not re.match(r"^[a-zA-Z0-9_]+$", peer_name):
        await update.message.reply_text("Invalid peer name. Please try again:")
        return PEER_NAME
    context.user_data["peer_name"] = peer_name
    await update.message.reply_text("Enter the IP address for the peer:")
    return PEER_IP

async def collect_peer_ip(update: Update, context: CallbackContext):
    peer_ip = update.message.text
    try:
        ip_address(peer_ip)
    except ValueError:
        await update.message.reply_text("Invalid IP address. Please enter a valid IP:")
        return PEER_IP
    context.user_data["peer_ip"] = peer_ip
    await update.message.reply_text("Enter a data limit for the peer (e.g., 500MiB or 1GiB):")
    return DATA_LIMIT

async def collect_data_limit(update: Update, context: CallbackContext):
    data_limit = update.message.text
    if not re.match(r"^\d+(MiB|GiB)$", data_limit):
        await update.message.reply_text("Invalid data limit. Enter a value like 500MiB or 1GiB:")
        return DATA_LIMIT
    context.user_data["data_limit"] = data_limit
    await update.message.reply_text("Enter expiry time in days (e.g., 30):")
    return EXPIRY

async def collect_expiry(update: Update, context: CallbackContext):
    try:
        expiry_days = int(update.message.text)
        if expiry_days <= 0:
            raise ValueError("Expiry must be greater than zero.")
        context.user_data["expiry_days"] = expiry_days
    except ValueError:
        await update.message.reply_text("Invalid expiry time. Please enter a positive number:")
        return EXPIRY
    await update.message.reply_text("Enter the config file name (default is wg0.conf):")
    return CONFIG_FILE

async def collect_config_file(update: Update, context: CallbackContext):
    config_file = update.message.text or "wg0.conf"
    if not re.match(r"^[a-zA-Z0-9_-]+\.conf$", config_file):
        await update.message.reply_text("Invalid config file name. Please try again:")
        return CONFIG_FILE
    context.user_data["config_file"] = config_file
    await update.message.reply_text("Enter DNS values (comma-separated, default: 1.1.1.1):")
    return DNS

async def collect_dns(update: Update, context: CallbackContext):
    dns = update.message.text or "1.1.1.1"
    context.user_data["dns"] = dns

    details = "\n".join([f"{key}: {value}" for key, value in context.user_data.items()])
    await update.message.reply_text(f"Please confirm the following details:\n{details}\n\nSend 'yes' to confirm or 'no' to cancel.")
    return CONFIRMATION

async def confirm_peer(update: Update, context: CallbackContext):
    if update.message.text.lower() != "yes":
        await update.message.reply_text("Peer creation canceled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    data = {
        "peerName": context.user_data["peer_name"],
        "peerIp": context.user_data["peer_ip"],
        "dataLimit": context.user_data["data_limit"],
        "expiryDays": context.user_data["expiry_days"],
        "configFile": context.user_data["config_file"],
        "dns": context.user_data["dns"],
    }
    response = api_request("api/create-peer", method="POST", data=data)
    if "error" in response:
        await update.message.reply_text(f"Error creating peer: {response['error']}")
    else:
        await update.message.reply_text(f"Peer created successfully!\n{response['message']}")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Peer creation canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

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
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation Handler for Create Peer
    peer_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_peer, pattern="create_peer")],
        states={
            PEER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND
, collect_peer_name)],
            PEER_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND
, collect_peer_ip)],
            DATA_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND
, collect_data_limit)],
            EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND
, collect_expiry)],
            CONFIG_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND
, collect_config_file)],
            DNS: [MessageHandler(filters.TEXT & ~filters.COMMAND
, collect_dns)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND
, confirm_peer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(peers_menu, pattern="peers_menu"))
    application.add_handler(peer_conversation)

    print("Bot is running...")
    application.run_polling()



if __name__ == "__main__":
    main()
