import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import ConversationHandler, MessageHandler
from telegram.ext import filters
from telegram import ReplyKeyboardRemove
TOGGLE_BLOCK = range(1)
SELECT_CONFIG, SELECT_PEER, TOGGLE_BLOCK = range(3)
SHOW_BACKUPS, CREATE_BACKUP, DELETE_BACKUP, RESTORE_BACKUP = range(4)
CREATE_PEER_NAME, CREATE_PEER_IP, CREATE_PEER_DATA_LIMIT, CREATE_PEER_EXPIRY, CREATE_PEER_DNS, CREATE_PEER_CONFIRMATION = range(6)
EDIT_PEER_SELECT, EDIT_PEER_FIELD, EDIT_PEER_UPDATE, EDIT_PEER_CONFIRMATION = range(4)
SELECT_CREATE_INTERFACE, SELECT_EDIT_INTERFACE = range(2)
EDIT_PEER_SELECT, EDIT_PEER_FIELD, EDIT_PEER_UPDATE, EDIT_PEER_CONFIRMATION = range(4)
SELECT_FIELD = EDIT_PEER_FIELD  # Alias for clarity
UPDATE_FIELD = EDIT_PEER_UPDATE  # Alias for clarity
CONFIRM_EDIT = EDIT_PEER_CONFIRMATION  # Alias for clarity



import re
import requests
from ipaddress import ip_address
import aiohttp
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
import logging

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
async def api_request(endpoint, method="GET", data=None):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            logging.info(f"API Request: {method} {url} with data: {data}")
            if method == "POST":
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    result = await response.json()
                    logging.info(f"API Response: {result}")
                    return result
            elif method == "DELETE":
                async with session.delete(url, json=data, headers=headers, timeout=10) as response:
                    result = await response.json()
                    logging.info(f"API Response: {result}")
                    return result
            else:
                async with session.get(url, headers=headers, timeout=10) as response:
                    result = await response.json()
                    logging.info(f"API Response: {result}")
                    return result
    except Exception as e:
        logging.error(f"API Request failed: {e}")
        return {"error": str(e)}

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logging.basicConfig(level=logging.INFO)

async def handle_interface_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    selected_interface = query.data.replace("interface_select_", "")
    context.user_data["config_name"] = selected_interface
    logging.info(f"Interface selected: {selected_interface}")

    await query.message.reply_text(
        f"📛 **Selected Interface:** {selected_interface}\n\n"
        "Please enter the name of the new peer (letters, numbers, and underscores only):",
        parse_mode="Markdown"
    )
    return PEER_NAME

