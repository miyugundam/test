import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import ConversationHandler, MessageHandler
from telegram.ext import filters
from telegram import ReplyKeyboardRemove
TOGGLE_BLOCK = range(1)
SELECT_CONFIG, SELECT_PEER, TOGGLE_BLOCK = range(3)
SHOW_BACKUPS, CREATE_BACKUP, DELETE_BACKUP, RESTORE_BACKUP = range(4)
SELECT_INTERFACE, SELECT_IP, PEER_DETAILS = range(3)


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



import aiohttp

async def api_request(endpoint, method="GET", data=None):
    """
    Make an asynchronous API request.
    
    :param endpoint: API endpoint (relative to the base URL)
    :param method: HTTP method (GET, POST, DELETE, etc.)
    :param data: Optional payload for POST/PUT requests
    :return: JSON response as a dictionary or an error message
    """
    url = f"{API_BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    return await response.json()
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    return await response.json()
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers, json=data) as response:
                    return await response.json()
            else:
                return {"error": "Unsupported HTTP method"}
        except aiohttp.ClientError as e:
            return {"error": str(e)}


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


async def create_peer_start(update: Update, context: CallbackContext):
    """Start the peer creation process."""
    chat_id = update.effective_chat.id

    response = await api_request("api/get-interfaces")
    if "error" in response:
        await context.bot.send_message(chat_id, text=f"❌ Error fetching interfaces: {response['error']}")
        return ConversationHandler.END

    interfaces = response.get("interfaces", [])
    if not interfaces:
        await context.bot.send_message(chat_id, text="No WireGuard interfaces found.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(interface, callback_data=f"select_interface_{interface}")] for interface in interfaces]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id, text="Select a WireGuard interface:", reply_markup=reply_markup)
    return SELECT_INTERFACE


async def select_interface(update: Update, context: CallbackContext):
    """Handle interface selection."""
    query = update.callback_query
    await query.answer()

    selected_interface = query.data.replace("select_interface_", "")
    context.user_data["selected_interface"] = selected_interface

    response = await api_request(f"api/available-ips?interface={selected_interface}")
    if "error" in response:
        await query.message.reply_text(f"❌ Error fetching available IPs: {response['error']}")
        return ConversationHandler.END

    ips = response.get("available_ips", [])
    if not ips:
        await query.message.reply_text("No available IPs found for this interface.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(ip, callback_data=f"select_ip_{ip}")] for ip in ips]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Select a private IP for the peer:", reply_markup=reply_markup)
    return SELECT_IP


async def select_ip(update: Update, context: CallbackContext):
    """Handle IP selection and request peer details."""
    query = update.callback_query
    await query.answer()

    selected_ip = query.data.replace("select_ip_", "")
    context.user_data["selected_ip"] = selected_ip

    await query.message.reply_text(
        "Enter the **Peer Name** (letters, numbers, and underscores only):",
        parse_mode="Markdown"
    )
    return PEER_DETAILS


async def collect_peer_details(update: Update, context: CallbackContext):
    """Collect peer details and send the creation request."""
    peer_name = update.message.text
    if not re.match(r"^\w+$", peer_name):
        await update.message.reply_text("❌ Invalid peer name. Use letters, numbers, and underscores only:")
        return PEER_DETAILS

    context.user_data["peer_name"] = peer_name

    keyboard = [
        [InlineKeyboardButton("✅ Enable First Usage", callback_data="first_usage_enable")],
        [InlineKeyboardButton("❌ Disable First Usage", callback_data="first_usage_disable")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Enable or disable 'First Usage' for the peer:", reply_markup=reply_markup)


async def set_first_usage(update: Update, context: CallbackContext):
    """Set the first usage flag and create the peer."""
    query = update.callback_query
    await query.answer()

    first_usage = query.data == "first_usage_enable"
    context.user_data["first_usage"] = first_usage

    payload = {
        "interface": context.user_data["selected_interface"],
        "private_ip": context.user_data["selected_ip"],
        "peer_name": context.user_data["peer_name"],
        "first_usage": first_usage,
    }

    response = await api_request("api/create-peer", method="POST", data=payload)
    if "error" in response:
        await query.message.reply_text(f"❌ Error creating peer: {response['error']}")
        return ConversationHandler.END

    await query.message.reply_text(f"✅ Peer '{payload['peer_name']}' created successfully!")
    return ConversationHandler.END



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




# Back Button Handler
async def handle_back(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == "main_menu":
        await start(update, context)
    elif query.data == "peers_menu":
        await peers_menu(update, context)
    else:
        return await start(update, context)

# Initialize Bot
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


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
    # Register the ConversationHandler
    peer_creation_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_peer_start, pattern="create_peer")],
    states={
        SELECT_INTERFACE: [CallbackQueryHandler(select_interface, pattern="select_interface_.*")],
        SELECT_IP: [CallbackQueryHandler(select_ip, pattern="select_ip_.*")],
        PEER_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_peer_details)],
    },
    fallbacks=[CallbackQueryHandler(peers_menu, pattern="peers_menu")],
    allow_reentry=True,
)


    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(peers_menu, pattern="peers_menu"))
    application.add_handler(peer_status_conversation)
    application.add_handler(block_unblock_conversation)
    application.add_handler(CallbackQueryHandler(fetch_metrics, pattern="metrics"))
    application.add_handler(CallbackQueryHandler(handle_back, pattern="main_menu"))
    register_backup_handlers(application)
    # Add this handler to the main function
    application.add_handler(peer_creation_conversation)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
