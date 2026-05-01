"""
Flask сервер для лоадера (без Discord бота)
python flask_only.py
"""

import json, os
from datetime import datetime
from flask import Flask, request, jsonify

PORT = 5000
ACCOUNTS = "accounts.json"

def load(f=ACCOUNTS):
    if not os.path.exists(f): return {}
    try:
        with open(f, encoding="utf-8") as fp: return json.load(fp)
    except: return {}

def save(db, f=ACCOUNTS):
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(db, fp, indent=2, ensure_ascii=False)

app = Flask(__name__)

@app.route("/auth", methods=["POST"])
def auth():
    d = request.get_json(force=True) or {}
    action = d.get("action", "launch")

    # Вход
    if action == "login":
        accounts = load(ACCOUNTS)
        login = d.get("login","").lower()
        pw = d.get("password","")
        
        print(f"[LOGIN] Попытка входа: {login}")
        
        if login not in accounts:
            print(f"[LOGIN] Логин не найден: {login}")
            return jsonify({"status": "wrong"})
        
        if accounts[login]["password"] != pw:
            print(f"[LOGIN] Неверный пароль для: {login}")
            return jsonify({"status": "wrong"})
        
        if accounts[login].get("banned"):
            print(f"[LOGIN] Забанен: {login}")
            return jsonify({"status": "banned"})
        
        print(f"[LOGIN] Успешный вход: {login}")
        return jsonify({
            "status": "ok",
            "uid": accounts[login].get("uid", 0),
            "group": accounts[login].get("group", "Пользователь"),
            "subscription_end": accounts[login].get("expires", "Не куплен")
        })

    return jsonify({"status": "error"}), 400

if __name__ == "__main__":
    print(f"[*] Flask сервер запущен на порту {PORT}")
    print(f"[*] Аккаунты загружены из: {ACCOUNTS}")
    
    accounts = load(ACCOUNTS)
    print(f"[*] Найдено аккаунтов: {len(accounts)}")
    for login in accounts:
        print(f"    - {login} (UID: {accounts[login].get('uid', '?')})")
    
    app.run("0.0.0.0", PORT, debug=False)
