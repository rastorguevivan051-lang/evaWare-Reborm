/**
 * WindowClient HWID System — Google Apps Script
 * Работает без VPN, без сервера, 24/7
 *
 * УСТАНОВКА:
 * 1. Вставь код в Apps Script
 * 2. Сохрани (Ctrl+S)
 * 3. Задеплой как веб-приложение (доступ: Все)
 * 4. Запусти setupTrigger() ОДИН РАЗ — создаст таймер каждую минуту
 * 5. Вставь URL деплоя в HwidManager.java
 */

const BOT_TOKEN  = "8594044049:AAHRvLqwt_uVfM1TYAUTWvhsMsV0e4Ddflg";
const ADMIN_ID   = "6381036957";
const SHEET_NAME = "Users";

// ── Точка входа — запросы от клиента ─────────────────────────────────────────

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);

    // Запрос от Java клиента (есть поле hwid)
    if (body.hwid) {
      return handleClientAuth(body);
    }

    return ok();
  } catch (err) {
    Logger.log("doPost error: " + err);
    return json({ status: "error" });
  }
}

function doGet(e) {
  return ContentService.createTextOutput("WindowClient OK")
    .setMimeType(ContentService.MimeType.TEXT);
}

// ── Авторизация клиента ───────────────────────────────────────────────────────

function handleClientAuth(data) {
  const hwid       = data.hwid        || "unknown";
  const clientName = data.client_name || "unknown";
  const mcName     = data.username    || "unknown";
  const version    = data.version     || "?";
  const hardware   = data.hardware    || "нет данных";
  const pcName     = data.pc_name     || "?";
  const osUser     = data.os_user     || "?";

  const sheet = getSheet();
  const row   = findRowByHwid(sheet, hwid);
  const now   = new Date().toLocaleString("ru-RU", {timeZone: "Europe/Moscow"});

  let status   = "unknown";
  let launches = 1;
  let uid      = 0;

  if (row > 0) {
    uid      = sheet.getRange(row, 1).getValue();
    status   = sheet.getRange(row, 5).getValue() || "unknown";
    launches = (parseInt(sheet.getRange(row, 9).getValue()) || 0) + 1;
    sheet.getRange(row, 3).setValue(clientName);
    sheet.getRange(row, 4).setValue(mcName);
    sheet.getRange(row, 7).setValue(now);
    sheet.getRange(row, 8).setValue(hardware);
    sheet.getRange(row, 9).setValue(launches);
    sheet.getRange(row, 11).setValue(pcName);
    sheet.getRange(row, 12).setValue(osUser);
    sheet.getRange(row, 13).setValue(version);
  } else {
    uid = Math.max(1, sheet.getLastRow());
    sheet.appendRow([uid, hwid, clientName, mcName, "unknown",
                     now, now, hardware, 1, "", pcName, osUser, version]);
    status = "unknown";
  }

  // Отправляем уведомление в Telegram
  const user = { uid, hwid, clientName, mcName, version, hardware, pcName, osUser, status, launches, lastSeen: now };
  sendNotification(user);

  return json({ status: status, uid: uid });
}

// ── Polling Telegram (запускается триггером каждую минуту) ────────────────────

// Хранит offset в ScriptProperties чтобы не обрабатывать старые апдейты
function pollTelegram() {
  const props  = PropertiesService.getScriptProperties();
  const offset = parseInt(props.getProperty("tg_offset") || "0");

  try {
    const resp = UrlFetchApp.fetch(
      `https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=${offset}&timeout=0&limit=10`,
      { muteHttpExceptions: true }
    );
    const data = JSON.parse(resp.getContentText());
    if (!data.ok) return;

    for (const update of data.result) {
      props.setProperty("tg_offset", String(update.update_id + 1));

      if (update.callback_query) {
        handleCallback(update.callback_query);
      } else if (update.message) {
        handleMessage(update.message);
      }
    }
  } catch (err) {
    Logger.log("pollTelegram error: " + err);
  }
}

