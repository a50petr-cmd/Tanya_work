const METRIC_FIELDS = [
  "meetings_ab",
  "stars",
  "passives",
  "pl_credit",
  "issues",
  "leasing",
  "salary",
  "te",
  "knk",
  "chkd_blago",
  "chkd_sberhealth",
  "chkd_accreds",
];

const METRIC_LABELS = {
  meetings_ab: "Встречи AB",
  stars: "Звезды",
  passives: "Пассивы",
  pl_credit: "PL по кредитованию",
  issues: "Выдачи",
  leasing: "Лизинг",
  salary: "ЗП",
  te: "ТЭ",
  knk: "КНК",
  chkd_blago: "ЧКД Благо",
  chkd_sberhealth: "ЧКД СберЗдоровье",
  chkd_accreds: "ЧКД Аккреды",
};

const ALIASES = {
  employee: ["сотрудник", "employee", "фио"],
  report_date: ["дата отчета", "дата отчёта", "report_date", "дата"],
  meetings_ab: ["встречи ab", "встречи аб", "встречиab", "meetings_ab"],
  stars: ["звезды", "stars"],
  passives: ["пассивы", "passives"],
  pl_credit: ["pl по кредитованию", "pl по кредиту", "pl_credit"],
  issues: ["выдачи", "issues"],
  leasing: ["лизинг", "leasing"],
  salary: ["зп", "salary"],
  te: ["тэ", "te"],
  knk: ["кнк", "knk"],
  chkd_blago: ["чкд благо", "chkd_blago"],
  chkd_sberhealth: ["чкд сберздоровье", "чкд сбер здоровье", "chkd_sberhealth"],
  chkd_accreds: ["чкд аккреды", "chkd_accreds"],
};

const LOOKUP = {};
for (const [field, names] of Object.entries(ALIASES)) {
  for (const name of names) {
    LOOKUP[normalizeLabel(name)] = field;
  }
}

export function money(value) {
  return Math.round(Number(value) * 100 + Number.EPSILON) / 100;
}

export function chkdBlago(raw) {
  return money((Number(raw) * 0.8) / 1.2);
}

export function chkdSberhealth(raw) {
  return money(Number(raw) * 0.65);
}

export function normalizeName(value) {
  return String(value).toLowerCase().replaceAll("ё", "е").split(/\s+/).filter(Boolean).join(" ");
}

export function normalizeLabel(value) {
  return String(value)
    .toLowerCase()
    .replaceAll("ё", "е")
    .replace(/[^0-9a-zа-я]+/gi, " ")
    .trim();
}

function unwrapValue(value) {
  if (value && typeof value === "object") {
    if (Array.isArray(value)) {
      return value.length ? unwrapValue(value[0]) : null;
    }
    if ("value" in value) return unwrapValue(value.value);
    if ("start" in value) return unwrapValue(value.start);
    if ("text" in value) return unwrapValue(value.text);
  }
  return value;
}

function questionLabel(item, fallback) {
  const question = item?.question && typeof item.question === "object" ? item.question : {};
  const options = question.options && typeof question.options === "object" ? question.options : {};
  for (const candidate of [
    item.label,
    item.text,
    item.title,
    question.label,
    question.text,
    question.title,
    options.label,
    options.title,
    question.slug,
    fallback,
  ]) {
    if (typeof candidate === "string" && candidate.trim()) return candidate;
  }
  return fallback;
}

export function extractPairs(payload) {
  const pairs = {};
  const data = payload.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    for (const [key, item] of Object.entries(data)) {
      if (item && typeof item === "object") {
        pairs[questionLabel(item, key)] = unwrapValue(item);
      } else {
        pairs[key] = item;
      }
    }
  } else if (Array.isArray(data)) {
    for (const item of data) {
      if (!item || typeof item !== "object") continue;
      const label = questionLabel(item, "");
      if (label) pairs[label] = unwrapValue(item.answer ?? item.value);
    }
  }
  if (Array.isArray(payload.answers)) {
    for (const item of payload.answers) {
      if (!item || typeof item !== "object") continue;
      const label = questionLabel(item, "");
      if (label) pairs[label] = unwrapValue(item.answer ?? item.value);
    }
  }
  const skip = new Set(["id", "uid", "survey", "created", "cloud_uid", "data", "answers"]);
  for (const [key, value] of Object.entries(payload)) {
    if (!skip.has(key)) pairs[key] = unwrapValue(value);
  }
  return pairs;
}

function parseIntValue(value) {
  if (value === null || value === undefined || value === "") return 0;
  if (typeof value === "boolean") throw new Error("invalid integer");
  if (typeof value === "number") return Math.trunc(value);
  const text = String(value).trim().replaceAll(" ", "").replace(",", ".");
  if (!text) return 0;
  const number = Number(text);
  if (!Number.isFinite(number) || !Number.isInteger(number)) {
    throw new Error(`expected integer, got ${value}`);
  }
  return number;
}

