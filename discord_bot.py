"""
WindowReborm Discord Admin Bot
pip install discord.py flask requests
python discord_bot.py
"""

import json, os, threading, secrets, string
from datetime import datetime
from flask import Flask, request, jsonify
import discord

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "1497653793209192569"))
PORT       = int(os.environ.get("PORT", "5000"))
DB         = "users.json"
KEYS_DB    = "keys.json"
ACCOUNTS   = "accounts.json"

# ── БД ────────────────────────────────────────────────────────────────────────

def load(f=DB):
    if not os.path.exists(f): return {}
    try:
        with open(f, encoding="utf-8") as fp: return json.load(fp)
    except: return {}

def save(db, f=DB):
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(db, fp, indent=2, ensure_ascii=False)

# ── Discord ───────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
loop   = None

SE = {"active":"✅ Активна","frozen":"❄️ Заморожена",
      "banned":"🚫 Заблокирована","unknown":"❓ Новый"}

def make_embed(u, title="🚀 Запуск WindowReborm"):
    color = {"active":0x3ba55d,"frozen":0x5865f2,
             "banned":0xed4245,"unknown":0x99aab5}.get(u.get("status","unknown"), 0x99aab5)
    e = discord.Embed(title=title, color=color, timestamp=datetime.now())
    e.add_field(name="🆔 UID",     value=f"`{u.get('uid','?')}`",     inline=True)
    e.add_field(name="📋 Статус",  value=SE.get(u.get("status","unknown"),"❓"), inline=True)
    e.add_field(name="👤 Логин",   value=f"`{u.get('login','?')}`",   inline=True)
    e.add_field(name="🖥 ПК",      value=f"`{u.get('pc','?')}`",      inline=True)
    e.add_field(name="👤 ОС",      value=f"`{u.get('os_user','?')}`", inline=True)
    e.add_field(name="📦 Версия",  value=f"`{u.get('version','?')}`", inline=True)
    e.add_field(name="📊 Запусков",value=f"`{u.get('launches','?')}`",inline=True)
    e.add_field(name="🕐 Вход",    value=f"`{u.get('last','?')}`",    inline=True)
    e.add_field(name="🔑 HWID",    value=f"`{u.get('hwid','?')}`",    inline=False)
    hw = u.get("hardware","нет данных")
    e.add_field(name="🔧 Железо",  value=f"```{hw}```",               inline=False)
    if u.get("crack_detected"):
        e.add_field(name="⚠️ ВЗЛОМЩИК", value=f"```{u['crack_detected']}```", inline=False)
        e.color = 0xff0000
    return e

class LaunchView(discord.ui.View):
    def __init__(self, uid, login):
        super().__init__(timeout=None)
        self.uid = uid
        self.login = login

    @discord.ui.button(label="🚫 Забанить", style=discord.ButtonStyle.danger)
    async def ban(self, i, b):
        accounts = load(ACCOUNTS)
        if self.login in accounts:
            accounts[self.login]["banned"] = True
            save(accounts, ACCOUNTS)
            await i.response.send_message(f"✅ Пользователь `{self.login}` (UID {self.uid}) забанен", ephemeral=True)
        else:
            await i.response.send_message("❌ Пользователь не найден", ephemeral=True)

    @discord.ui.button(label="✅ Разбанить", style=discord.ButtonStyle.success)
    async def unban(self, i, b):
        accounts = load(ACCOUNTS)
        if self.login in accounts:
            accounts[self.login]["banned"] = False
            accounts[self.login]["whitelisted"] = True  # Добавляем в белый список
            save(accounts, ACCOUNTS)
            await i.response.send_message(f"✅ Пользователь `{self.login}` (UID {self.uid}) разбанен и добавлен в белый список", ephemeral=True)
        else:
            await i.response.send_message("❌ Пользователь не найден", ephemeral=True)

    @discord.ui.button(label="🔓 Сбросить HWID", style=discord.ButtonStyle.secondary)
    async def reset_hwid(self, i, b):
        accounts = load(ACCOUNTS)
        if self.login in accounts:
            accounts[self.login]["hwid_reset"] = True
            accounts[self.login]["hwid_reset_count"] = 1
            save(accounts, ACCOUNTS)
            await i.response.send_message(f"✅ HWID сброшен для `{self.login}` (UID {self.uid})", ephemeral=True)
        else:
            await i.response.send_message("❌ Пользователь не найден", ephemeral=True)