// ── Создать триггер (запусти ОДИН РАЗ вручную) ────────────────────────────────

function setupTrigger() {
  // Удаляем старые триггеры
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "pollTelegram") {
      ScriptApp.deleteTrigger(t);
    }
  });
  // Создаём новый — каждую минуту
  ScriptApp.newTrigger("pollTelegram")
    .timeBased()
    .everyMinutes(1)
    .create();
  Logger.log("Триггер создан! Бот будет проверять сообщения каждую минуту.");
}

// ── Обработка callback кнопок ─────────────────────────────────────────────────

function handleCallback(cb) {
  const queryId = cb.id;
  const chatId  = String(cb.message.chat.id);
  const msgId   = cb.message.message_id;
  const data    = cb.data || "";

  if (chatId !== ADMIN_ID) {
    answerCb(queryId, "⛔ Нет доступа");
    return;
  }

  const parts  = data.split(":");
  const action = parts[0];

  if (action === "refresh") {
    const hwid = parts[1];
    const sheet = getSheet();
    const row   = findRowByHwid(sheet, hwid);
    if (row > 0) {
      const u = getRowData(sheet, row);
      editMsg(chatId, msgId, u);
      answerCb(queryId, "🔄 Обновлено");
    }
    return;
  }

  if (action === "set") {
    const newStatus = parts[1];
    const hwid      = parts[2];
    const sheet     = getSheet();
    const row       = findRowByHwid(sheet, hwid);
    if (row > 0) {
      sheet.getRange(row, 5).setValue(newStatus);
      const u = getRowData(sheet, row);
      editMsg(chatId, msgId, u);
      const labels = {active:"✅ ACTIVE", frozen:"❄️ FROZEN", banned:"🚫 BANNED"};
      answerCb(queryId, labels[newStatus] || "✅ Обновлено");
    } else {
      answerCb(queryId, "Пользователь не найден");
    }
    return;
  }

  if (action === "list") {
    const page = parseInt(parts[1]) || 0;
    sendUserList(chatId, msgId, page, true);
    answerCb(queryId, "");
    return;
  }

  if (action === "user") {
    const hwid  = parts[1];
    const sheet = getSheet();
    const row   = findRowByHwid(sheet, hwid);
    if (row > 0) {
      const u  = getRowData(sheet, row);
      const kb = buildKeyboard(u.hwid);
      kb.inline_keyboard.push([{ text: "◀️ Назад к списку", callback_data: "list:0" }]);
      editMsgRaw(chatId, msgId, formatUser(u), kb);
    }
    answerCb(queryId, "");
    return;
  }

  if (action === "stats") {
    sendStats(chatId, msgId, true);
    answerCb(queryId, "");
    return;
  }

  answerCb(queryId, "");
}

// ── Обработка сообщений ───────────────────────────────────────────────────────

function handleMessage(msg) {
  const chatId = String(msg.chat.id);
  const text   = msg.text || "";
  if (chatId !== ADMIN_ID) return;

  if (text === "/start" || text === "/menu") {
    sendMsg(chatId,
      "👋 <b>WindowClient Admin Panel</b>\n\nВыберите действие:",
      { inline_keyboard: [
        [{ text: "👥 Список пользователей", callback_data: "list:0" }],
        [{ text: "📊 Статистика",           callback_data: "stats"  }]
      ]}
    );
  } else if (text === "/stats") {
    sendStats(chatId, null, false);
  } else if (text.startsWith("/find ")) {
    const name  = text.substring(6).trim().toLowerCase();
    const sheet = getSheet();
    const data  = sheet.getDataRange().getValues().slice(1);
    let found   = false;
    for (const row of data) {
      if (String(row[2]).toLowerCase() === name || String(row[3]).toLowerCase() === name) {
        const u = rowToUser(row);
        sendMsg(chatId, formatUser(u), buildKeyboard(u.hwid));
        found = true;
        break;
      }
    }
    if (!found) sendMsg(chatId, `❌ Пользователь <code>${name}</code> не найден`);
  }
}

