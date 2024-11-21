# -*- coding: utf-8 -*-
import os
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

def load_config():
    config_path = "config.json"
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as config_file:
            try:
                config = json.load(config_file)
            except json.JSONDecodeError:
                print("JSON is invalid. Recreating...")

    if not config.get("telegram_bot_token") or config["telegram_bot_token"] == "YOUR_TELEGRAM_BOT_TOKEN":
        config["telegram_bot_token"] = input("Enter your Telegram Bot Token: ")
    if not config.get("api_base_url") or config["api_base_url"] == "http://localhost:8080":
        config["api_base_url"] = input("Enter your API Base URL (e.g., http://localhost:8080): ")
    if not config.get("api_key") or config["api_key"] == "YOUR_API_KEY":
        config["api_key"] = input("Enter your API Key: ")

    with open(config_path, "w") as config_file:
        json.dump(config, config_file, indent=4)

    return config

config = load_config()

TELEGRAM_BOT_TOKEN = config.get("telegram_bot_token")
API_BASE_URL = config.get("api_base_url")
API_KEY = config.get("api_key")

def api_request(endpoint, method="GET", data=None):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        if method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)

        print(f"API call to {url} returned status {response.status_code}: {response.text}")

        if response.status_code == 200:
            try:
                return response.json()  
            except json.JSONDecodeError:
                return {"message": response.text} 
        else:
            return {"error": response.text}

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = u"🤖 به ربات مانیتورینگ Azumi خوش آمدید! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"

    keyboard = [
        [InlineKeyboardButton(u"📊 آمار ترافیک", callback_data="traffic_stats")],
        [InlineKeyboardButton(u"💻 وضعیت سیستم", callback_data="system_metrics")],
        [InlineKeyboardButton(u"🌐 ایپی‌های متصل", callback_data="connected_ips")],
        [InlineKeyboardButton(u"📝 مشاهده لاگ‌ها", callback_data="tunnel_logs")],
        [InlineKeyboardButton(u"🔄 ریست فورواردرها", callback_data="restart_tunnel")],
        [InlineKeyboardButton(u"🛑 توقف فورواردرها", callback_data="stop_tunnel")],
        [InlineKeyboardButton(u"🔍 وضعیت فورواردرها", callback_data="tunnel_status")],  # گزینه جدید
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
    elif query.data == "tunnel_status":
        await fetch_forwarder_status(update, context)  
    elif query.data == "show_menu":
        await start(update, context)
    elif query.data == "exit_bot":
        await context.bot.send_message(chat_id=chat_id, text="👋 بای بای")

async def traffic_stats(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = api_request("network-stats")
    
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
    
    keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def system_metrics(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = api_request("metrics")
    
    if "error" in data:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {data['error']}")
        return

    message = (
        f"💻 وضعیت سیستم:\n"
        f"🔹 استفاده از CPU: {data['cpu_usage']}%\n"
        f"🔹 استفاده از RAM: {data['ram_usage']}%\n"
        f"🔹 زمان روشن بودن سیستم: {data.get('uptime', 'نامشخص')}\n"
    )
    
    keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


async def connected_ips(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = api_request("public-ip-settings")

    if "error" in data:
        message = f"❌ خطا: {data['error']}"
        keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)
        return

    message = u"🌐 ایپی‌های متصل:\n"
    keyboard = []

    for ip, status in data["ip_status"].items():
        status_text = "🔴 مسدود" if status == "banned" else "🟢 فعال"
        message += f"<b>IP: {ip}</b> - وضعیت: {status_text}\n"

        if status == "banned":
            keyboard.append([InlineKeyboardButton(f"🚫 رفع انسداد {ip}", callback_data=f"unban_{ip}")])
        else:
            keyboard.append([InlineKeyboardButton(f"🔒 مسدود کردن {ip}", callback_data=f"ban_{ip}")])

    keyboard.append([InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="HTML")

async def ban_ip(chat_id, ip, context):
    response = api_request("ban-ip", method="POST", data={"ip": ip})
    message = f"✅ IP {ip} مسدود شد." if "message" in response else f"❌ خطا: {response.get('error')}"
    
    keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def unban_ip(chat_id, ip, context):
    response = api_request("unban-ip", method="POST", data={"ip": ip})
    message = f"✅ IP {ip} رفع انسداد شد." if "message" in response else f"❌ خطا: {response.get('error')}"
    
    keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def tunnel_logs(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = api_request("api/tunnel-logs")
    
    if "error" in data:
        message = f"❌ خطا: {data['error']}"
    else:
        logs = data.get("logs", "لاگی برای نمایش وجود ندارد.")
        message = f"📝 لاگ‌های تانل:\n```\n{logs}\n```"

    keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown", reply_markup=reply_markup)

async def restart_tunnel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    tcp_response = api_request("restart-tcp-forwarder", method="POST")
    udp_response = api_request("restart-udp-forwarder", method="POST")

    tcp_message = (
        "✅ فورواردر TCP با موفقیت ریست شد."
        if "message" in tcp_response
        else f"❌ خطا در ریست فورواردر TCP: {tcp_response.get('error')}"
    )

    udp_message = (
        "✅ فورواردر UDP با موفقیت ریست شد."
        if "message" in udp_response
        else f"❌ خطا در ریست فورواردر UDP: {udp_response.get('error')}"
    )

    message = f"{tcp_message}\n{udp_message}"
    await context.bot.send_message(chat_id=chat_id, text=message)

async def stop_tunnel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    tcp_response = api_request("stop-tcp-forwarder", method="POST")
    udp_response = api_request("stop-udp-forwarder", method="POST")

    tcp_message = (
        "✅ فورواردر TCP با موفقیت متوقف شد."
        if "message" in tcp_response
        else f"❌ خطا در متوقف کردن فورواردر TCP: {tcp_response.get('error')}"
    )

    udp_message = (
        "✅ فورواردر UDP با موفقیت متوقف شد."
        if "message" in udp_response
        else f"❌ خطا در متوقف کردن فورواردر UDP: {udp_response.get('error')}"
    )

    message = f"{tcp_message}\n{udp_message}"
    await context.bot.send_message(chat_id=chat_id, text=message)

async def fetch_forwarder_status(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    response = api_request("tunnel-status")

    if "error" in response:
        message = f"❌ خطا در دریافت وضعیت فورواردرها: {response['error']}"
    else:
        tcp_status = response.get("tcp_forwarder", "Inactive")
        udp_status = response.get("udp_forwarder", "Inactive")

        tcp_status_text = "🟢 فعال" if tcp_status == "Active" else "🔴 غیرفعال"
        udp_status_text = "🟢 فعال" if udp_status == "Active" else "🔴 غیرفعال"

        message = (
            f"🔍 وضعیت فورواردرها:\n"
            f"  🔹 فورواردر TCP: {tcp_status_text}\n"
            f"  🔹 فورواردر UDP: {udp_status_text}\n"
        )

    keyboard = [[InlineKeyboardButton(u"🔙 بازگشت به منو", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Azumi Monitoring Bot started. Press Ctrl+C to stop.")
    application.run_polling()

main()
