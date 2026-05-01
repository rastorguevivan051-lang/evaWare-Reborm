# Установка HWID системы (без VPS, бесплатно)

## Шаг 1 — Google Apps Script

1. Открой https://script.google.com
2. Нажми **"Новый проект"**
3. Удали весь код в редакторе
4. Скопируй содержимое файла `google_apps_script.js` и вставь
5. Нажми **"Сохранить"** (Ctrl+S)

## Шаг 2 — Создать Google Таблицу

1. Открой https://sheets.google.com
2. Создай новую таблицу с названием **"WindowClient Users"**
3. Вернись в Apps Script
4. Нажми **"Ресурсы"** → **"Сервисы Google"** → найди **"Google Sheets API"** → включи

## Шаг 3 — Деплой

1. В Apps Script нажми **"Развернуть"** → **"Новое развертывание"**
2. Тип: **"Веб-приложение"**
3. Описание: любое
4. Выполнять от имени: **"Я (твой аккаунт)"**
5. Доступ: **"Все"**
6. Нажми **"Развернуть"**
7. Скопируй **URL веб-приложения** — он выглядит так:
   ```
   https://script.google.com/macros/s/AKfycb.../exec
   ```

## Шаг 4 — Вставить URL в клиент

Открой `src/eva/ware/auth/HwidManager.java` и замени:
```java
public static final String SCRIPT_URL =
    "https://script.google.com/macros/s/ТВОЙ_ID/exec";
```

## Шаг 5 — Настроить Webhook для кнопок

1. В Apps Script найди функцию `setWebhook()`
2. Выбери её в выпадающем списке функций (вверху редактора)
3. Нажми **▶ Запустить**
4. Разреши доступ если попросит
5. В логах должно появиться: `{"ok":true,...}`

Теперь кнопки ACTIVE / FROZEN / BANNED / UNLOCK будут работать!

## Что получишь в Telegram при каждом запуске клиента:

```
🚀 Запуск клиента

🔑 HWID: A1B2C3D4-E5F6G7H8-...
👾 Ник MC: Player123
🖥 Имя ПК: DESKTOP-ABC123
👤 Пользователь ОС: user
📦 Версия: 1.7
🕐 Время: 25.04.2026 15:30:00
📊 Запусков: 1
📋 Статус: ❓ Новый пользователь

🔧 Железо:
💻 ОС: Windows 10 Pro
🔲 МП: B450M DS3H
⚙️ CPU: AMD Ryzen 5 3600
🎮 GPU: NVIDIA GeForce RTX 3060
🧠 RAM: 16 GB
💾 Диск: 512 GB

[✅ ACTIVE] [❄️ FROZEN]
[🚫 BANNED] [🔓 UNLOCK]
[🔄 Обновить]
```

## Команды бота

- `/start` — главное меню
- `/stats` — статистика
- `/users` — список пользователей
- `/find ник` — найти по нику
- `/hwid XXXX-XXXX-XXXX-XXXX` — найти по HWID