// ── Список пользователей ──────────────────────────────────────────────────────

function sendUserList(chatId, msgId, page, edit) {
  const sheet    = getSheet();
  const allData  = sheet.getDataRange().getValues().slice(1);
  const perPage  = 8;
  const total    = allData.length;
  const start    = page * perPage;
  const end      = Math.min(start + perPage, total);
  const pageData = allData.slice(start, end);

  let text    = `👥 <b>Пользователи</b> (${total} всего, стр. ${page + 1}):\n\n`;
  const btns  = [];

  for (const row of pageData) {
    const u     = rowToUser(row);
    const emoji = {active:"✅",frozen:"❄️",banned:"🚫",unknown:"❓"}[u.status] || "❓";
    text += `${emoji} <b>UID ${u.uid}</b> — <code>${u.clientName}</code>\n`;
    btns.push([{ text: `${emoji} UID ${u.uid} — ${u.clientName}`, callback_data: `user:${u.hwid}` }]);
  }

  const nav = [];
  if (page > 0)    nav.push({ text: "◀️", callback_data: `list:${page - 1}` });
  if (end < total) nav.push({ text: "▶️", callback_data: `list:${page + 1}` });
  if (nav.length)  btns.push(nav);

  const kb = { inline_keyboard: btns };
  if (edit && msgId) {
    editMsgRaw(chatId, msgId, text, kb);
  } else {
    sendMsg(chatId, text, kb);
  }
}

function sendStats(chatId, msgId, edit) {
  const sheet = getSheet();
  const data  = sheet.getDataRange().getValues().slice(1);
  let active = 0, frozen = 0, banned = 0, unknown = 0;
  for (const row of data) {
    const s = row[4];
    if (s === "active") active++;
    else if (s === "frozen") frozen++;
    else if (s === "banned") banned++;
    else unknown++;
  }
  const text =
    `📊 <b>Статистика</b>\n\n` +
    `👥 Всего: <b>${data.length}</b>\n` +
    `✅ Active: <b>${active}</b>\n` +
    `❄️ Frozen: <b>${frozen}</b>\n` +
    `🚫 Banned: <b>${banned}</b>\n` +
    `❓ Unknown: <b>${unknown}</b>`;
  if (edit && msgId) editMsgRaw(chatId, msgId, text, null);
  else sendMsg(chatId, text);
}

// ── Уведомление при запуске клиента ──────────────────────────────────────────

function sendNotification(u) {
  const statusLabel = {active:"✅ Активна",frozen:"❄️ Заморожена",banned:"🚫 Заблокирована",unknown:"❓ Новый"}[u.status] || "❓";
  const text =
    `🚀 <b>Запуск клиента</b>\n\n` +
    `🆔 <b>UID:</b> <code>${u.uid}</code>\n` +
    `🔑 <b>HWID:</b> <code>${u.hwid}</code>\n` +
    `👤 <b>Имя:</b> <code>${u.clientName}</code>\n` +
    `👾 <b>Ник MC:</b> <code>${u.mcName}</code>\n` +
    `🖥 <b>Имя ПК:</b> <code>${u.pcName}</code>\n` +
    `👤 <b>ОС юзер:</b> <code>${u.osUser}</code>\n` +
    `📦 <b>Версия:</b> <code>${u.version}</code>\n` +
    `🕐 <b>Время:</b> <code>${u.lastSeen}</code>\n` +
    `📊 <b>Запусков:</b> <code>${u.launches}</code>\n` +
    `📋 <b>Статус:</b> ${statusLabel}\n\n` +
    `🔧 <b>Железо:</b>\n<code>${u.hardware}</code>`;
  sendMsg(ADMIN_ID, text, buildKeyboard(u.hwid));
}

// ── Клавиатура ────────────────────────────────────────────────────────────────