export function parseDateValue(value, todayIso) {
  if (value === null || value === undefined || value === "") return todayIso;
  const text = String(value).trim();
  if (!text) return todayIso;
  const datePart = text.includes("T") ? text.split("T", 1)[0] : text;
  const iso = datePart.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const ru = datePart.match(/^(\d{2})\.(\d{2})\.(\d{2,4})$/);
  if (ru) {
    const year = ru[3].length === 2 ? `20${ru[3]}` : ru[3];
    return `${year}-${ru[2]}-${ru[1]}`;
  }
  throw new Error(`cannot parse date ${value}`);
}

export function parseReport(payload, todayIso) {
  const mapped = {};
  for (const [label, value] of Object.entries(extractPairs(payload))) {
    const field = LOOKUP[normalizeLabel(label)];
    if (field) mapped[field] = value;
  }
  const employee = String(mapped.employee || "").trim();
  if (!employee) throw new Error("не указан сотрудник");
  const metrics = {};
  for (const field of METRIC_FIELDS) {
    metrics[field] = parseIntValue(mapped[field]);
  }
  return {
    employee,
    employee_key: normalizeName(employee),
    report_date: parseDateValue(mapped.report_date, todayIso),
    metrics,
    form_answer_id: payload.id == null || payload.id === "" ? null : String(payload.id),
  };
}

export function moscowParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Moscow",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type).value;
  return {
    year: get("year"),
    month: get("month"),
    day: get("day"),
    hour: Number(get("hour")),
    minute: Number(get("minute")),
  };
}

