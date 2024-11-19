# -*- coding: utf-8 -*-

import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Function to get user input for configuration
def get_user_input(prompt, default_value=None):
    user_input = input(f"{prompt} (Press Enter to use '{default_value}'): ")
    return user_input if user_input else default_value

# Prompt user for inputs
TELEGRAM_BOT_TOKEN = get_user_input("Enter your Telegram Bot Token", "YOUR_TELEGRAM_BOT_TOKEN")
API_BASE_URL = get_user_input("Enter your API Base URL", "http://localhost:8080")
API_KEY = get_user_input("Enter your API Key", "YOUR_API_KEY")

# Helper function to make an authenticated API request
def make_api_request(endpoint):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(f"{API_BASE_URL}/{endpoint}", headers=headers)
    return response.json() if response.status_code == 200 else {"error": response.text}

# Function to start the bot and show options
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = u"👋 به ربات مانیتورینگ خوش آمدید! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"

    keyboard = [
        [InlineKeyboardButton(u"📊 آمار ترافیک", callback_data="traffic_stats")],
        [InlineKeyboardButton(u"💻 وضعیت سیستم", callback_data="system_metrics")],
        [InlineKeyboardButton(u"🌐 مدیریت IP‌های عمومی", callback_data="manage_ips")],
        [InlineKeyboardButton(u"🔄 بازنشانی تونل", callback_data="reset_tunnel")],
        [InlineKeyboardButton(u"🛑 توقف تونل", callback_data="stop_tunnel")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Function to handle button clicks
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "traffic_stats":
        await traffic_stats(update, context)
    elif query.data == "system_metrics":
        await system_metrics(update, context)
    elif query.data == "manage_ips":
        await manage_ips(update, context)
    elif query.data == "reset_tunnel":
        await reset_tunnel(update, context)
    elif query.data == "stop_tunnel":
        await stop_tunnel(update, context)

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
        f"🔹 زمان روشن بودن سیستم: {data['uptime']}\n"
    )
    await context.bot.send_message(chat_id=chat_id, text=message)

# Function to display connected and banned IPs
async def manage_ips(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = make_api_request("public-ip-settings")
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {data['error']}")
        return

    message = u"🌐 IP‌های متصل:\n"
    keyboard = []

    # Show connected IPs
    for ip, status in data.get("ip_status", {}).items():
        status_text = "✅ متصل" if status == "unbanned" else "🚫 مسدود"
        button_text = f"{ip} - {status_text}"
        callback_data = f"ban_{ip}" if status == "unbanned" else f"unban_{ip}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

# Function to handle banning and unbanning IPs
async def ban_unban_ip(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    action, ip = query.data.split("_")

    if action == "ban":
        response = requests.post(f"{API_BASE_URL}/ban-ip", json={"ip": ip})
        if response.status_code == 200:
            await context.bot.send_message(chat_id=chat_id, text=f"🚫 IP {ip} با موفقیت مسدود شد.")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در مسدود کردن IP: {response.text}")
    elif action == "unban":
        response = requests.post(f"{API_BASE_URL}/unban-ip", json={"ip": ip})
        if response.status_code == 200:
            await context.bot.send_message(chat_id=chat_id, text=f"✅ IP {ip} با موفقیت رفع مسدودیت شد.")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در رفع مسدودیت IP: {response.text}")

# Function to reset the tunnel
async def reset_tunnel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=u"🔄 در حال بازنشانی تونل...")
    await context.bot.send_message(chat_id=chat_id, text=u"✅ تونل با موفقیت بازنشانی شد.")

# Function to stop the tunnel
async def stop_tunnel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    response = requests.post(f"{API_BASE_URL}/shutdown")
    if response.status_code == 200:
        await context.bot.send_message(chat_id=chat_id, text=u"🛑 تونل با موفقیت متوقف شد.")
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در توقف تونل: {response.text}")

# Main function to start the bot
def main():
    # Create an Application instance using your bot token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command and callback query handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(ban_unban_ip))

    # Run the bot until it is stopped
    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