function buildKeyboard(hwid) {
  return {
    inline_keyboard: [
      [
        { text: "✅ ACTIVE", callback_data: `set:active:${hwid}` },
        { text: "❄️ FROZEN", callback_data: `set:frozen:${hwid}` },
      ],
      [
        { text: "🚫 BANNED", callback_data: `set:banned:${hwid}` },
        { text: "🔓 UNLOCK", callback_data: `set:active:${hwid}` },
      ],
      [{ text: "🔄 Обновить", callback_data: `refresh:${hwid}` }]
    ]
  };
}

// ── Вспомогательные ───────────────────────────────────────────────────────────

function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["UID","HWID","ClientName","MCUsername","Status",
                     "FirstSeen","LastSeen","Hardware","Launches",
                     "TGMsgID","PCName","OSUser","Version"]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function findRowByHwid(sheet, hwid) {
  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === hwid) return i + 1;
  }
  return -1;
}

function getRowData(sheet, row) {
  const r = sheet.getRange(row, 1, 1, 13).getValues()[0];
  return rowToUser(r);
}

function rowToUser(r) {
  return {
    uid: r[0], hwid: r[1], clientName: r[2], mcName: r[3],
    status: r[4], firstSeen: r[5], lastSeen: r[6],
    hardware: r[7], launches: r[8], tgMsgId: r[9],
    pcName: r[10], osUser: r[11], version: r[12]
  };
}

function formatUser(u) {
  const statusLabel = {active:"✅ Активна",frozen:"❄️ Заморожена",banned:"🚫 Заблокирована",unknown:"❓ Новый"}[u.status] || "❓";
  return (
    `🆔 <b>UID:</b> <code>${u.uid}</code>\n` +
    `🔑 <b>HWID:</b> <code>${u.hwid}</code>\n` +
    `👤 <b>Имя:</b> <code>${u.clientName}</code>\n` +
    `👾 <b>Ник MC:</b> <code>${u.mcName}</code>\n` +
    `🖥 <b>ПК:</b> <code>${u.pcName}</code>\n` +
    `👤 <b>ОС:</b> <code>${u.osUser}</code>\n` +
    `📦 <b>Версия:</b> <code>${u.version}</code>\n` +
    `📊 <b>Запусков:</b> <code>${u.launches}</code>\n` +
    `🕐 <b>Последний вход:</b> <code>${u.lastSeen}</code>\n` +
    `📋 <b>Статус:</b> ${statusLabel}\n\n` +
    `🔧 <b>Железо:</b>\n<code>${u.hardware}</code>`
  );
}

function editMsg(chatId, msgId, u) {
  editMsgRaw(chatId, msgId, formatUser(u), buildKeyboard(u.hwid));
}

function editMsgRaw(chatId, msgId, text, kb) {
  const payload = { chat_id: chatId, message_id: msgId, text: text, parse_mode: "HTML" };
  if (kb) payload.reply_markup = JSON.stringify(kb);
  fetch_("editMessageText", payload);
}

function sendMsg(chatId, text, kb) {
  const payload = { chat_id: chatId, text: text, parse_mode: "HTML" };
  if (kb) payload.reply_markup = JSON.stringify(kb);
  const resp = fetch_("sendMessage", payload);
  try { return JSON.parse(resp).result.message_id; } catch(e) { return null; }
}

function answerCb(id, text) {
  fetch_("answerCallbackQuery", { callback_query_id: id, text: text || "" });
}

function fetch_(method, payload) {
  try {
    const resp = UrlFetchApp.fetch(
      `https://api.telegram.org/bot${BOT_TOKEN}/${method}`,
      { method: "post", payload: JSON.stringify(payload),
        contentType: "application/json", muteHttpExceptions: true }
    );
    return resp.getContentText();
  } catch(e) {
    Logger.log("fetch_ error: " + e);
    return "{}";
  }
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function ok() {
  return ContentService.createTextOutput("ok")
    .setMimeType(ContentService.MimeType.TEXT);
}
