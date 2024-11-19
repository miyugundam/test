# -*- coding: utf-8 -*-
import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Function to load configuration and prompt for missing values only if necessary
def load_config():
    config_path = "config.json"
    config = {}

    # Load the existing config if available
    if os.path.exists(config_path):
        with open(config_path, "r") as config_file:
            try:
                config = json.load(config_file)
            except json.JSONDecodeError:
                print("Invalid JSON in config file. Recreating...")

    # Check if the loaded config has valid values; if not, prompt the user
    if not config.get("telegram_bot_token") or config["telegram_bot_token"] == "YOUR_TELEGRAM_BOT_TOKEN":
        config["telegram_bot_token"] = input("Enter your Telegram Bot Token: ")
    if not config.get("api_base_url") or config["api_base_url"] == "http://localhost:8080":
        config["api_base_url"] = input("Enter your API Base URL (e.g., http://localhost:8080): ")
    if not config.get("api_key") or config["api_key"] == "YOUR_API_KEY":
        config["api_key"] = input("Enter your API Key: ")

    # Save the updated configuration back to the file
    with open(config_path, "w") as config_file:
        json.dump(config, config_file, indent=4)

    return config

# Load the configuration
config = load_config()

# Extract configuration details
TELEGRAM_BOT_TOKEN = config.get("telegram_bot_token")
API_BASE_URL = config.get("api_base_url")
API_KEY = config.get("api_key")

# Helper function to make an authenticated API request
def make_api_request(endpoint, method="GET", data=None):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        if method == "POST":
            # Adding a longer timeout of 30 seconds
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            # Adding a longer timeout of 30 seconds
            response = requests.get(url, headers=headers, timeout=30)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# Function to show the main menu
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = u"🤖 به ربات مانیتورینگ Azumi خوش آمدید! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    
    # Girlish-style buttons
    keyboard = [
        [InlineKeyboardButton(u"📊 آمار ترافیک", callback_data="traffic_stats")],
        [InlineKeyboardButton(u"💻 وضعیت سیستم", callback_data="system_metrics")],
        [InlineKeyboardButton(u"🌐 ایپی‌های متصل", callback_data="connected_ips")],
        [InlineKeyboardButton(u"📝 مشاهده لاگ‌ها", callback_data="tunnel_logs")],
        [InlineKeyboardButton(u"🔄 ریست تانل", callback_data="restart_tunnel")],
        [InlineKeyboardButton(u"🛑 توقف تانل", callback_data="stop_tunnel")],
        [InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")],
        [InlineKeyboardButton(u"🚪 خروج", callback_data="exit_bot")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "traffic_stats":
        await traffic_stats(update, context)
    elif query.data == "system_metrics":
        await system_metrics(update, context)
    elif query.data == "connected_ips":
        await connected_ips(update, context)
    elif query.data == "tunnel_logs":
        await tunnel_logs(update, context)
    elif query.data == "restart_tunnel":
        await restart_tunnel(update, context)
    elif query.data == "stop_tunnel":
        await stop_tunnel(update, context)
    elif query.data == "show_menu":
        await start(update, context)
    elif query.data == "exit_bot":
        await context.bot.send_message(chat_id=chat_id, text="👋 ربات بسته شد.")


# Function to display traffic statistics
async def traffic_stats(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = make_api_request("network-stats")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {data['error']}")
        return

    message = u"📊 آمار ترافیک:\n"
    for port, stats in data.items():
        message += (
            f"پورت {port}:\n"
            f"  🔹 داده‌های ارسال‌شده: {stats['bytes_sent']}\n"
            f"  🔹 داده‌های دریافت‌شده: {stats['bytes_received']}\n"
            f"  🔹 بسته‌های ارسال‌شده: {stats['packets_sent']}\n"
            f"  🔹 بسته‌های دریافت‌شده: {stats['packets_received']}\n\n"
        )
    await context.bot.send_message(chat_id=chat_id, text=message)

# Function to display system metrics
async def system_metrics(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = make_api_request("metrics")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {data['error']}")
        return

    message = (
        f"💻 وضعیت سیستم:\n"
        f"🔹 استفاده از CPU: {data['cpu_usage']}%\n"
        f"🔹 استفاده از RAM: {data['ram_usage']}%\n"
        f"🔹 زمان روشن بودن سیستم: {data.get('uptime', 'نامشخص')}\n"
    )
    await context.bot.send_message(chat_id=chat_id, text=message)

# Function to show connected public IPs with buttons to ban or unban
async def connected_ips(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = make_api_request("public-ip-settings")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {data['error']}")
        return

    message = u"🌐 ایپی‌های متصل:\n"
    keyboard = []

    for ip, status in data["ip_status"].items():
        status_text = "🔴 مسدود" if status == "banned" else "🟢 فعال"
        message += f"<b>IP: {ip}</b> - وضعیت: {status_text}\n"

        # Add buttons for each IP
        if status == "banned":
            keyboard.append([InlineKeyboardButton(f"🚫 رفع انسداد {ip}", callback_data=f"unban_{ip}")])
        else:
            keyboard.append([InlineKeyboardButton(f"🔒 مسدود کردن {ip}", callback_data=f"ban_{ip}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="HTML")

# Function to handle banning an IP
async def ban_ip(chat_id, ip, context):
    response = make_api_request("ban-ip", method="POST", data={"ip": ip})
    message = f"✅ IP {ip} مسدود شد." if "message" in response else f"❌ خطا: {response.get('error')}"
    await context.bot.send_message(chat_id=chat_id, text=message)

# Function to handle unbanning an IP
async def unban_ip(chat_id, ip, context):
    response = make_api_request("unban-ip", method="POST", data={"ip": ip})
    message = f"✅ IP {ip} رفع انسداد شد." if "message" in response else f"❌ خطا: {response.get('error')}"
    await context.bot.send_message(chat_id=chat_id, text=message)

# Function to display tunnel logs
async def tunnel_logs(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = make_api_request("api/tunnel-logs")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {data['error']}")
        return

    logs = data.get("logs", "لاگی برای نمایش وجود ندارد.")
    message = f"📝 لاگ‌های تانل:\n```\n{logs}\n```"
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

# Function to restart the tunnel
async def restart_tunnel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    # Make the API request to restart the tcp_forwarder
    response = make_api_request("restart-tcp-forwarder", method="POST")
    message = "🔄 تانل با موفقیت ریست شد." if "tcp_forwarder restarted." in response else f"❌ خطا: {response.get('error')}"
    await context.bot.send_message(chat_id=chat_id, text=message)

# Function to stop the tunnel
async def stop_tunnel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    # Make the API request to stop the tcp_forwarder
    response = make_api_request("stop-tcp-forwarder", method="POST")
    message = "🛑 تانل با موفقیت متوقف شد." if "tcp_forwarder stopped." in response else f"❌ خطا: {response.get('error')}"
    await context.bot.send_message(chat_id=chat_id, text=message)


# Main function to start the bot
def main():
    # Create an Application instance using your bot token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command and callback query handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Run the bot until it is stopped
    print("Azumi Monitoring Bot started. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