export function moscowDateIso(date = new Date()) {
  const parts = moscowParts(date);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function formatRuDate(iso) {
  const [year, month, day] = iso.split("-");
  return `${day}.${month}.${year}`;
}

export function formatRuNumber(value) {
  const text = value.toFixed(2);
  if (text.endsWith(".00")) return text.slice(0, -3);
  return text.replace(".", ",");
}

export function formatMetricLine(field, raw) {
  const label = METRIC_LABELS[field];
  if (field === "chkd_blago") return `${label}: ${formatRuNumber(chkdBlago(raw))} (введено ${raw})`;
  if (field === "chkd_sberhealth") {
    return `${label}: ${formatRuNumber(chkdSberhealth(raw))} (введено ${raw})`;
  }
  return `${label}: ${raw}`;
}

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

export function formatReportBlock(row, index) {
  const lines = [`${index}. ${escapeHtml(row.employee)}, ${formatRuDate(row.report_date)}`];
  for (const field of METRIC_FIELDS) {
    lines.push(formatMetricLine(field, Number(row[field])));
  }
  return lines.join("\n");
}

export function splitEmployees(raw) {
  return String(raw || "")
    .split(",")
    .map((part) => part.trim().replace(/\s+/g, " "))
    .filter(Boolean);
}

export function missingEmployees(rows, employees) {
  const submitted = new Set(rows.map((row) => row.employee_key || normalizeName(row.employee)));
  return employees.filter((name) => !submitted.has(normalizeName(name)));
}

export function buildSummary(reportDate, rows, missing, expectedCount) {
  const header = [`<b>Сводка за ${formatRuDate(reportDate)}</b>`];
  header.push(expectedCount ? `Сдали ${rows.length} из ${expectedCount}` : `Сдали ${rows.length}`);
  if (missing.length) header.push("Не сдали: " + missing.map(escapeHtml).join(", "));
  const blocks = rows.map((row, index) => formatReportBlock(row, index + 1));
  if (!blocks.length) blocks.push("Отчётов пока нет.");
  return `${header.join("\n")}\n\n${blocks.join("\n\n")}`;
}

export function buildSupplement(row, submittedAt) {
  const parts = moscowParts(submittedAt);
  const hh = String(parts.hour).padStart(2, "0");
  const mm = String(parts.minute).padStart(2, "0");
  return (
    `<b>Дополнение к сводке за ${formatRuDate(row.report_date)}</b>\n` +
    `${escapeHtml(row.employee)} сдал отчёт в ${hh}:${mm}\n\n` +
    formatReportBlock(row, 1)
  );
}

export function parseCommandDate(raw, todayIso) {
  const text = String(raw).trim();
  if (/^\d{2}\.\d{2}$/.test(text)) {
    return parseDateValue(`${text}.${todayIso.slice(0, 4)}`, todayIso);
  }
  return parseDateValue(text, todayIso);
}

export function afterDeadline(reportDate, submittedAt, summaryHour, summaryMinute, sentDate) {
  const parts = moscowParts(submittedAt);
  const today = `${parts.year}-${parts.month}-${parts.day}`;
  const reached =
    parts.hour > summaryHour || (parts.hour === summaryHour && parts.minute >= summaryMinute);
  return reportDate === today && (reached || sentDate === reportDate);
}

function splitMessage(text) {
  if (text.length <= 4000) return [text];
  const chunks = [];
  let current = [];
  let size = 0;
  for (const block of text.split("\n\n")) {
    const extra = block.length + (current.length ? 2 : 0);
    if (current.length && size + extra > 4000) {
      chunks.push(current.join("\n\n"));
      current = [block];
      size = block.length;
    } else {
      current.push(block);
      size += extra;
    }
  }
  if (current.length) chunks.push(current.join("\n\n"));
  return chunks;
}

async function telegramCall(token, method, payload) {
  const clean = String(token || "").trim();
  let response;
  try {
    response = await fetch(`https://api.telegram.org/bot${clean}/${method}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
  } catch (error) {
    throw new Error(`Telegram ${method} network: ${String(error)}`);
  }
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    throw new Error(`Telegram ${method} HTTP ${response.status}: ${text.slice(0, 300)}`);
  }
  if (!body.ok) throw new Error(`Telegram ${method} failed: ${JSON.stringify(body)}`);
  return body;
}

const BOT_COMMANDS = [
  { command: "start", description: "Меню и привязка чата" },
  { command: "today", description: "Сводка за сегодня" },
  { command: "missing", description: "Кто не сдал" },
  { command: "date", description: "Сводка за дату: /date 06.10" },
];

const MENU_KEYBOARD = {
  keyboard: [
    [{ text: "Сегодня" }, { text: "Не сдали" }],
    [{ text: "За дату" }, { text: "Помощь" }],
  ],
  resize_keyboard: true,
  is_persistent: true,
};

const TEXT_ALIASES = {
  сегодня: "/today",
  "не сдали": "/missing",
  "за дату": "/date",
  помощь: "/start",
};

export function normalizeIncomingText(text) {
  const alias = TEXT_ALIASES[String(text).trim().toLowerCase()];
  return alias || text;
}

async function setupBotMenu(env) {
  await telegramCall(env.TELEGRAM_BOT_TOKEN, "setMyCommands", { commands: BOT_COMMANDS });
  await telegramCall(env.TELEGRAM_BOT_TOKEN, "setChatMenuButton", { menu_button: { type: "commands" } });
}

async function sendTelegram(env, chatId, text, extra = {}) {
  if (!env.TELEGRAM_BOT_TOKEN || !chatId) return;
  const chunks = splitMessage(text);
  for (const [index, chunk] of chunks.entries()) {
    const payload = {
      chat_id: chatId,
      text: chunk,
      parse_mode: "HTML",
      disable_web_page_preview: true,
      ...extra,
    };
    if (index < chunks.length - 1) delete payload.reply_markup;
    await telegramCall(env.TELEGRAM_BOT_TOKEN, "sendMessage", payload);
  }
}

function rowFromReport(report, submittedAtIso) {
  return {
    employee: report.employee,
    employee_key: report.employee_key,
    report_date: report.report_date,
    ...report.metrics,
    submitted_at: submittedAtIso,
    form_answer_id: report.form_answer_id,
  };
}

async function saveReport(env, report, submittedAtIso) {
  const row = rowFromReport(report, submittedAtIso);
  await env.REPORTS.put(`report:${report.report_date}:${report.employee_key}`, JSON.stringify(row));
  return row;
}

async function reportsFor(env, reportDate) {
  const listed = await env.REPORTS.list({ prefix: `report:${reportDate}:` });
  const rows = [];
  for (const key of listed.keys) {
    const raw = await env.REPORTS.get(key.name);
    if (raw) rows.push(JSON.parse(raw));
  }
  rows.sort((a, b) => a.employee.localeCompare(b.employee, "ru"));
  return rows;
}

async function managerChatId(env) {
  return (await env.REPORTS.get("settings:telegram_chat_id")) || env.TELEGRAM_CHAT_ID || "";
}

async function summaryFor(env, reportDate) {
  const rows = await reportsFor(env, reportDate);
  const employees = splitEmployees(env.EMPLOYEES);
  return buildSummary(reportDate, rows, missingEmployees(rows, employees), employees.length);
}

async function handleCommand(env, chatId, text) {
  const allowed = env.TELEGRAM_CHAT_ID;
  text = normalizeIncomingText(text);
  if (text.startsWith("/start")) {
    if (allowed && chatId !== allowed) return "Нет доступа.";
    await env.REPORTS.put("settings:telegram_chat_id", chatId);
    try {
      await setupBotMenu(env);
    } catch (error) {
      console.error("setup bot menu failed", error);
    }
    return (
      "Бот сводки отчётов. Команды в меню слева и на кнопках внизу.\n" +
      "/today — сводка за сегодня\n" +
      "/missing — кто не сдал\n" +
      "/date 06.10 — сводка за дату"
    );
  }
  if (allowed && chatId !== allowed) return "Нет доступа.";
  const [commandRaw, ...rest] = text.split(" ");
  const command = commandRaw.split("@", 1)[0].toLowerCase();
  const argument = rest.join(" ").trim();
  const today = moscowDateIso();
  if (command === "/today") return summaryFor(env, today);
  if (command === "/missing") {
    const employees = splitEmployees(env.EMPLOYEES);
    if (!employees.length) return "Список сотрудников не задан. Заполните EMPLOYEES.";
    const rows = await reportsFor(env, today);
    const missing = missingEmployees(rows, employees);
    if (!missing.length) return `За ${formatRuDate(today)} сдали все.`;
    return "Не сдали: " + missing.join(", ");
  }
  if (command === "/date") {
    if (!argument) return "Укажите дату, например /date 06.10";
    try {
      return summaryFor(env, parseCommandDate(argument, today));
    } catch {
      return "Не понял дату. Пример: /date 06.10 или /date 06.10.2026";
    }
  }
  return "Неизвестная команда. Доступны /today, /missing, /date.";
}

async function handleForms(request, env) {
  const secret = env.FORMS_WEBHOOK_SECRET;
  if (secret && request.headers.get("x-webhook-secret") !== secret) {
    return Response.json({ detail: "invalid secret" }, { status: 401 });
  }
  let payload;
  try {
    payload = await request.json();
  } catch {
    return Response.json({ detail: "invalid json" }, { status: 400 });
  }
  if (!payload || typeof payload !== "object") {
    return Response.json({ detail: "json object expected" }, { status: 400 });
  }
  let report;
  try {
    report = parseReport(payload, moscowDateIso());
  } catch (error) {
    return Response.json({ detail: String(error.message || error) }, { status: 400 });
  }
  const submittedAt = new Date();
  const row = await saveReport(env, report, submittedAt.toISOString());
  const sentDate = await env.REPORTS.get("settings:summary_sent_date");
  if (afterDeadline(report.report_date, submittedAt, 18, 0, sentDate)) {
    const chatId = await managerChatId(env);
    try {
      await sendTelegram(env, chatId, buildSupplement(row, submittedAt));
    } catch (error) {
      console.error("late telegram send failed", error);
    }
  }
  return Response.json({ ok: true, employee: report.employee, date: report.report_date });
}

async function handleTelegram(request, env) {
  const update = await request.json();
  const message = update.message || update.edited_message || {};
  const text = String(message.text || "").trim();
  const chatId = String(message.chat?.id || "");
  if (!text || !chatId) return Response.json({ ok: true });
  const reply = await handleCommand(env, chatId, text);
  if (reply) {
    const showMenu = normalizeIncomingText(text).startsWith("/start");
    await sendTelegram(env, chatId, reply, showMenu ? { reply_markup: MENU_KEYBOARD } : {});
  }
  return Response.json({ ok: true });
}

async function sendDailySummary(env) {
  const today = moscowDateIso();
  const chatId = await managerChatId(env);
  await sendTelegram(env, chatId, await summaryFor(env, today));
  await env.REPORTS.put("settings:summary_sent_date", today);
}

async function setupTelegram(request, env) {
  const url = new URL(request.url);
  const secret = env.FORMS_WEBHOOK_SECRET;
  if (secret && url.searchParams.get("secret") !== secret) {
    return Response.json({ detail: "invalid secret" }, { status: 401 });
  }
  if (!env.TELEGRAM_BOT_TOKEN) {
    return Response.json({ detail: "TELEGRAM_BOT_TOKEN is empty" }, { status: 400 });
  }
  try {
    const me = await telegramCall(env.TELEGRAM_BOT_TOKEN, "getMe", {});
    const webhookUrl = `${url.origin}/webhook/telegram`;
    const body = await telegramCall(env.TELEGRAM_BOT_TOKEN, "setWebhook", {
      url: webhookUrl,
      allowed_updates: ["message"],
    });
    await setupBotMenu(env);
    return Response.json({
      ok: true,
      bot: me.result?.username || null,
      webhook: webhookUrl,
      telegram: body.result,
      commands: BOT_COMMANDS,
    });
  } catch (error) {
    return Response.json({ ok: false, detail: String(error.message || error) }, { status: 502 });
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ status: "ok" });
    }
    if (request.method === "GET" && url.pathname === "/setup-telegram") {
      return setupTelegram(request, env);
    }
    if (request.method === "POST" && url.pathname === "/webhook/forms") {
      return handleForms(request, env);
    }
    if (request.method === "POST" && url.pathname === "/webhook/telegram") {
      return handleTelegram(request, env);
    }
    return new Response("Not found", { status: 404 });
  },
  async scheduled(_event, env) {
    await sendDailySummary(env);
  },
};
