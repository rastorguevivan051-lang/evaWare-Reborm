"""
WindowClient HWID Server + Telegram Admin Bot
=============================================
Установка:
    pip install flask python-telegram-bot requests

Запуск:
    python server.py

Настройка:
    1. Вставь BOT_TOKEN от @BotFather
    2. Вставь ADMIN_CHAT_ID (свой Telegram ID, узнать через @userinfobot)
    3. Измени SECRET_KEY на свой (должен совпадать с HwidManager.java)
"""

import json
import os
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, abort
import requests

# ── НАСТРОЙКИ ─────────────────────────────────────────────────────────────────
BOT_TOKEN    = "YOUR_BOT_TOKEN"          # токен от @BotFather
ADMIN_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # твой Telegram ID
SECRET_KEY   = "windowclient-secret-key" # должен совпадать с HwidManager.java
DB_FILE      = "users.json"              # файл базы данных
PORT         = 5000
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)

# ── База данных (JSON файл) ───────────────────────────────────────────────────

def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def get_user(hwid: str) -> dict | None:
    return load_db().get(hwid)

def set_user(hwid: str, data: dict):
    db = load_db()
    db[hwid] = data
    save_db(db)

# ── Telegram уведомления ──────────────────────────────────────────────────────

def tg_send(text: str, reply_markup: dict = None):
    """Отправить сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[TG] Ошибка отправки: {e}")

def tg_edit(chat_id: str, message_id: int, text: str, reply_markup: dict = None):
    """Редактировать сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[TG] Ошибка редактирования: {e}")

def tg_answer_callback(callback_id: str, text: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_id, "text": text}, timeout=5)

def build_user_keyboard(hwid: str, status: str) -> dict:
    """Строим inline-клавиатуру для управления пользователем."""
    buttons = []

    if status == "active":
        buttons.append([
            {"text": "❄️ Заморозить", "callback_data": f"freeze:{hwid}"},
            {"text": "🚫 Заблокировать", "callback_data": f"ban:{hwid}"},
        ])
    elif status == "frozen":
        buttons.append([
            {"text": "✅ Разморозить", "callback_data": f"unfreeze:{hwid}"},
            {"text": "🚫 Заблокировать", "callback_data": f"ban:{hwid}"},
        ])
    elif status == "banned":
        buttons.append([
            {"text": "✅ Разблокировать", "callback_data": f"unban:{hwid}"},
        ])
    elif status == "unknown":
        buttons.append([
            {"text": "✅ Активировать", "callback_data": f"activate:{hwid}"},
            {"text": "🚫 Заблокировать", "callback_data": f"ban:{hwid}"},
        ])

    buttons.append([{"text": "🔄 Обновить", "callback_data": f"refresh:{hwid}"}])
    return {"inline_keyboard": buttons}

def format_user_message(hwid: str, user: dict) -> str:
    status_emoji = {
        "active":  "✅ Активна",
        "frozen":  "❄️ Заморожена",
        "banned":  "🚫 Заблокирована",
        "unknown": "❓ Новый пользователь",
    }.get(user.get("status", "unknown"), "❓ Неизвестно")

    return (
        f"👤 <b>Новый запуск клиента</b>\n\n"
        f"🔑 <b>HWID:</b> <code>{hwid}</code>\n"
        f"👾 <b>Ник:</b> <code>{user.get('username', '?')}</code>\n"
        f"📦 <b>Версия:</b> <code>{user.get('version', '?')}</code>\n"
        f"🕐 <b>Последний вход:</b> <code>{user.get('last_seen', '?')}</code>\n"
        f"📊 <b>Запусков:</b> <code>{user.get('launches', 0)}</code>\n"
        f"📋 <b>Статус подписки:</b> {status_emoji}"
    )

# ── Flask маршруты ────────────────────────────────────────────────────────────

def check_key():
    key = request.headers.get("X-Client-Key", "")
    if key != SECRET_KEY:
        abort(403)

@app.route("/auth", methods=["POST"])
def auth():
    check_key()
    data = request.get_json(force=True)
    hwid     = data.get("hwid", "")
    username = data.get("username", "unknown")
    version  = data.get("version", "?")

    if not hwid:
        return jsonify({"status": "error", "message": "no hwid"}), 400

    db   = load_db()
    user = db.get(hwid)
    now  = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    if user is None:
        # Новый пользователь
        user = {
            "hwid":      hwid,
            "username":  username,
            "version":   version,
            "status":    "unknown",
            "launches":  1,
            "first_seen": now,
            "last_seen": now,
        }
    else:
        user["username"]  = username
        user["version"]   = version
        user["last_seen"] = now
        user["launches"]  = user.get("launches", 0) + 1

    db[hwid] = user
    save_db(db)

    # Уведомление в Telegram
    msg    = format_user_message(hwid, user)
    markup = build_user_keyboard(hwid, user["status"])
    tg_send(msg, markup)

    return jsonify({"status": user["status"]})

