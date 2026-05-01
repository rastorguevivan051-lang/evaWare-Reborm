"""
WindowClient Test Bot
pip install flask telebot
python test_bot.py
"""

import json, os, threading
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8594044049:AAHRvLqwt_uVfM1TYAUTWvhsMsV0e4Ddflg"
ADMIN_ID  = 6381036957
PORT      = 5000
DB        = "users.json"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

def load():
    if not os.path.exists(DB): return {}
    try:
        with open(DB, encoding="utf-8") as f: return json.load(f)
    except: return {}

def save(db):
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

@app.route("/auth", methods=["POST"])
def auth():
    d    = request.get_json(force=True) or {}
    hwid = d.get("hwid", "")
    if not hwid: return jsonify({"status": "error"}), 400
    db   = load()
    user = db.get(hwid)
    now  = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    if user is None:
        user = {
            "uid": len(db)+1, "hwid": hwid,
            "name": d.get("client_name","?"), "mc": d.get("username","?"),
            "version": d.get("version","?"), "hardware": d.get("hardware","?"),
            "pc": d.get("pc_name","?"), "os_user": d.get("os_user","?"),
            "status": "unknown", "launches": 1, "first": now, "last": now,
        }
    else:
        user.update({"name": d.get("client_name", user["name"]),
                     "mc": d.get("username", user["mc"]),
                     "hardware": d.get("hardware", user["hardware"]),
                     "pc": d.get("pc_name", user["pc"]),
                     "os_user": d.get("os_user", user["os_user"]),
                     "last": now, "launches": user.get("launches",0)+1})
    db[hwid] = user
    save(db)
    threading.Thread(target=notify, args=(user,), daemon=True).start()
    return jsonify({"status": user["status"], "uid": user["uid"]})

SE = {"active":"✅ Активна","frozen":"❄️ Заморожена","banned":"🚫 Заблокирована","unknown":"❓ Новый"}

def fmt(u):
    return (f"🚀 <b>Запуск клиента</b>\n\n"
            f"🆔 <b>UID:</b> <code>{u['uid']}</code>\n"
            f"🔑 <b>HWID:</b> <code>{u['hwid']}</code>\n"
            f"👤 <b>Имя:</b> <code>{u['name']}</code>\n"
            f"👾 <b>Ник MC:</b> <code>{u['mc']}</code>\n"
            f"🖥 <b>ПК:</b> <code>{u['pc']}</code>\n"
            f"👤 <b>ОС:</b> <code>{u['os_user']}</code>\n"
            f"📦 <b>Версия:</b> <code>{u['version']}</code>\n"
            f"📊 <b>Запусков:</b> <code>{u['launches']}</code>\n"
            f"🕐 <b>Вход:</b> <code>{u['last']}</code>\n"
            f"📋 <b>Статус:</b> {SE.get(u['status'],'❓')}\n\n"
            f"🔧 <b>Железо:</b>\n<code>{u['hardware']}</code>")

def kb(hwid):
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("✅ ACTIVE", callback_data=f"s:active:{hwid}"),
          InlineKeyboardButton("❄️ FROZEN", callback_data=f"s:frozen:{hwid}"),
          InlineKeyboardButton("🚫 BANNED", callback_data=f"s:banned:{hwid}"),
          InlineKeyboardButton("🔓 UNLOCK", callback_data=f"s:active:{hwid}"))
    m.add(InlineKeyboardButton("🔄 Обновить", callback_data=f"r:{hwid}"))
    return m

def notify(u):
    try: bot.send_message(ADMIN_ID, fmt(u), reply_markup=kb(u["hwid"]))
    except Exception as e: print(f"[notify] {e}")

@bot.message_handler(commands=["start","menu"])
def cmd_start(m):
    if m.chat.id != ADMIN_ID: return
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("👥 Пользователи", callback_data="list:0"))
    mk.add(InlineKeyboardButton("📊 Статистика",   callback_data="stats"))
    bot.send_message(ADMIN_ID, "👋 <b>WindowClient Admin Panel</b>", reply_markup=mk)

