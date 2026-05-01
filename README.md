# WindowClient HWID Server

## Быстрый старт

### 1. Установка
```bash
pip install -r requirements.txt
```

### 2. Настройка server.py
Открой `server.py` и замени:
```python
BOT_TOKEN     = "YOUR_BOT_TOKEN"          # токен от @BotFather
ADMIN_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"   # твой Telegram ID (узнать через @userinfobot)
SECRET_KEY    = "windowclient-secret-key" # секретный ключ (должен совпадать с клиентом)
```

### 3. Настройка клиента (HwidManager.java)
```java
public static final String SERVER_URL = "http://YOUR_VPS_IP:5000";
```
И убедись что `SECRET_KEY` совпадает.

### 4. Запуск
```bash
python server.py
```

---

## Как работает

1. Пользователь запускает клиент
2. Клиент генерирует HWID (SHA-256 от MAC + имя ПК + процессор)
3. Клиент отправляет POST `/auth` с HWID, ником, версией
4. Сервер сохраняет в `users.json` и отправляет уведомление в Telegram
5. Ты видишь сообщение с кнопками управления
6. Клиент получает статус и действует соответственно

## Статусы подписки

| Статус    | Описание                          | Клиент работает? |
|-----------|-----------------------------------|-----------------|
| `active`  | Подписка активна                  | ✅ Да           |
| `frozen`  | Заморожена (временно)             | ❌ Нет          |
| `banned`  | Заблокирована навсегда            | ❌ Нет          |
| `unknown` | Новый пользователь (не в базе)    | ✅ Да (пока)    |

## Команды Telegram бота

- `/start` — главное меню
- `/users` — список всех пользователей
- `/stats` — статистика (всего/активных/заморожено/заблокировано)
- `/hwid XXXX-XXXX-XXXX-XXXX` — информация о конкретном пользователе

## Кнопки в уведомлении

- ❄️ **Заморозить** — временно отключить доступ
- ✅ **Разморозить** — восстановить доступ
- 🚫 **Заблокировать** — навсегда заблокировать
- ✅ **Разблокировать** — снять блокировку
- 🔄 **Обновить** — обновить информацию в сообщении

## Деплой на VPS (Ubuntu)

```bash
# Установка
sudo apt update && sudo apt install python3-pip -y
pip3 install -r requirements.txt

# Запуск как сервис (systemd)
sudo nano /etc/systemd/system/hwid-server.service
```

```ini
[Unit]
Description=WindowClient HWID Server
After=network.target

[Service]
User=root
WorkingDirectory=/root/hwid-server
ExecStart=/usr/bin/python3 server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable hwid-server
sudo systemctl start hwid-server
```