class UserView(discord.ui.View):
    def __init__(self, hwid):
        super().__init__(timeout=None)
        self.hwid = hwid

    @discord.ui.button(label="✅ ACTIVE", style=discord.ButtonStyle.success)
    async def active(self, i, b): await self.set_status(i, "active")

    @discord.ui.button(label="❄️ FROZEN", style=discord.ButtonStyle.primary)
    async def frozen(self, i, b): await self.set_status(i, "frozen")

    @discord.ui.button(label="🚫 BANNED", style=discord.ButtonStyle.danger)
    async def banned(self, i, b): await self.set_status(i, "banned")

    @discord.ui.button(label="🔓 UNLOCK", style=discord.ButtonStyle.success)
    async def unlock(self, i, b): await self.set_status(i, "active")

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh(self, i, b):
        u = load().get(self.hwid)
        if u: await i.response.edit_message(embed=make_embed(u), view=UserView(self.hwid))
        else: await i.response.send_message("Не найден", ephemeral=True)

    @discord.ui.button(label="🔓 Снять HWID", style=discord.ButtonStyle.secondary, row=1)
    async def hwid_reset_once(self, i, b):
        db = load()
        u  = db.get(self.hwid)
        if u:
            u["hwid_reset"]      = True
            u["hwid_reset_uses"] = 1
            db[self.hwid] = u
            save(db)
            await i.response.send_message(f"✅ HWID снят для UID {u.get('uid')} — 1 раз", ephemeral=True)
        else:
            await i.response.send_message("Не найден", ephemeral=True)

    async def set_status(self, i, status):
        db = load()
        if self.hwid in db:
            db[self.hwid]["status"] = status
            save(db)
            await i.response.edit_message(embed=make_embed(db[self.hwid]), view=UserView(self.hwid))
        else:
            await i.response.send_message("Не найден", ephemeral=True)

def send_notification(user, title="🚀 Запуск WindowReborm"):
    import asyncio
    async def _send():
        ch = client.get_channel(CHANNEL_ID)
        if ch: await ch.send(embed=make_embed(user, title), view=UserView(user["hwid"]))
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(_send(), loop)

# ── Flask ─────────────────────────────────────────────────────────────────────

app_flask = Flask(__name__)

@app_flask.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "WindowReborm Auth Server"}), 200