# Main Menu
async def start(update: Update, context: CallbackContext):
    """Display the main menu."""
    chat_id = update.effective_chat.id
    message = "Welcome to the WireGuard Manager Bot. Please choose an option below:"
    keyboard = [
        [InlineKeyboardButton("👥 Peers", callback_data="peers_menu")],  # Updated with icon
        [InlineKeyboardButton("📊 Metrics", callback_data="metrics")],
        [InlineKeyboardButton("📦 Backups", callback_data="backups_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


# Backups Menu
async def backups_menu(update: Update, context: CallbackContext):
    """Display the backups menu."""
    chat_id = update.effective_chat.id
    message = "📦 **Backups Menu**\n\nChoose an action:"
    keyboard = [
        [InlineKeyboardButton("📄 Show Manual Backups", callback_data="show_backups")],
        [InlineKeyboardButton("🛠️ Create Backup", callback_data="create_backup")],
        [InlineKeyboardButton("❌ Delete Backup", callback_data="delete_backup")],
        [InlineKeyboardButton("🔄 Restore Backup", callback_data="restore_backup")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown")

# Show Backups
async def show_backups(update: Update, context: CallbackContext):
    """Fetch and display available manual backups with download links."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    response = await api_request("api/backups")
    if "error" in response:
        await query.message.reply_text(f"❌ Error fetching backups: {response['error']}")
        return ConversationHandler.END

    backups = response.get("backups", [])
    if not backups:
        await query.message.reply_text("No manual backups found.")
        await backups_menu(update, context)
        return ConversationHandler.END

    # Create buttons for each backup with a download link
    keyboard = [
        [
            InlineKeyboardButton(
                f"📄 {backup}",
                callback_data=f"show_backup_details_{backup}"
            ),
            InlineKeyboardButton(
                "⬇️ Download", url=f"{config['base_url']}/api/download-backup?name={backup}"
            ),
        ]
        for backup in backups
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="backups_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "📦 **Available Backups:**\n\nSelect a backup or download directly:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


# Create Backup
async def create_backup(update: Update, context: CallbackContext):
    """Trigger the creation of a new backup."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    response = await api_request("api/create-backup", method="POST")
    if "error" in response:
        await query.message.reply_text(f"❌ Error creating backup: {response['error']}")
    else:
        message = response.get("message", "Backup created successfully.")
        await query.message.reply_text(f"✅ {message}", parse_mode="Markdown")

    await backups_menu(update, context)

# Delete Backup
async def delete_backup_prompt(update: Update, context: CallbackContext):
    """Prompt the user to select a backup to delete."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    response = await api_request("api/backups")
    if "error" in response:
        await query.message.reply_text(f"❌ Error fetching backups: {response['error']}")
        return ConversationHandler.END

    backups = response.get("backups", [])
    if not backups:
        await query.message.reply_text("No manual backups found.")
        await backups_menu(update, context)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"{backup}", callback_data=f"delete_{backup}")] for backup in backups]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="backups_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("❌ **Select a backup to delete:**", reply_markup=reply_markup, parse_mode="Markdown")

async def delete_backup(update: Update, context: CallbackContext):
    """Handle the deletion of a selected backup."""
    query = update.callback_query
    await query.answer()

    backup_name = query.data.replace("delete_", "")
    response = await api_request(f"api/delete-backup?name={backup_name}&folder=root", method="DELETE")
    if "error" in response:
        await query.message.reply_text(f"❌ Error deleting backup: {response['error']}")
    else:
        message = response.get("message", f"Backup {backup_name} deleted successfully.")
        await query.message.reply_text(f"✅ {message}", parse_mode="Markdown")

    await backups_menu(update, context)

# Restore Backup
async def restore_backup_prompt(update: Update, context: CallbackContext):
    """Prompt the user to select a backup to restore."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    response = await api_request("api/backups")
    if "error" in response:
        await query.message.reply_text(f"❌ Error fetching backups: {response['error']}")
        return ConversationHandler.END

    backups = response.get("backups", [])
    if not backups:
        await query.message.reply_text("No manual backups found.")
        await backups_menu(update, context)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"{backup}", callback_data=f"restore_{backup}")] for backup in backups]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="backups_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("🔄 **Select a backup to restore:**", reply_markup=reply_markup, parse_mode="Markdown")

async def restore_backup(update: Update, context: CallbackContext):
    """Handle the restoration of a selected backup."""
    query = update.callback_query
    await query.answer()

    backup_name = query.data.replace("restore_", "")
    response = await api_request("api/restore-backup", method="POST", data={"backupName": backup_name})
    if "error" in response:
        await query.message.reply_text(f"❌ Error restoring backup: {response['error']}")
    else:
        message = response.get("message", f"Backup {backup_name} restored successfully.")
        await query.message.reply_text(f"✅ {message}", parse_mode="Markdown")

    await backups_menu(update, context)

# Register Backups Menu Handlers
def register_backup_handlers(application):
    """Register the backups menu handlers with the Telegram bot."""
    application.add_handler(CallbackQueryHandler(backups_menu, pattern="backups_menu"))
    application.add_handler(CallbackQueryHandler(show_backups, pattern="show_backups"))
    application.add_handler(CallbackQueryHandler(create_backup, pattern="create_backup"))
    application.add_handler(CallbackQueryHandler(delete_backup_prompt, pattern="delete_backup"))
    application.add_handler(CallbackQueryHandler(restore_backup_prompt, pattern="restore_backup"))
    application.add_handler(CallbackQueryHandler(delete_backup, pattern="delete_.*"))
    application.add_handler(CallbackQueryHandler(restore_backup, pattern="restore_.*"))

async def fetch_metrics(update: Update, context: CallbackContext):
    """Fetch and display system metrics as a chart."""
    chat_id = update.effective_chat.id

    # Fetch metrics from the API
    response = await api_request("api/metrics")
    if "error" in response:
        await context.bot.send_message(chat_id, text=f"❌ Error fetching metrics: {response['error']}")
        return

    # Extract metrics
    cpu = response.get("cpu", "N/A")
    ram = response.get("ram", "N/A")
    disk = response.get("disk", {"used": "N/A", "total": "N/A"})
    uptime = response.get("uptime", "N/A")

    # Generate a bar chart
    metrics_labels = ["CPU Usage", "RAM Usage", "Disk Used"]
    metrics_values = [
        float(cpu.replace("%", "")) if "%" in cpu else 0,
        float(ram.replace("%", "")) if "%" in ram else 0,
        float(disk["used"].replace("GB", "").strip()) if "used" in disk else 0,
    ]

    plt.figure(figsize=(6, 4))
    plt.bar(metrics_labels, metrics_values, color=["blue", "green", "orange"])
    plt.title("System Metrics")
    plt.ylabel("Percentage / GB")
    plt.ylim(0, 100)
    plt.grid(axis="y")

    # Save chart to a BytesIO buffer
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)

    # Send the image to the user
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_photo(
        chat_id,
        photo=buffer,
        caption=f"📊 **System Metrics**\n\n"
                f"CPU Usage: {cpu}\n"
                f"RAM Usage: {ram}\n"
                f"Disk Used: {disk['used']} / {disk['total']}\n"
                f"Uptime: {uptime}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    buffer.close()

# Peers Menu
async def peers_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = (
        "🎛 **Peer Management Menu**\n\n"
        "Choose an action below to manage your WireGuard peers:"
    )
    keyboard = [
        [InlineKeyboardButton("🆕 Create Peer", callback_data="create_peer")],
        [InlineKeyboardButton("✏️ Edit Peer", callback_data="edit_peer")],
        [InlineKeyboardButton("❌ Delete Peer", callback_data="delete_peer")],
        [InlineKeyboardButton("🔍 Peer Status", callback_data="peer_status")],
        [InlineKeyboardButton("🔒 Block/Unblock Peer", callback_data="block_unblock_peer")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown")


async def block_unblock_peer(update: Update, context: CallbackContext):
    """
    Initial entry point for the block/unblock feature.
    """
    chat_id = update.effective_chat.id
    message = (
        "🔒 **Block/Unblock Peer**\n\n"
        "Please enter the **configuration file name** (e.g., wg0.conf):"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_CONFIG

async def fetch_config(update: Update, context: CallbackContext):
    """
    Collect the configuration file name and proceed to fetch peer details.
    """
    config_name = update.message.text
    if not re.match(r"^[a-zA-Z0-9_-]+\.conf$", config_name):
        await update.message.reply_text("❌ Invalid configuration file name. Please try again:")
        return SELECT_CONFIG

    context.user_data["config_name"] = config_name

    message = (
        "🔒 **Block/Unblock Peer**\n\n"
        "Please enter the **name** of the peer you want to block or unblock:"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="block_unblock_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_PEER

async def fetch_block_status(update: Update, context: CallbackContext):
    """
    Fetch the block status of the specified peer from the given config.
    """
    peer_name = update.message.text
    config_name = context.user_data.get("config_name", "wg0.conf")  # Ensure config is set

    response = api_request("api/peers?config=" + config_name + "&page=1&limit=50")

    if "error" in response:
        await update.message.reply_text(f"❌ Error fetching peers: {response['error']}")
        return SELECT_PEER

    peers = response.get("peers", [])
    matched_peer = next((peer for peer in peers if peer.get("peer_name") == peer_name), None)

    if not matched_peer:
        await update.message.reply_text(
            "❌ Peer not found. Please enter a valid peer name:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="block_unblock_peer")]]),
            parse_mode="Markdown"
        )
        return SELECT_PEER

    context.user_data["matched_peer"] = matched_peer

    # Show current block status
    is_blocked = matched_peer.get("monitor_blocked", False)
    status = "Blocked" if is_blocked else "Unblocked"
    message = (
        f"🔒 **Block/Unblock Peer**\n\n"
        f"📛 <b>Peer Name:</b> {peer_name}\n"
        f"⚡ <b>Current Status:</b> {status}\n\n"
        f"Would you like to toggle the status?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data="toggle_status")],
        [InlineKeyboardButton("❌ No", callback_data="peers_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
    return TOGGLE_BLOCK


async def toggle_block_status(update: Update, context: CallbackContext):
    """
    Toggle the block/unblock status of the peer.
    """
    query = update.callback_query
    await query.answer()

    matched_peer = context.user_data.get("matched_peer")
    config_name = context.user_data.get("config_name", "wg0.conf")
    if not matched_peer:
        await query.message.reply_text("❌ No peer data found. Please try again.")
        return ConversationHandler.END

    is_blocked = matched_peer.get("monitor_blocked", False)
    new_status = not is_blocked

    # Prepare the payload
    data = {
        "peerName": matched_peer["peer_name"],
        "blocked": new_status,
        "config": config_name,
    }

    response = api_request("api/toggle-peer", method="POST", data=data)

    if "error" in response:
        await query.message.reply_text(f"❌ Error toggling peer status: {response['error']}")
        return ConversationHandler.END

    # Update local status
    matched_peer["monitor_blocked"] = new_status
    matched_peer["expiry_blocked"] = new_status
    context.user_data["matched_peer"] = matched_peer

    # Notify the user
    status = "Blocked" if new_status else "Unblocked"
    message = (
        f"🔒 **Peer Name:** {matched_peer['peer_name']}\n"
        f"⚡ **New Status:** {status}\n\n"
        "✅ Peer status updated successfully!"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END



async def peer_status(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = (
        "🌐 **Peer Status**\n\n"
        "Please enter the **name** of the peer you want to check:"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_PEER


async def fetch_peer_status(update: Update, context: CallbackContext):
    peer_name = update.message.text
    response = api_request("api/peers?config=wg0.conf&page=1&limit=50")

    if "error" in response:
        await update.message.reply_text(f"❌ Error fetching peers: {response['error']}")
        return SELECT_PEER

    peers = response.get("peers", [])
    matched_peer = next((peer for peer in peers if peer.get("peer_name") == peer_name), None)

    if not matched_peer:
        await update.message.reply_text(
            "❌ Peer not found. Please enter a valid peer name:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]),
            parse_mode="Markdown"
        )
        return SELECT_PEER

    # Format peer details for display
    peer_details = (
        f"🎛 **Peer Information**\n\n"
        f"📛 **Peer Name:** `{matched_peer['peer_name']}`\n"
        f"🌐 **Peer IP:** `{matched_peer['peer_ip']}`\n"
        f"🔑 **Public Key:** `{matched_peer['public_key']}`\n"
        f"📊 **Data Limit:** `{matched_peer['limit']}`\n"
        f"🕒 **Expiry Time:** {matched_peer['expiry_time']['days']} days, "
        f"{matched_peer['expiry_time']['hours']} hours, {matched_peer['expiry_time']['minutes']} minutes\n"
        f"📡 **DNS:** `{matched_peer['dns']}`\n"
        f"⏳ **Remaining Data:** `{matched_peer['remaining_human']}`\n"
        f"⚡ **Status:** {'🟢 Active' if not matched_peer['expiry_blocked'] else '🔴 Blocked'}\n"
    )

    keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(peer_details, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END


## Step 1: Display Available WireGuard Interfaces
async def create_peer(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Log the API response
    response = await api_request("api/get-interfaces")
    logging.info(f"Interfaces API Response: {response}")

    if "error" in response:
        await query.message.reply_text(f"❌ Error fetching interfaces: {response['error']}")
        return ConversationHandler.END

    interfaces = response.get("interfaces", [])
    if not interfaces:
        await query.message.reply_text("No WireGuard interfaces found.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(interface, callback_data=f"create_interface_{interface}")] for interface in interfaces]
    keyboard.append([InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "🆕 **Create Peer**\n\nPlease select a WireGuard interface to proceed:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_CREATE_INTERFACE





async def handle_create_interface_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    selected_interface = query.data.replace("create_interface_", "")
    context.user_data["config_name"] = selected_interface

    logging.info(f"Selected interface for Create Peer: {selected_interface}")

    await query.message.reply_text(
        f"📛 **Selected Interface:** {selected_interface}\n\n"
        "Please enter the name of the new peer (letters, numbers, and underscores only):",
        parse_mode="Markdown"
    )
    return CREATE_PEER_NAME



# Step 3: Validate Peer Name and Proceed
async def validate_peer_name(update: Update, context: CallbackContext):
    """Validate the peer name and proceed to collect other peer details."""
    peer_name = update.message.text
    if not peer_name or not re.match(r"^[a-zA-Z0-9_]+$", peer_name):
        await update.message.reply_text("❌ Invalid peer name. Please try again (letters, numbers, and underscores only):")
        return PEER_NAME

    context.user_data["peer_name"] = peer_name

    # Proceed to next step (e.g., collecting IP)
    await update.message.reply_text("🌐 **Enter the IP address for the peer:**", parse_mode="Markdown")
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

    message = "🆗 **Set First Usage?**\n\nChoose whether the peer is considered used initially."
    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data="first_usage_yes")],
        [InlineKeyboardButton("❌ No", callback_data="first_usage_no")],
        [InlineKeyboardButton("🔙 Back", callback_data="collect_config_file")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return None

async def handle_first_usage(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data["first_usage"] = query.data == "first_usage_yes"
    await query.answer()

    details = "\n".join([f"**{key.capitalize()}**: {value}" for key, value in context.user_data.items()])
    message = f"✅ **Review Peer Details:**\n\n{details}\n\nSend **yes** to confirm or **no** to cancel."
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="collect_dns")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
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
        "firstUsage": context.user_data["first_usage"],
    }
    response = api_request("api/create-peer", method="POST", data=data)
    if "error" in response:
        await update.message.reply_text(f"❌ Error creating peer: {response['error']}")
    else:
        message = f"✅ Peer created successfully!\n\n{response['message']}"
        keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END



# Step 1: Prompt to select an interface
async def edit_peer(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    response = await api_request("api/get-interfaces")
    if "error" in response:
        await query.message.reply_text(f"❌ Error fetching interfaces: {response['error']}")
        return ConversationHandler.END

    interfaces = response.get("interfaces", [])
    if not interfaces:
        await query.message.reply_text(
            "No interfaces were found. Please check your WireGuard configuration or enter the interface name manually:"
        )
        return SELECT_CREATE_INTERFACE

    keyboard = [[InlineKeyboardButton(interface, callback_data=f"edit_interface_{interface}")] for interface in interfaces]
    keyboard.append([InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "✏️ **Edit Peer**\n\nPlease select a WireGuard interface to proceed:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_EDIT_INTERFACE




async def handle_edit_interface_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    selected_interface = query.data.replace("edit_interface_", "")
    context.user_data["config_name"] = selected_interface

    logging.info(f"Selected interface for Edit Peer: {selected_interface}")

    await query.message.reply_text(
        f"📛 **Selected Interface:** {selected_interface}\n\n"
        "Please enter the name of the peer you want to edit:",
        parse_mode="Markdown"
    )
    return EDIT_PEER_SELECT



# Step 3: Fetch Peer Details for Edit
async def fetch_peer_details(update: Update, context: CallbackContext):
    peer_name = update.message.text
    config_name = context.user_data["config_name"]
    response = await api_request(f"api/peers?config={config_name}&page=1&limit=50")

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

    # Prepare peer details for editing
    peer_details = {
        "DNS": matched_peer["dns"],
        "Blocked Status": "Blocked" if matched_peer["expiry_blocked"] or matched_peer["monitor_blocked"] else "Unblocked",
        "Peer Name": matched_peer["peer_name"],
        "Limit (Data)": matched_peer["limit"],
        "Expiry Time": f"{matched_peer['expiry_time']['days']} days, {matched_peer['expiry_time']['hours']} hours, {matched_peer['expiry_time']['minutes']} minutes",
    }

    fields = "\n".join(
        [f"<b>{i+1}. {key}</b>: {value}" for i, (key, value) in enumerate(peer_details.items())]
    )
    message = (
        f"🔧 <b>Peer Details</b>\n\n{fields}\n\n"
        "Send the <b>number</b> of the field you want to edit:\n\n"
        "<i>Examples:</i>\n"
        "DNS: 8.8.8.8\n"
        "Blocked Status: Blocked/Unblocked\n"
        "Limit: 500MiB or 1GiB\n"
        "Expiry: 10,0,0 (days,hours,minutes)"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="edit_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
    return SELECT_FIELD



# Step 3: Handle Field Selection
async def select_field(update: Update, context: CallbackContext):
    """
    Handle user input to select a field to edit and provide examples.
    """
    try:
        # Parse the user's input as an integer (menu option)
        field_index = int(update.message.text) - 1
        fields = ["DNS", "Blocked Status", "Peer Name", "Limit (Data)", "Expiry Time"]

        # Validate the selected field
        if field_index < 0 or field_index >= len(fields):
            raise ValueError("Invalid selection.")

        # Get the selected field name
        selected_field = fields[field_index]
        context.user_data["selected_field"] = selected_field  # Save selected field for future steps

        # Define examples for each field
        examples = {
            "DNS": "Example: 8.8.8.8 or 1.1.1.1,8.8.4.4",
            "Blocked Status": "Enter 'Blocked' or 'Unblocked'",
            "Peer Name": "Example: anna or peer_123",
            "Limit (Data)": "Example: 500MiB or 1GiB",
            "Expiry Time": "Format: days,hours,minutes (e.g., '10,0,0')",
        }

        # Include the example in the prompt
        example = examples.get(selected_field, "")
        await update.message.reply_text(
            f"✏️ Enter a new value for <b>{selected_field}</b>: {example}",
            parse_mode="HTML",
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


# Step 4: Update Field Value
async def update_field(update: Update, context: CallbackContext):
    field = context.user_data["selected_field"]
    new_value = update.message.text
    peer_details = context.user_data["peer_details"]

    # Validate and process input based on the selected field
    if field == "DNS":
        example = "Example: 8.8.8.8 or 1.1.1.1,8.8.4.4"
        if not re.match(r'^(\d{1,3}(\.\d{1,3}){3}|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(,\d{1,3}(\.\d{1,3}){3})*$', new_value):
            await update.message.reply_text(f"❌ Invalid DNS value. {example}")
            return UPDATE_FIELD
        peer_details["dns"] = new_value
    elif field == "Blocked Status":
        if new_value.lower() not in ["blocked", "unblocked"]:
            await update.message.reply_text("❌ Invalid value. Enter 'Blocked' or 'Unblocked'.")
            return UPDATE_FIELD
        peer_details["expiry_blocked"] = new_value.lower() == "blocked"
        peer_details["monitor_blocked"] = new_value.lower() == "blocked"
    elif field == "Limit (Data)":
        example = "Example: 500MiB or 1GiB"
        try:
            # Convert human-readable limit to bytes
            bytes_value = convert_to_bytes(new_value)
            peer_details["limit"] = new_value
            peer_details["remaining"] = bytes_value
            peer_details["remaining_human"] = bytes_to_human_readable(bytes_value)
        except ValueError:
            await update.message.reply_text(f"❌ Invalid data limit format. {example}")
            return UPDATE_FIELD
    elif field == "Expiry Time":
        example = "Format: days,hours,minutes (e.g., '10,0,0')"
        try:
            days, hours, minutes = map(int, new_value.split(","))
            peer_details["expiry_time"] = {
                "days": days,
                "hours": hours,
                "minutes": minutes,
            }
        except ValueError:
            await update.message.reply_text(f"❌ Invalid format. {example}")
            return UPDATE_FIELD
    elif field == "Peer Name":
        example = "Example: anna or peer_123"
        if not re.match(r"^[a-zA-Z0-9_]+$", new_value):
            await update.message.reply_text(f"❌ Invalid peer name. {example}")
            return UPDATE_FIELD
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
    payload = {"peerName": peer_name}
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
    response = await api_request("api/edit-peer", method="POST", data=payload)

    if "error" in response:
        await update.message.reply_text(f"❌ Error editing peer: {response['error']}")
    else:
        message = f"✅ Peer edited successfully!\n\n{response['message']}"
        keyboard = [[InlineKeyboardButton("🔙 Back to Peers Menu", callback_data="peers_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END




async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Peer edit canceled.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()  # Clear user data
    return ConversationHandler.END



# Back Button Handler
async def handle_back(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == "main_menu":
        await start(update, context)
    elif query.data == "peers_menu":
        await peers_menu(update, context)
    elif query.data == "edit_peer":
        return await edit_peer(update, context)  # Restart the edit peer process
    elif query.data == "peers_menu":
        return await peers_menu(update, context)
    else:
        return await start(update, context)

# Initialize Bot
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation Handler for Create Peer
    peer_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_peer, pattern="create_peer")],
    states={
        SELECT_CREATE_INTERFACE: [CallbackQueryHandler(handle_create_interface_selection, pattern="create_interface_.*")],
        CREATE_PEER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_peer_name)],
        CREATE_PEER_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_peer_ip)],
        CREATE_PEER_DATA_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_data_limit)],
        CREATE_PEER_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_expiry)],
        CREATE_PEER_DNS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_dns)],
        CREATE_PEER_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_peer)],
    },
    fallbacks=[CallbackQueryHandler(peers_menu, pattern="peers_menu")],
    allow_reentry=True,
)



    edit_peer_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_peer, pattern="edit_peer")],
    states={
        SELECT_EDIT_INTERFACE: [CallbackQueryHandler(handle_edit_interface_selection, pattern="edit_interface_.*")],
        EDIT_PEER_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_peer_details)],
        EDIT_PEER_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_field)],
        EDIT_PEER_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_field)],
        EDIT_PEER_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_edit)],
    },
    fallbacks=[CallbackQueryHandler(peers_menu, pattern="peers_menu")],
    allow_reentry=True,
)





    # Conversation Handler for Peer Status
    peer_status_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(peer_status, pattern="peer_status")],
        states={
            SELECT_PEER: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_peer_status)],
        },
        fallbacks=[CallbackQueryHandler(peers_menu, pattern="peers_menu")],
    )

    # Conversation Handler for Block/Unblock Peer
    block_unblock_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(block_unblock_peer, pattern="block_unblock_peer")],
        states={
            SELECT_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_config)],
            SELECT_PEER: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_block_status)],
            TOGGLE_BLOCK: [CallbackQueryHandler(toggle_block_status, pattern="toggle_status")],
        },
        fallbacks=[CallbackQueryHandler(peers_menu, pattern="peers_menu")],
        allow_reentry=True,
    )

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(peers_menu, pattern="peers_menu"))
    application.add_handler(peer_conversation)
    application.add_handler(edit_peer_conversation)
    application.add_handler(peer_status_conversation)
    application.add_handler(block_unblock_conversation)
    application.add_handler(CallbackQueryHandler(fetch_metrics, pattern="metrics"))
    application.add_handler(CallbackQueryHandler(handle_back, pattern="main_menu"))
    register_backup_handlers(application)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