@app.route("/status/<hwid>", methods=["GET"])
def status(hwid):
    check_key()
    user = get_user(hwid)
    if user is None:
        return jsonify({"status": "unknown"})
    return jsonify({"status": user["status"]})

# ── Telegram Webhook / Polling ────────────────────────────────────────────────

def handle_callback(callback: dict):
    query_id   = callback["id"]
    chat_id    = str(callback["message"]["chat"]["id"])
    message_id = callback["message"]["message_id"]
    data       = callback.get("data", "")

    # Проверяем что это наш админ
    if chat_id != str(ADMIN_CHAT_ID):
        tg_answer_callback(query_id, "⛔ Нет доступа")
        return

    action, _, hwid = data.partition(":")
    if not hwid:
        tg_answer_callback(query_id, "Ошибка")
        return

    db   = load_db()
    user = db.get(hwid)

    if user is None and action != "activate":
        tg_answer_callback(query_id, "Пользователь не найден")
        return

    action_map = {
        "freeze":   ("frozen",  "❄️ Подписка заморожена"),
        "unfreeze": ("active",  "✅ Подписка разморожена"),
        "ban":      ("banned",  "🚫 Пользователь заблокирован"),
        "unban":    ("active",  "✅ Пользователь разблокирован"),
        "activate": ("active",  "✅ Подписка активирована"),
    }

    if action == "refresh":
        if user:
            msg    = format_user_message(hwid, user)
            markup = build_user_keyboard(hwid, user["status"])
            tg_edit(chat_id, message_id, msg, markup)
            tg_answer_callback(query_id, "🔄 Обновлено")
        return

    if action in action_map:
        new_status, answer_text = action_map[action]
        if user is None:
            user = {"hwid": hwid, "username": "?", "version": "?",
                    "status": new_status, "launches": 0,
                    "first_seen": "?", "last_seen": "?"}
        else:
            user["status"] = new_status
        db[hwid] = user
        save_db(db)

        msg    = format_user_message(hwid, user)
        markup = build_user_keyboard(hwid, user["status"])
        tg_edit(chat_id, message_id, msg, markup)
        tg_answer_callback(query_id, answer_text)

def handle_message(message: dict):
    chat_id = str(message["chat"]["id"])
    text    = message.get("text", "")

    if chat_id != str(ADMIN_CHAT_ID):
        return

    if text == "/start":
        tg_send(
            "👋 <b>WindowClient Admin Panel</b>\n\n"
            "Команды:\n"
            "/users — список всех пользователей\n"
            "/hwid <code>HWID</code> — информация о пользователе\n"
            "/stats — статистика"
        )
    elif text == "/users":
        db = load_db()
        if not db:
            tg_send("📭 Нет пользователей")
            return
        lines = []
        for hwid, u in list(db.items())[:20]:  # первые 20
            emoji = {"active": "✅", "frozen": "❄️", "banned": "🚫"}.get(u.get("status"), "❓")
            lines.append(f"{emoji} <code>{u.get('username','?')}</code> — <code>{hwid[:8]}...</code>")
        tg_send("👥 <b>Пользователи:</b>\n\n" + "\n".join(lines))
    elif text == "/stats":
        db = load_db()
        total   = len(db)
        active  = sum(1 for u in db.values() if u.get("status") == "active")
        frozen  = sum(1 for u in db.values() if u.get("status") == "frozen")
        banned  = sum(1 for u in db.values() if u.get("status") == "banned")
        unknown = sum(1 for u in db.values() if u.get("status") == "unknown")
        tg_send(
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Всего: <b>{total}</b>\n"
            f"✅ Активных: <b>{active}</b>\n"
            f"❄️ Заморожено: <b>{frozen}</b>\n"
            f"🚫 Заблокировано: <b>{banned}</b>\n"
            f"❓ Новых: <b>{unknown}</b>"
        )
    elif text.startswith("/hwid "):
        hwid = text[6:].strip()
        user = get_user(hwid)
        if user is None:
            tg_send(f"❌ HWID <code>{hwid}</code> не найден")
        else:
            msg    = format_user_message(hwid, user)
            markup = build_user_keyboard(hwid, user["status"])
            tg_send(msg, markup)

def polling_loop():
    """Простой long-polling для Telegram бота."""
    offset = 0
    print(f"[BOT] Запущен polling...")
    while True:
        try:
            url  = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            resp = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
            data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(update["callback_query"])
                elif "message" in update:
                    handle_message(update["message"])
        except Exception as e:
            print(f"[BOT] Ошибка polling: {e}")
            time.sleep(5)

# ── Запуск ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[SERVER] WindowClient HWID Server v1.0")
    print(f"[SERVER] Порт: {PORT}")
    print(f"[SERVER] БД: {DB_FILE}")

    # Запускаем Telegram бота в отдельном потоке
    bot_thread = threading.Thread(target=polling_loop, daemon=True)
    bot_thread.start()

    # Запускаем Flask сервер
    app.run(host="0.0.0.0", port=PORT, debug=False)