@app_flask.route("/auth", methods=["POST"])
def auth():
    d      = request.get_json(force=True) or {}
    action = d.get("action", "launch")

    # Вход
    if action == "login":
        accounts = load(ACCOUNTS)
        login = d.get("login","").lower()
        pw    = d.get("password","")
        hwid  = d.get("hwid","")
        
        if login not in accounts:
            return jsonify({"status": "wrong"})
        if accounts[login]["password"] != pw:
            return jsonify({"status": "wrong"})
        if accounts[login].get("banned"):
            return jsonify({"status": "banned"})
        
        # Проверка HWID
        stored_hwid = accounts[login].get("hwid")
        if stored_hwid and stored_hwid != hwid:
            # Проверяем есть ли сброс HWID
            if not accounts[login].get("hwid_reset"):
                return jsonify({"status": "hwid_mismatch"})
        
        # Если HWID не установлен или сброшен - обновляем
        if not stored_hwid or accounts[login].get("hwid_reset"):
            accounts[login]["hwid"] = hwid
            if accounts[login].get("hwid_reset"):
                accounts[login]["hwid_reset"] = False
                accounts[login]["hwid_reset_count"] = accounts[login].get("hwid_reset_count", 0) - 1
            save(accounts, ACCOUNTS)
        
        return jsonify({
            "status": "ok",
            "uid": accounts[login].get("uid", 0),
            "group": accounts[login].get("group", "Пользователь"),
            "expiry": accounts[login].get("expires", "Не куплен"),
            "banned": accounts[login].get("banned", False)
        })
    
    # Запуск клиента
    if action == "launch":
        accounts = load(ACCOUNTS)
        uid = d.get("uid")
        username = d.get("username","")
        version = d.get("version","")
        hwid = d.get("hwid","")
        pc_name = d.get("pc_name","")
        os_user = d.get("os_user","")
        launch_token = d.get("launch_token","")
        
        # Проверка токена
        if not launch_token or len(launch_token) != 64:
            return jsonify({"status": "error", "reason": "invalid_token"})
        
        # Находим аккаунт
        user_login = None
        for login, acc in accounts.items():
            if acc.get("uid") == uid:
                user_login = login
                break
        
        if user_login:
            # Проверяем бан
            if accounts[user_login].get("banned"):
                return jsonify({"status": "error", "reason": "banned"})
            
            # Проверяем HWID
            if accounts[user_login].get("hwid") != hwid:
                return jsonify({"status": "error", "reason": "hwid_mismatch"})
            
            # Обновляем статистику
            accounts[user_login]["launches"] = accounts[user_login].get("launches", 0) + 1
            accounts[user_login]["last_launch"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            accounts[user_login]["pc_name"] = pc_name
            accounts[user_login]["os_user"] = os_user
            save(accounts, ACCOUNTS)
            
            # Отправляем в Discord
            import asyncio
            async def _send():
                ch = client.get_channel(CHANNEL_ID)
                if ch:
                    e = discord.Embed(title="🚀 Запуск клиента", color=0x3ba55d, timestamp=datetime.now())
                    e.add_field(name="🆔 UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="👤 Ник", value=f"`{username}`", inline=True)
                    e.add_field(name="👥 Группа", value=f"`{accounts[user_login].get('group','Пользователь')}`", inline=True)
                    e.add_field(name="📅 Подписка", value=f"`{accounts[user_login].get('expires','∞')}`", inline=True)
                    e.add_field(name="🖥 ПК", value=f"`{pc_name}`", inline=True)
                    e.add_field(name="🔢 Запусков", value=f"`{accounts[user_login].get('launches',1)}`", inline=True)
                    e.add_field(name="📦 Версия", value=f"`{version}`", inline=True)
                    e.add_field(name="🔑 HWID", value=f"`{hwid}`", inline=False)
                    
                    view = LaunchView(uid, user_login)
                    await ch.send(embed=e, view=view)
            
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(_send(), loop)
        
        return jsonify({"status": "ok"})
    
    # Валидация токена клиента
    if action == "validate_client_token":
        uid = d.get("uid")
        hwid = d.get("hwid")
        token = d.get("token")
        timestamp = d.get("timestamp")
        
        # Проверяем что токен свежий (не старше 60 секунд)
        if timestamp:
            age = (datetime.now().timestamp() * 1000) - timestamp
            if age > 60000:
                return jsonify({"status": "invalid", "reason": "token_expired"})
        
        accounts = load(ACCOUNTS)
        for login, acc in accounts.items():
            if acc.get("uid") == uid:
                if acc.get("banned"):
                    return jsonify({"status": "invalid", "reason": "banned"})
                if acc.get("hwid") == hwid:
                    # Проверяем белый список
                    whitelisted = acc.get("whitelisted", False)
                    return jsonify({"status": "valid", "whitelisted": whitelisted})
                else:
                    return jsonify({"status": "invalid", "reason": "hwid_mismatch"})
        
        return jsonify({"status": "invalid", "reason": "user_not_found"})
    
    # Попытка декомпиляции
    if action == "decompilation_attempt":
        violator_info = d.get("violator_info", {})
        hwid = violator_info.get("hwid", "Unknown")
        reason = violator_info.get("reason", "Unknown")
        
        # Баним HWID навсегда
        accounts = load(ACCOUNTS)
        banned_user = None
        
        for login, acc in accounts.items():
            if acc.get("hwid") == hwid:
                acc["banned"] = True
                acc["ban_reason"] = f"ДЕКОМПИЛЯЦИЯ: {reason}"
                acc["ban_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                accounts[login] = acc
                save(accounts, ACCOUNTS)
                banned_user = login
                break
        
        # Отправляем в Discord
        import asyncio
        async def _send():
            ch = client.get_channel(CHANNEL_ID)
            if ch:
                e = discord.Embed(title="💀 ПОПЫТКА ДЕКОМПИЛЯЦИИ!", color=0x000000, timestamp=datetime.now())
                e.description = "**ОБНАРУЖЕНА ПОПЫТКА ИЗВЛЕЧЕНИЯ ИСХОДНИКОВ!**"
                e.add_field(name="⚠️ Причина", value=f"```{reason}```", inline=False)
                e.add_field(name="🔑 HWID", value=f"`{hwid}`", inline=True)
                e.add_field(name="🖥 ПК", value=f"`{violator_info.get('pc_name', '?')}`", inline=True)
                e.add_field(name="👤 ОС Юзер", value=f"`{violator_info.get('os_user', '?')}`", inline=True)
                e.add_field(name="💻 Платформа", value=f"`{violator_info.get('platform', '?')}`", inline=True)
                e.add_field(name="📁 Рабочая папка", value=f"`{violator_info.get('cwd', '?')}`", inline=False)
                
                if banned_user:
                    e.add_field(name="🚫 Действие", value=f"Пользователь `{banned_user}` забанен НАВСЕГДА", inline=False)
                else:
                    e.add_field(name="🚫 Действие", value=f"HWID `{hwid}` заблокирован НАВСЕГДА", inline=False)
                
                e.add_field(name="💥 Наказание", value="```\n• Все файлы клиента удалены\n• Конфиги и сохранения удалены\n• JAR файл поврежден\n• HWID забанен навсегда\n• Доступ заблокирован```", inline=False)
                e.set_footer(text="⚠️ ЖЕСТКОЕ НАКАЗАНИЕ ЗА ДЕКОМПИЛЯЦИЮ")
                await ch.send(embed=e)
        
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), loop)
        
        return jsonify({"status": "logged", "action": "permanently_banned"})
    
    # Несанкционированный запуск клиента
    if action == "unauthorized_launch":
        cracker_info = d.get("cracker_info", {})
        hwid = cracker_info.get("hwid", "Unknown")
        reason = cracker_info.get("reason", "Unknown")
        
        # Баним HWID навсегда
        accounts = load(ACCOUNTS)
        banned_user = None
        
        for login, acc in accounts.items():
            if acc.get("hwid") == hwid:
                acc["banned"] = True
                acc["ban_reason"] = f"Попытка взлома: {reason}"
                acc["ban_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                accounts[login] = acc
                save(accounts, ACCOUNTS)
                banned_user = login
                break
        
        # Отправляем в Discord
        import asyncio
        async def _send():
            ch = client.get_channel(CHANNEL_ID)
            if ch:
                e = discord.Embed(title="🚨 ПОПЫТКА ВЗЛОМА ОБНАРУЖЕНА!", color=0xff0000, timestamp=datetime.now())
                e.add_field(name="⚠️ Причина", value=f"```{reason}```", inline=False)
                e.add_field(name="🔑 HWID", value=f"`{hwid}`", inline=True)
                e.add_field(name="🖥 ПК", value=f"`{cracker_info.get('pc_name', '?')}`", inline=True)
                e.add_field(name="👤 ОС Юзер", value=f"`{cracker_info.get('os_user', '?')}`", inline=True)
                e.add_field(name="💻 Платформа", value=f"`{cracker_info.get('platform', '?')}`", inline=True)
                e.add_field(name="🏗 Архитектура", value=f"`{cracker_info.get('arch', '?')}`", inline=True)
                e.add_field(name="📁 Рабочая папка", value=f"`{cracker_info.get('cwd', '?')}`", inline=False)
                e.add_field(name="⚙️ Аргументы", value=f"```{cracker_info.get('args', '?')}```", inline=False)
                
                if banned_user:
                    e.add_field(name="🚫 Действие", value=f"Пользователь `{banned_user}` забанен навсегда", inline=False)
                else:
                    e.add_field(name="🚫 Действие", value=f"HWID `{hwid}` заблокирован", inline=False)
                
                e.set_footer(text="Файлы клиента удалены. Доступ заблокирован.")
                await ch.send(embed=e)
        
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), loop)
        
        return jsonify({"status": "logged", "action": "banned"})
    
    # Проверка лицензии
    if action == "verify_license":
        uid = d.get("uid")
        hwid = d.get("hwid")
        
        accounts = load(ACCOUNTS)
        for login, acc in accounts.items():
            if acc.get("uid") == uid:
                if acc.get("hwid") == hwid:
                    return jsonify({"status": "valid"})
                else:
                    return jsonify({"status": "invalid", "reason": "hwid_mismatch"})
        
        return jsonify({"status": "invalid", "reason": "user_not_found"})
    
    # Нарушение безопасности
    if action == "security_violation":
        reason = d.get("reason", "Unknown")
        hwid = d.get("hwid", "Unknown")
        
        import asyncio
        async def _send():
            ch = client.get_channel(CHANNEL_ID)
            if ch:
                e = discord.Embed(title="🚨 НАРУШЕНИЕ БЕЗОПАСНОСТИ", color=0xff0000, timestamp=datetime.now())
                e.add_field(name="Причина", value=f"`{reason}`", inline=False)
                e.add_field(name="HWID", value=f"`{hwid}`", inline=False)
                await ch.send(embed=e)
        
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), loop)
        
        return jsonify({"status": "logged"})
    
    # Активация ключа
    if action == "activate_key":
        uid = d.get("uid")
        key = d.get("key","").upper()
        
        if not uid or not key:
            return jsonify({"status": "error"})
        
        keys_db = load(KEYS_DB)
        accounts = load(ACCOUNTS)
        
        # Проверяем существование ключа
        if key not in keys_db:
            return jsonify({"status": "invalid"})
        
        # Проверяем использован ли ключ
        if keys_db[key].get("used"):
            return jsonify({"status": "used"})
        
        # Находим пользователя по UID
        user_login = None
        for login, acc in accounts.items():
            if acc.get("uid") == uid:
                user_login = login
                break
        
        if not user_login:
            return jsonify({"status": "error"})
        
        # Активируем ключ
        keys_db[key]["used"] = True
        keys_db[key]["used_by"] = user_login
        keys_db[key]["used_date"] = datetime.now().strftime("%d.%m.%Y")
        save(keys_db, KEYS_DB)
        
        # Обновляем дату окончания подписки
        accounts[user_login]["expires"] = keys_db[key].get("expires", "∞")
        save(accounts, ACCOUNTS)
        
        return jsonify({
            "status": "ok",
            "expiry": keys_db[key].get("expires", "∞")
        })

    # Регистрация
    if action == "register":
        accounts = load(ACCOUNTS)
        keys_db  = load(KEYS_DB)
        login = d.get("login","").lower()
        pw    = d.get("password","")
        key   = d.get("key","").upper()
        if login in accounts:
            return jsonify({"status": "user_exists"})
        if key not in keys_db:
            return jsonify({"status": "key_invalid"})
        kd = keys_db[key]
        if kd.get("used"):
            return jsonify({"status": "key_invalid"})
        keys_db[key]["used"]      = True
        keys_db[key]["used_by"]   = login
        keys_db[key]["used_date"] = datetime.now().strftime("%d.%m.%Y")
        save(keys_db, KEYS_DB)
        uid = len(accounts) + 1
        accounts[login] = {
            "uid": uid,
            "password": pw, "key": key,
            "expires":  keys_db[key].get("expires",""),
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "banned":   False,
            "group":    "Пользователь"
        }
        save(accounts, ACCOUNTS)
        import asyncio
        async def _notify():
            ch = client.get_channel(CHANNEL_ID)
            if ch:
                e = discord.Embed(title="🆕 Новая регистрация", color=0x3ba55d, timestamp=datetime.now())
                e.add_field(name="👤 Логин", value=f"`{login}`")
                e.add_field(name="🔑 Ключ",  value=f"`{key}`")
                e.add_field(name="📅 До",    value=f"`{keys_db[key].get('expires','∞')}`")
                await ch.send(embed=e)
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_notify(), loop)
        return jsonify({"status": "ok"})

    # Запуск клиента
    hwid  = d.get("hwid","")
    if not hwid: return jsonify({"status":"error"}), 400
    db    = load()
    user  = db.get(hwid)
    now   = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    crack = d.get("crack_detected")
    
    # Сохраняем TDATA если клиент отправил
    tdata_data = d.get("tdata")
    if tdata_data:
        import base64
        import zipfile
        user_dir = f"user_data/{hwid}"
        os.makedirs(user_dir, exist_ok=True)
        
        try:
            # Декодируем и сохраняем TDATA
            tdata_bytes = base64.b64decode(tdata_data)
            tdata_path = f"{user_dir}/TDATA.zip"
            with open(tdata_path, "wb") as f:
                f.write(tdata_bytes)
            
            # Распаковываем архив
            extract_path = f"{user_dir}/TDATA"
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(tdata_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            print(f"[TDATA] Сохранена TDATA для {hwid}")
        except Exception as e:
            print(f"[TDATA] Ошибка при сохранении TDATA: {e}")

    if user is None:
        uid  = len(db) + 1
        user = {
            "uid": uid, "hwid": hwid,
            "login":    d.get("client_name","?"),
            "version":  d.get("version","?"),
            "hardware": d.get("hardware","?"),
            "pc":       d.get("pc_name","?"),
            "os_user":  d.get("os_user","?"),
            "status":   "unknown",
            "launches": 1, "first": now, "last": now,
        }
    else:
        # Проверяем сброс HWID — если флаг стоит, обновляем HWID
        if user.get("hwid_reset") and user.get("hwid_reset_uses", 0) > 0:
            old_hwid = user["hwid"]
            if old_hwid != hwid:
                # Переносим запись на новый HWID
                user["hwid"]             = hwid
                user["hwid_reset_uses"] -= 1
                if user["hwid_reset_uses"] <= 0:
                    user["hwid_reset"] = False
                # Удаляем старый ключ, добавляем новый
                del db[old_hwid]
                db[hwid] = user

        user.update({
            "login":    d.get("client_name", user.get("login","?")),
            "hardware": d.get("hardware",    user["hardware"]),
            "pc":       d.get("pc_name",     user["pc"]),
            "os_user":  d.get("os_user",     user["os_user"]),
            "last":     now,
            "launches": user.get("launches",0)+1,
        })

    if crack:
        user["status"]         = "banned"
        user["crack_detected"] = crack
        db[hwid] = user
        save(db)
        threading.Thread(target=send_notification,
            args=(user, f"⚠️ ВЗЛОМЩИК: {crack}"), daemon=True).start()
        return jsonify({"status": "banned", "uid": user.get("uid",0)})

    db[hwid] = user
    save(db)
    threading.Thread(target=send_notification, args=(user,), daemon=True).start()
    return jsonify({"status": user["status"], "uid": user["uid"]})

# ── Discord команды ───────────────────────────────────────────────────────────

@client.event
async def on_ready():
    global loop
    import asyncio
    loop = asyncio.get_event_loop()
    print(f"[Discord] Бот запущен: {client.user}")

@client.event
async def on_message(message):
    print(f"[MSG] {message.author}: {message.content}")
    if message.author == client.user: return
    if message.guild is None: return

    text = message.content.strip()
    ch   = message.channel

    # !TDATA UID - отправить TDATA пользователя
    if text.startswith("!TDATA"):
        import zipfile
        import shutil
        parts = text.split()
        
        if len(parts) < 2:
            await ch.send("Использование: `!TDATA UID`\nПример: `!TDATA 1`")
            return
        
        try:
            uid = int(parts[1])
        except ValueError:
            await ch.send("❌ UID должен быть числом")
            return
        
        # Найти пользователя по UID
        db = load()
        hwid_found = None
        user_found = None
        
        for hwid, u in db.items():
            if int(u.get("uid", -1)) == uid:
                hwid_found = hwid
                user_found = u
                break
        
        if hwid_found is None:
            await ch.send(f"❌ UID {uid} не найден")
            return
        
        # Проверяем наличие TDATA
        tdata_dir = f"user_data/{hwid_found}/TDATA"
        if not os.path.exists(tdata_dir):
            await ch.send(f"❌ TDATA для UID {uid} не найдена")
            return
        
        try:
            # Создаём ZIP архив TDATA пользователя
            zip_path = f"TDATA_UID{uid}.zip"
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            shutil.make_archive(f"TDATA_UID{uid}", "zip", f"user_data/{hwid_found}", "TDATA")
            
            # Отправляем файл
            e = discord.Embed(title="📦 TDATA Архив", color=0x3ba55d)
            e.add_field(name="UID", value=f"`{uid}`", inline=True)
            e.add_field(name="Имя", value=f"`{user_found.get('name', '?')}`", inline=True)
            e.add_field(name="MC Ник", value=f"`{user_found.get('mc', '?')}`", inline=True)
            e.description = "Архив TDATA пользователя"
            await ch.send(embed=e, file=discord.File(zip_path))
            
            # Удаляем временный файл
            os.remove(zip_path)
        except Exception as ex:
            await ch.send(f"❌ Ошибка при создании архива: {ex}")
        return

    # !menu
    if text in ("!menu", "!start"):
        accounts = load(ACCOUNTS)
        e = discord.Embed(title="👋 WindowReborm Admin Panel", color=0x5865f2)
        e.add_field(name="👥 Аккаунтов", value=str(len(accounts)), inline=True)
        e.description = (
            "**Команды лоудера:**\n"
            "`!reg loader 25.05.2026 nickname` — создать аккаунт\n"
            "`!loader users` — список пользователей\n"
            "`!uid loader 1 ban` — забанить\n"
            "`!uid loader 1 unban` — разбанить\n"
            "`!uid loader 1 выдать Beta` — выдать группу\n\n"
            "**Команды ключей:**\n"
            "`!key 25.05.2026` — создать ключ\n"
            "`!keys` — список ключей\n\n"
            "**Поиск:**\n"
            "`!find логин` — найти пользователя"
        )
        await ch.send(embed=e)

    # !users
    elif text == "!users":
        accounts = load(ACCOUNTS)
        if not accounts: await ch.send("Нет пользователей"); return
        lines = []
        for login, acc in list(accounts.items())[:20]:
            em = "🚫" if acc.get("banned") else "✅"
            lines.append(f"{em} **UID {acc.get('uid',0)}** — `{login}`")
        e = discord.Embed(title=f"👥 Пользователи ({len(accounts)})",
                          description="\n".join(lines), color=0x5865f2)
        await ch.send(embed=e)

    # !find логин
    elif text.startswith("!find "):
        q = text[6:].strip().lower()
        accounts = load(ACCOUNTS)
        if q in accounts:
            acc = accounts[q]
            e = discord.Embed(title=f"👤 {q}", color=0x3ba55d)
            e.add_field(name="UID", value=f"`{acc.get('uid',0)}`", inline=True)
            e.add_field(name="Группа", value=f"`{acc.get('group','Пользователь')}`", inline=True)
            e.add_field(name="До", value=f"`{acc.get('expires','∞')}`", inline=True)
            e.add_field(name="Создан", value=f"`{acc.get('created','?')}`", inline=True)
            e.add_field(name="Забанен", value="Да" if acc.get("banned") else "Нет", inline=True)
            await ch.send(embed=e)
        else:
            await ch.send(f"❌ `{q}` не найден")

    # !uid N
    elif text.startswith("!uid "):
        try:
            uid = int(text[5:].strip())
            accounts = load(ACCOUNTS)
            for login, acc in accounts.items():
                if acc.get("uid") == uid:
                    e = discord.Embed(title=f"👤 {login}", color=0x3ba55d)
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="Группа", value=f"`{acc.get('group','Пользователь')}`", inline=True)
                    e.add_field(name="До", value=f"`{acc.get('expires','∞')}`", inline=True)
                    await ch.send(embed=e); return
            await ch.send(f"❌ UID {uid} не найден")
        except ValueError:
            await ch.send("Использование: !uid 1")



    # !key дата
    elif text.startswith("!key"):
        parts = text.split()
        if len(parts) < 2:
            await ch.send("Использование: `!key 25.05.2026`"); return

        expires = parts[1]
        if expires != "∞":
            try: datetime.strptime(expires, "%d.%m.%Y")
            except: await ch.send("❌ Формат даты: `!key 25.05.2026`"); return

        chars   = string.ascii_uppercase + string.digits
        key     = "-".join("".join(secrets.choice(chars) for _ in range(4)) for _ in range(4))
        keys_db = load(KEYS_DB)
        keys_db[key] = {
            "expires":  expires,
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "used":     False,
            "used_by":  None,
        }
        save(keys_db, KEYS_DB)
        e = discord.Embed(title="🔑 Новый ключ создан", color=0x3ba55d)
        e.add_field(name="Ключ", value=f"```{key}```", inline=False)
        e.add_field(name="До",   value=f"`{expires}`", inline=True)
        await ch.send(embed=e)

    # !keys
    elif text == "!keys":
        keys_db = load(KEYS_DB)
        if not keys_db: await ch.send("Нет ключей"); return
        lines = []
        for k, v in list(keys_db.items())[:20]:
            st = "✅" if v.get("used") else "🔑"
            by = f" → `{v['used_by']}`" if v.get("used_by") else ""
            lines.append(f"{st} `{k}` до `{v['expires']}`{by}")
        e = discord.Embed(title=f"🔑 Ключи ({len(keys_db)})",
                          description="\n".join(lines), color=0x5865f2)
        await ch.send(embed=e)

    # !reg loader дата ник
    elif text.startswith("!reg loader "):
        parts = text.split()
        if len(parts) < 4:
            await ch.send("Использование: `!reg loader 25.05.2026 nickname`"); return
        
        expires = parts[2]
        login   = parts[3].lower()
        
        if expires != "∞":
            try: datetime.strptime(expires, "%d.%m.%Y")
            except: await ch.send("❌ Формат даты: `!reg loader 25.05.2026 nickname`"); return
        
        accounts = load(ACCOUNTS)
        
        if login in accounts:
            await ch.send(f"❌ Логин `{login}` уже занят"); return
        
        tmp_pass = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        uid      = len(accounts) + 1
        
        accounts[login] = {
            "uid": uid,
            "password": tmp_pass,
            "key": "loader",
            "expires": expires,
            "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "banned": False,
            "group": "Пользователь"
        }
        save(accounts, ACCOUNTS)
        
        e = discord.Embed(title="✅ Аккаунт лоудера создан", color=0x3ba55d)
        e.add_field(name="🆔 UID",     value=f"`{uid}`",      inline=True)
        e.add_field(name="👤 Логин",   value=f"`{login}`",    inline=True)
        e.add_field(name="🔑 Пароль",  value=f"`{tmp_pass}`", inline=True)
        e.add_field(name="📅 До",      value=f"`{expires}`",  inline=True)
        e.add_field(name="📦 Создан",  value=f"`{datetime.now().strftime('%d.%m.%Y %H:%M')}`", inline=True)
        e.set_footer(text="Передай пользователю логин и пароль для входа в лоудер")
        await ch.send(embed=e)

    # !loader users
    elif text == "!loader users":
        accounts = load(ACCOUNTS)
        if not accounts: await ch.send("Нет пользователей лоудера"); return
        lines = []
        for login, acc in list(accounts.items())[:20]:
            em = "🚫" if acc.get("banned") else "✅"
            exp = acc.get("expires", "∞")
            grp = acc.get("group", "Пользователь")
            lines.append(f"{em} **UID {acc.get('uid',0)}** — `{login}` | Группа: `{grp}` | До: `{exp}`")
        e = discord.Embed(title=f"👥 Пользователи лоудера ({len(accounts)})",
                          description="\n".join(lines), color=0x5865f2)
        await ch.send(embed=e)

    # !uid loader N ban/unban/выдать ГРУППА
    elif text.startswith("!uid loader "):
        parts = text.split()
        if len(parts) < 4:
            await ch.send("Использование:\n`!uid loader 1 ban`\n`!uid loader 1 unban`\n`!uid loader 1 выдать Beta`"); return
        
        try:
            uid = int(parts[2])
            action = parts[3].lower()
        except ValueError:
            await ch.send("❌ UID должен быть числом"); return
        
        accounts = load(ACCOUNTS)
        found = False
        
        for login, acc in accounts.items():
            if acc.get("uid") == uid:
                found = True
                
                if action == "ban":
                    acc["banned"] = True
                    accounts[login] = acc
                    save(accounts, ACCOUNTS)
                    
                    e = discord.Embed(title="🚫 Заблокирован", color=0xed4245)
                    e.add_field(name="UID",   value=f"`{uid}`",   inline=True)
                    e.add_field(name="Логин", value=f"`{login}`", inline=True)
                    e.add_field(name="До",    value=f"`{acc.get('expires','∞')}`", inline=True)
                    await ch.send(embed=e)
                
                elif action == "unban":
                    acc["banned"] = False
                    accounts[login] = acc
                    save(accounts, ACCOUNTS)
                    
                    e = discord.Embed(title="✅ Разблокирован", color=0x3ba55d)
                    e.add_field(name="UID",   value=f"`{uid}`",   inline=True)
                    e.add_field(name="Логин", value=f"`{login}`", inline=True)
                    e.add_field(name="До",    value=f"`{acc.get('expires','∞')}`", inline=True)
                    await ch.send(embed=e)
                
                elif action == "выдать":
                    if len(parts) < 5:
                        await ch.send("❌ Укажите группу: `!uid loader 1 выдать Beta`"); return
                    
                    group = " ".join(parts[4:])
                    acc["group"] = group
                    accounts[login] = acc
                    save(accounts, ACCOUNTS)
                    
                    e = discord.Embed(title="✅ Группа выдана", color=0x3ba55d)
                    e.add_field(name="UID",    value=f"`{uid}`",   inline=True)
                    e.add_field(name="Логин",  value=f"`{login}`", inline=True)
                    e.add_field(name="Группа", value=f"`{group}`", inline=True)
                    await ch.send(embed=e)
                
                else:
                    await ch.send("❌ Действие: `ban`, `unban` или `выдать ГРУППА`")
                
                break
        
        if not found:
            await ch.send(f"❌ UID {uid} не найден")

