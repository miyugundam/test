import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import ConversationHandler, MessageHandler
from telegram.ext import filters
PEER_NAME, PEER_IP, DATA_LIMIT, EXPIRY, CONFIG_FILE, DNS, CONFIRMATION = range(7)
SELECT_PEER, SELECT_FIELD, UPDATE_FIELD, CONFIRM_EDIT = range(4)
import re
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
    response = api_request("api/peers?config=wg0.conf&page=1&limit=50")

    if "error" in response:
        await update.message.reply_text(f"❌ Error fetching peers: {response['error']}")
        return SELECT_PEER

    peers = response.get("peers", [])
    matched_peer = next((peer for peer in peers if peer.get("peer_name") == peer_name), None)

    if not matched_peer:
        await update.message.reply_text("❌ Peer not found. Please enter a valid peer name:")
        return SELECT_PEER

    context.user_data["peer_name"] = peer_name
    context.user_data["peer_details"] = matched_peer

    # Prepare relevant fields for display
    peer_details = {
        "DNS": matched_peer["dns"],
        "Blocked Status": "Blocked" if matched_peer["expiry_blocked"] or matched_peer["monitor_blocked"] else "Unblocked",
        "First Usage": "Used" if matched_peer["first_usage"] else "Not Used",
        "Peer Name": matched_peer["peer_name"],
        "Limit (Data)": matched_peer["limit"],
        "Expiry Time": f"{matched_peer['expiry_time']['days']} days, {matched_peer['expiry_time']['hours']} hours, {matched_peer['expiry_time']['minutes']} minutes",
    }

    fields = "\n".join(
        [f"{i+1}. <b>{key}</b>: {value}" for i, (key, value) in enumerate(peer_details.items())]
    )
    message = f"🔧 <b>Peer Details</b>\n\n{fields}\n\nSend the <b>number</b> of the field you want to edit:"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="edit_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
    return SELECT_FIELD





# Step 3: Handle Field Selection
async def select_field(update: Update, context: CallbackContext):
    """
    Handle user input to select a field to edit.
    """
    try:
        # Parse the user's input as an integer (menu option)
        field_index = int(update.message.text) - 1
        fields = ["DNS", "Blocked Status", "First Usage", "Peer Name", "Limit (Data)", "Expiry Time"]
        
        # Validate the selected field
        if field_index < 0 or field_index >= len(fields):
            raise ValueError("Invalid selection.")

        # Get the selected field name
        selected_field = fields[field_index]
        context.user_data["selected_field"] = selected_field  # Save selected field for future steps

        # Prompt the user to enter a new value
        await update.message.reply_text(
            f"✏️ Enter a new value for <b>{selected_field}</b>:",
            parse_mode="HTML"
        )
        return UPDATE_FIELD
    except (ValueError, IndexError):
        # Handle invalid input
        await update.message.reply_text("❌ Invalid selection. Please send the number of the field you want to edit:")
        return SELECT_FIELD


def bytes_to_human_readable(bytes_value):
    """
    Convert bytes to human-readable format using GiB, MiB, KiB units.
    """
    if bytes_value >= 1024 ** 3:  # Greater than or equal to 1 GiB
        return f"{bytes_value / (1024 ** 3):.2f} GiB"
    elif bytes_value >= 1024 ** 2:  # Greater than or equal to 1 MiB
        return f"{bytes_value / (1024 ** 2):.2f} MiB"
    elif bytes_value >= 1024:  # Greater than or equal to 1 KiB
        return f"{bytes_value / 1024:.2f} KiB"
    else:
        return f"{bytes_value} bytes"




def convert_to_bytes(limit):
    """
    Convert a string like '1.5GiB' or '1024MiB' into bytes.
    Supports 'B', 'KiB', 'MiB', and 'GiB'.
    """
    try:
        # If limit is already a numeric type, return it as bytes
        if isinstance(limit, (int, float)):
            return int(limit)

        # Handle string input with units
        size, unit = float(limit[:-3]), limit[-3:].upper()
        unit_mapping = {
            "B": 1,
            "KIB": 1024,
            "MIB": 1024 ** 2,
            "GIB": 1024 ** 3,
        }

        if unit not in unit_mapping:
            raise ValueError(f"Invalid unit: {unit}")
        
        return int(size * unit_mapping[unit])
    except (ValueError, TypeError) as e:
        print(f"Error converting limit to bytes: {e}")
        return 0

