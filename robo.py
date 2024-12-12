import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import ConversationHandler, MessageHandler
from telegram.ext import filters
PEER_NAME, PEER_IP, DATA_LIMIT, EXPIRY, CONFIG_FILE, DNS, CONFIRMATION = range(7)
SELECT_PEER, SELECT_FIELD, UPDATE_FIELD, CONFIRM_EDIT = range(4)

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
    message = "🆕 **Peer Creation**\n\nEnter a **name** for the peer (letters, numbers, and underscores only):"
    keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown")
    return PEER_NAME

async def collect_peer_name(update: Update, context: CallbackContext):
    peer_name = update.message.text
    if not peer_name or not re.match(r"^[a-zA-Z0-9_]+$", peer_name):
        await update.message.reply_text("❌ Invalid peer name. Please try again (letters, numbers, and underscores only):")
        return PEER_NAME
    context.user_data["peer_name"] = peer_name
    message = "🌐 **Enter the IP address for the peer:**"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="create_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return PEER_IP

async def collect_peer_ip(update: Update, context: CallbackContext):
    peer_ip = update.message.text
    try:
        ip_address(peer_ip)
    except ValueError:
        await update.message.reply_text("❌ Invalid IP address. Please enter a valid IP:")
        return PEER_IP
    context.user_data["peer_ip"] = peer_ip
    message = "📊 **Enter a data limit for the peer** (e.g., 500MiB or 1GiB):"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="collect_peer_name")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return DATA_LIMIT

async def collect_data_limit(update: Update, context: CallbackContext):
    data_limit = update.message.text
    if not re.match(r"^\d+(MiB|GiB)$", data_limit):
        await update.message.reply_text("❌ Invalid data limit. Enter a value like 500MiB or 1GiB:")
        return DATA_LIMIT
    context.user_data["data_limit"] = data_limit
    message = "📅 **Enter expiry time in days** (e.g., 30):"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="collect_peer_ip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return EXPIRY

async def collect_expiry(update: Update, context: CallbackContext):
    try:
        expiry_days = int(update.message.text)
        if expiry_days <= 0:
            raise ValueError("Expiry must be greater than zero.")
        context.user_data["expiry_days"] = expiry_days
    except ValueError:
        await update.message.reply_text("❌ Invalid expiry time. Please enter a positive number:")
        return EXPIRY
    message = "⚙️ **Enter the config file name** (default is wg0.conf):"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="collect_data_limit")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIG_FILE

async def collect_config_file(update: Update, context: CallbackContext):
    config_file = update.message.text or "wg0.conf"
    if not re.match(r"^[a-zA-Z0-9_-]+\.conf$", config_file):
        await update.message.reply_text("❌ Invalid config file name. Please try again:")
        return CONFIG_FILE
    context.user_data["config_file"] = config_file
    message = "🔧 **Enter DNS values** (comma-separated, default: 1.1.1.1):"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="collect_expiry")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return DNS

async def collect_dns(update: Update, context: CallbackContext):
    dns = update.message.text or "1.1.1.1"
    context.user_data["dns"] = dns

    details = "\n".join([f"**{key.capitalize()}**: {value}" for key, value in context.user_data.items()])
    message = f"✅ **Review Peer Details:**\n\n{details}\n\nSend **yes** to confirm or **no** to cancel."
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="collect_config_file")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIRMATION

async def confirm_peer(update: Update, context: CallbackContext):
    if update.message.text.lower() != "yes":
        await update.message.reply_text("❌ Peer creation canceled.", reply_markup=ReplyKeyboardRemove())
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
        await update.message.reply_text(f"❌ Error creating peer: {response['error']}")
    else:
        await update.message.reply_text(f"✅ Peer created successfully!\n\n{response['message']}")
    return ConversationHandler.END


# Step 1: Ask for Peer Name
async def edit_peer(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = "✏️ **Edit Peer**\n\nEnter the **name** of the peer you want to edit:"
    keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_PEER

# Step 2: Fetch and Show Peer Details
async def fetch_peer_details(update: Update, context: CallbackContext):
    peer_name = update.message.text
    response = api_request(f"api/get-peer-details?peerName={peer_name}")
    
    if "error" in response:
        await update.message.reply_text(f"❌ Error: {response['error']}")
        return SELECT_PEER

    # Save peer details in user_data
    context.user_data["peer_name"] = peer_name
    context.user_data["peer_details"] = response

    # Show fields for editing
    fields = "\n".join([f"{i+1}. **{key.capitalize()}**: {value}" for i, (key, value) in enumerate(response.items())])
    message = f"🔧 **Peer Details**\n\n{fields}\n\nSend the **number** of the field you want to edit:"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="edit_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_FIELD

# Step 3: Handle Field Selection
async def select_field(update: Update, context: CallbackContext):
    try:
        field_index = int(update.message.text) - 1
        fields = list(context.user_data["peer_details"].keys())
        selected_field = fields[field_index]
        context.user_data["selected_field"] = selected_field

        await update.message.reply_text(f"✏️ Enter a new value for **{selected_field.capitalize()}**:")
        return UPDATE_FIELD
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid selection. Please send the number of the field you want to edit:")
        return SELECT_FIELD

# Step 4: Update Field Value
async def update_field(update: Update, context: CallbackContext):
    new_value = update.message.text
    selected_field = context.user_data["selected_field"]
    context.user_data["peer_details"][selected_field] = new_value

    message = f"✅ Updated **{selected_field.capitalize()}** to: {new_value}\n\nDo you want to confirm the changes? (yes/no)"
    await update.message.reply_text(message, parse_mode="Markdown")
    return CONFIRM_EDIT

# Step 5: Confirm Changes
async def confirm_edit(update: Update, context: CallbackContext):
    if update.message.text.lower() != "yes":
        await update.message.reply_text("❌ Peer edit canceled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    peer_name = context.user_data["peer_name"]
    updated_details = context.user_data["peer_details"]
    data = {"peerName": peer_name, **updated_details}

    response = api_request("api/edit-peer", method="POST", data=data)
    if "error" in response:
        await update.message.reply_text(f"❌ Error editing peer: {response['error']}")
    else:
        await update.message.reply_text(f"✅ Peer edited successfully!\n\n{response['message']}")
    return ConversationHandler.END

# Step 6: Cancel Edit
async def cancel_edit(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Peer edit canceled.", reply_markup=ReplyKeyboardRemove())
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
     # Conversation Handler for Edit Peer
    edit_peer_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_peer, pattern="edit_peer")],
        states={
            SELECT_PEER: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_peer_details)],
            SELECT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_field)],
            UPDATE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_field)],
            CONFIRM_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_edit)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
    )

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(peers_menu, pattern="peers_menu"))
    application.add_handler(peer_conversation)

    print("Bot is running...")
    application.run_polling()



if __name__ == "__main__":
    main()