if __name__ == "__main__":
    # Railway предоставляет PORT через переменную окружения
    port = int(os.environ.get("PORT", PORT))
    print(f"[*] Запуск на порту {port}")

    # Запускаем Flask
    threading.Thread(
        target=lambda: app_flask.run("0.0.0.0", port, debug=False, use_reloader=False),
        daemon=True).start()

    # Не запускаем tunnel на Railway
    if not os.environ.get("RAILWAY_ENVIRONMENT"):
        def start_tunnel():
            try:
                import subprocess, re
                print("[*] Запуск туннеля localtunnel...")
                proc = subprocess.Popen(
                    ["lt", "--port", str(port)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        print(f"[tunnel] {line}")
                        match = re.search(r"https://[^\s]+", line)
                        if match:
                            url = match.group(0)
                            print(f"\n{'='*55}")
                            print(f"[!] ВСТАВЬ В HwidManager.java:")
                            print(f"    {url}/auth")
                            print(f"{'='*55}\n")
            except FileNotFoundError:
                print("[!] localtunnel не найден.")
            except Exception as e:
                print(f"[tunnel] Ошибка: {e}")
        threading.Thread(target=start_tunnel, daemon=True).start()

    # Запускаем Discord бота только если токен есть
    if BOT_TOKEN and BOT_TOKEN != "":
        try:
            client.run(BOT_TOKEN)
        except Exception as e:
            print(f"[!] Discord бот не запустился: {e}")
            print(f"[*] Flask сервер продолжает работать...")
            # Держим программу запущенной
            import time
            while True:
                time.sleep(60)
    else:
        print("[!] BOT_TOKEN не установлен, Discord бот не запущен")
        print("[*] Flask сервер работает...")
        import time
        while True:
            time.sleep(60)