async def set_data_limit(update: Update, context: CallbackContext):
    try:
        # Get the numerical value and unit
        unit = context.user_data.get("data_limit_unit", "MiB")
        numerical_value = update.message.text.strip()
        limit = f"{numerical_value}{unit}"

        # Convert human-readable limit to bytes
        bytes_value = convert_to_bytes(limit)
        peer_details = context.user_data["peer_details"]
        peer_details["limit"] = limit  # Human-readable
        peer_details["remaining"] = bytes_value
        peer_details["remaining_human"] = bytes_to_human_readable(bytes_value)

        context.user_data["peer_details"] = peer_details
        await update.message.reply_text(
            f"✅ Updated <b>Limit (Data)</b> to: {limit}\n\nDo you want to confirm the changes? (yes/no)",
            parse_mode="HTML",
        )
        return CONFIRM_EDIT
    except ValueError:
        await update.message.reply_text("❌ Invalid numerical value. Please enter a valid number.")
        return UPDATE_FIELD


async def select_unit(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Save the selected unit in user_data
    unit = "MiB" if query.data == "unit_mib" else "GiB"
    context.user_data["data_limit_unit"] = unit

    # Prompt user for the numerical value
    message = f"✏️ Enter the numerical value for the data limit (in {unit}):"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="edit_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)
    return None  # Wait for numerical input


# Step 4: Update Field Value
async def update_field(update: Update, context: CallbackContext):
    field = context.user_data["selected_field"]

    if field == "Limit (Data)":
        # Save the field in user_data for the next step
        context.user_data["field_to_update"] = field

        # Prompt user to choose a unit first
        message = "🆕 Please choose a unit for the data limit:"
        keyboard = [
            [InlineKeyboardButton("MiB", callback_data="unit_mib")],
            [InlineKeyboardButton("GiB", callback_data="unit_gib")],
            [InlineKeyboardButton("🔙 Back", callback_data="edit_peer")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        return None  # Wait for the user to select a unit

    # Handle other fields as before
    new_value = update.message.text
    peer_details = context.user_data["peer_details"]

    if field == "DNS":
        peer_details["dns"] = new_value
    elif field == "Blocked Status":
        if new_value.lower() in ["blocked", "unblocked"]:
            peer_details["expiry_blocked"] = new_value.lower() == "blocked"
            peer_details["monitor_blocked"] = new_value.lower() == "blocked"
        else:
            await update.message.reply_text("❌ Invalid value. Please enter 'Blocked' or 'Unblocked'.")
            return UPDATE_FIELD
    elif field == "Expiry Time":
        try:
            days, hours, minutes = map(int, new_value.split(","))
            peer_details["expiry_time"] = {
                "days": days,
                "hours": hours,
                "minutes": minutes,
            }
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use 'days,hours,minutes' (e.g., '10,0,0').")
            return UPDATE_FIELD
    elif field == "First Usage":
        peer_details["first_usage"] = new_value.lower() == "used"
    elif field == "Peer Name":
        peer_details["peer_name"] = new_value

    context.user_data["peer_details"] = peer_details

    await update.message.reply_text(
        f"✅ Updated <b>{field}</b> to: {new_value}\n\nDo you want to confirm the changes? (yes/no)",
        parse_mode="HTML",
    )
    return CONFIRM_EDIT




# Step 5: Confirm Changes
async def confirm_edit(update: Update, context: CallbackContext):
    if update.message.text.lower() != "yes":
        await update.message.reply_text("❌ Peer edit canceled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    peer_name = context.user_data["peer_name"]
    updated_details = context.user_data["peer_details"]

    # Prepare payload with only allowed fields
    payload = {
        "peerName": peer_name,  # Required
    }

    # Add optional fields if they exist
    if "dns" in updated_details:
        payload["dns"] = updated_details["dns"]

    if "limit" in updated_details:
        payload["dataLimit"] = updated_details["limit"]

    if "expiry_time" in updated_details:
        expiry_time = updated_details["expiry_time"]
        payload.update({
            "expiryMonths": expiry_time.get("months", 0),
            "expiryDays": expiry_time.get("days", 0),
            "expiryHours": expiry_time.get("hours", 0),
            "expiryMinutes": expiry_time.get("minutes", 0),
        })

    # Send the filtered payload to the API
    response = api_request("api/edit-peer", method="POST", data=payload)

    if "error" in response:
        await update.message.reply_text(f"❌ Error editing peer: {response['error']}")
    else:
        await update.message.reply_text(f"✅ Peer edited successfully!\n\n{response['message']}")
    return ConversationHandler.END


# Step 6: Cancel Edit
async def cancel(update: Update, context: CallbackContext):
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
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(peers_menu, pattern="peers_menu"))
    application.add_handler(peer_conversation)
    application.add_handler(edit_peer_conversation)
    application.add_handler(CallbackQueryHandler(select_unit, pattern="unit_mib|unit_gib"))


    print("Bot is running...")
    application.run_polling()



if __name__ == "__main__":
    main()