@bot.message_handler(commands=["find"])
def cmd_find(m):
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2: bot.send_message(ADMIN_ID, "Использование: /find имя"); return
    q = parts[1].strip().lower()
    for hwid, u in load().items():
        if u["name"].lower()==q or u["mc"].lower()==q:
            bot.send_message(ADMIN_ID, fmt(u), reply_markup=kb(hwid)); return
    bot.send_message(ADMIN_ID, f"❌ <code>{q}</code> не найден")

@bot.callback_query_handler(func=lambda c: True)
def on_cb(c):
    if c.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "⛔"); return
    data, cid, mid = c.data, c.message.chat.id, c.message.message_id

    if data.startswith("r:"):
        u = load().get(data[2:])
        if u:
            try: bot.edit_message_text(fmt(u), cid, mid, reply_markup=kb(u["hwid"]))
            except: pass
            bot.answer_callback_query(c.id, "🔄")
        return

    if data.startswith("s:"):
        _, status, hwid = data.split(":", 2)
        db = load()
        if hwid in db:
            db[hwid]["status"] = status; save(db)
            try: bot.edit_message_text(fmt(db[hwid]), cid, mid, reply_markup=kb(hwid))
            except: pass
            bot.answer_callback_query(c.id, {"active":"✅","frozen":"❄️","banned":"🚫"}.get(status,"✅"))
        return

    if data.startswith("list:"):
        page = int(data.split(":")[1])
        db = load(); users = list(db.values())
        per, total = 8, len(users)
        start, end = page*per, min(page*per+per, total)
        text = f"👥 <b>Пользователи</b> ({total}, стр.{page+1}):\n\n"
        mk = InlineKeyboardMarkup(row_width=1)
        for u in users[start:end]:
            e = {"active":"✅","frozen":"❄️","banned":"🚫","unknown":"❓"}.get(u["status"],"❓")
            text += f"{e} UID {u['uid']} — <code>{u['name']}</code>\n"
            mk.add(InlineKeyboardButton(f"{e} UID {u['uid']} — {u['name']}", callback_data=f"u:{u['hwid']}"))
        nav = []
        if page > 0:    nav.append(InlineKeyboardButton("◀️", callback_data=f"list:{page-1}"))
        if end < total: nav.append(InlineKeyboardButton("▶️", callback_data=f"list:{page+1}"))
        if nav: mk.add(*nav)
        try: bot.edit_message_text(text, cid, mid, reply_markup=mk)
        except: bot.send_message(cid, text, reply_markup=mk)
        bot.answer_callback_query(c.id)
        return

    if data.startswith("u:"):
        u = load().get(data[2:])
        if u:
            mk = kb(u["hwid"])
            mk.add(InlineKeyboardButton("◀️ Назад", callback_data="list:0"))
            try: bot.edit_message_text(fmt(u), cid, mid, reply_markup=mk)
            except: bot.send_message(cid, fmt(u), reply_markup=mk)
        bot.answer_callback_query(c.id)
        return

    if data == "stats":
        db = load()
        a = sum(1 for u in db.values() if u["status"]=="active")
        f = sum(1 for u in db.values() if u["status"]=="frozen")
        b = sum(1 for u in db.values() if u["status"]=="banned")
        n = sum(1 for u in db.values() if u["status"]=="unknown")
        text = (f"📊 <b>Статистика</b>\n\n👥 Всего: <b>{len(db)}</b>\n"
                f"✅ Active: <b>{a}</b>\n❄️ Frozen: <b>{f}</b>\n"
                f"🚫 Banned: <b>{b}</b>\n❓ Unknown: <b>{n}</b>")
        try: bot.edit_message_text(text, cid, mid)
        except: bot.send_message(cid, text)
        bot.answer_callback_query(c.id)
        return

    bot.answer_callback_query(c.id)

if __name__ == "__main__":
    print(f"[*] Запуск на порту {PORT}")
    print(f"[*] Для теста: в HwidManager.java поставь http://localhost:5000/auth")
    threading.Thread(
        target=lambda: app.run("0.0.0.0", PORT, debug=False, use_reloader=False),
        daemon=True).start()
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
