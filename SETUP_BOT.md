# Запуск Python бота

## Установка (один раз)

```
pip install flask requests pytelegrambotapi
```

## Запуск ngrok (каждый раз)

1. Скачай ngrok: https://ngrok.com/download
2. Распакуй рядом с bot.py
3. Запусти:
```
ngrok http 5000
```
4. Скопируй HTTPS URL (типа `https://xxxx.ngrok-free.app`)
5. Вставь в `bot.py` → `NGROK_URL`
6. Вставь в `HwidManager.java` → `SCRIPT_URL` (добавь `/auth` в конце)

## Запуск бота

```
python bot.py
```

Бот работает пока открыто окно. VPN нужен только при запуске.

## Команды в Telegram

- `/start` — главное меню с кнопками
- `/stats` — статистика
- `/find имя` — найти пользователя

## Кнопки

- ✅ ACTIVE — активировать подписку
- ❄️ FROZEN — заморозить
- 🚫 BANNED — заблокировать (клиент не запустится)
- 🔓 UNLOCK — разблокировать
- 🔄 Обновить — обновить данные
