# Сводка отчётов

Сотрудники заполняют [Яндекс Форму](https://forms.yandex.ru/u/6ac545514936394846dec049). Бесплатный воркер на Cloudflare принимает ответ, считает ЧКД и в 18:00 по Москве отправляет сводку в `@Sberteam_reports_bot`.

В форме сотрудник пишет исходное число. В сводке:

- **ЧКД Благо** = число × 0,8 / 1,2
- **ЧКД СберЗдоровье** = число × 0,65

Отдельный VPS не нужен. Яндекс Формы умеют слать запросы только по IPv6, у Cloudflare он есть.

## 1. Создать воркер

1. Откройте [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) и зарегистрируйтесь.
2. Слева выберите **Workers & Pages** → **Create** → **Create Worker**.
3. Имя: `sberteam-reports`. Нажмите **Deploy**, затем **Edit code**.
4. Удалите шаблон и вставьте содержимое файла [`cloudflare/worker.js`](cloudflare/worker.js). Нажмите **Deploy**.

## 2. Хранилище и секреты

1. В разделе **Workers** откройте **KV** → **Create a namespace**. Имя: `REPORTS`.
2. Вернитесь в воркер `sberteam-reports` → **Settings** → **Bindings** → **Add** → **KV Namespace**. Variable name: `REPORTS`, namespace: созданный. Save.
3. Там же **Variables and Secrets**:

| Имя | Тип | Значение |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Secret | токен `@Sberteam_reports_bot` |
| `FORMS_WEBHOOK_SECRET` | Secret | любая длинная случайная строка |
| `EMPLOYEES` | Text | десять фамилий через запятую, как в форме |
| `TELEGRAM_CHAT_ID` | Text | можно пустым |

4. **Triggers** → **Cron Triggers** → Add: `0 15 * * *` (это 18:00 по Москве).

Скопируйте адрес воркера вида `https://sberteam-reports.<аккаунт>.workers.dev`.

## 3. Подключить Telegram и форму

Подставить секрет и адрес:

```bash
curl "https://sberteam-reports.<аккаунт>.workers.dev/setup-telegram?secret=СЕКРЕТ"
curl "https://sberteam-reports.<аккаунт>.workers.dev/health"
```

Второе должно вернуть `{"status":"ok"}`.

В форме **Интеграции → API → Запрос заданным методом**:

- Адрес: `https://sberteam-reports.<аккаунт>.workers.dev/webhook/forms`
- Метод: `POST`
- Заголовок `Content-Type`: `application/json`
- Заголовок `X-Webhook-Secret`: тот же секрет
- Тело запроса. В каждое значение вставьте переменную **Ответ на вопрос**:

```json
{
  "employee": "",
  "report_date": "",
  "meetings_ab": 0,
  "stars": 0,
  "passives": 0,
  "pl_credit": 0,
  "issues": 0,
  "leasing": 0,
  "salary": 0,
  "te": 0,
  "knk": 0,
  "chkd_blago": 0,
  "chkd_sberhealth": 0,
  "chkd_accreds": 0
}
```

Руководитель пишет боту `/start`. Затем отправьте тестовую анкету и в форме откройте **Выполненные интеграции**: нужен код 200.

## Команды руководителя

- `/start` — привязать чат
- `/today` — сводка за сегодня
- `/missing` — кто не сдал
- `/date 06.10` — сводка за дату

## Локальные тесты

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest
node --test tests/test_worker_logic.mjs
```

Docker с `docker compose up --build` остаётся запасным вариантом, если появится своя ВМ с IPv6.
