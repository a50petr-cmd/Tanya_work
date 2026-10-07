from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import Settings
from app.db import Store
from app.parser import ParseError, parse_report
from app.summary import build_summary, build_supplement, build_totals, format_ru_date
from app.telegram import TelegramBot, start_polling
from app.webform import (
    check_form_key,
    form_access_token,
    payload_from_form,
    render_report_page,
)

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, background: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Store(settings.database_path)
    stop = threading.Event()
    scheduler = BackgroundScheduler(timezone=settings.tz)

    def manager_chat_id() -> str:
        return store.get_setting("telegram_chat_id") or settings.telegram_chat_id

    def send_to_manager(text: str) -> None:
        chat_id = manager_chat_id()
        if not chat_id:
            log.warning("Manager chat id is not set")
            return
        bot.send(chat_id, text)

    def summary_for(report_date: date) -> str:
        rows = store.reports_for(report_date)
        missing = store.missing_for(report_date, settings.employees)
        return build_summary(report_date, rows, missing, len(settings.employees))

    def totals_for(report_date: date) -> str:
        rows = store.reports_for(report_date)
        missing = store.missing_for(report_date, settings.employees)
        return build_totals(report_date, rows, missing, len(settings.employees))

    def send_daily_summary() -> None:
        today = datetime.now(settings.tz).date()
        send_to_manager(totals_for(today))
        send_to_manager(summary_for(today))
        store.set_setting("summary_sent_date", today.isoformat())

    def after_deadline(report_date: date, submitted_at: datetime) -> bool:
        now = submitted_at.astimezone(settings.tz)
        deadline = now.replace(
            hour=settings.summary_hour,
            minute=settings.summary_minute,
            second=0,
            microsecond=0,
        )
        sent = store.get_setting("summary_sent_date") == report_date.isoformat()
        return report_date == now.date() and (now >= deadline or sent)

    def handle_command(chat_id: str, text: str) -> str | None:
        if text.startswith("/start"):
            if not settings.telegram_chat_id:
                store.set_setting("telegram_chat_id", chat_id)
            elif chat_id != settings.telegram_chat_id:
                return "Нет доступа."
            else:
                store.set_setting("telegram_chat_id", chat_id)
            return (
                "Бот сводки отчётов.\n"
                "/svod — сводный отчёт: суммы и кто не сдал\n"
                "/today — отчёты каждого сотрудника\n"
                "/missing — кто не сдал\n"
                "/date 06.10 — отчёты за дату"
            )
        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0].lower()
        if command == "/today":
            return summary_for(datetime.now(settings.tz).date())
        if command in {"/svod", "/summary", "/totals"}:
            raw = argument.strip()
            if not raw:
                return totals_for(datetime.now(settings.tz).date())
            try:
                report_date = _parse_command_date(raw, datetime.now(settings.tz).date())
            except ValueError:
                return "Не понял дату. Пример: /svod 06.10 или /svod 06.10.2026"
            return totals_for(report_date)
        if command == "/missing":
            today = datetime.now(settings.tz).date()
            missing = store.missing_for(today, settings.employees)
            if not settings.employees:
                return "Список сотрудников не задан. Заполните EMPLOYEES."
            if not missing:
                return f"За {format_ru_date(today)} сдали все."
            return "Не сдали: " + ", ".join(missing)
        if command == "/date":
            raw = argument.strip()
            if not raw:
                return "Укажите дату, например /date 06.10"
            try:
                report_date = _parse_command_date(raw, datetime.now(settings.tz).date())
            except ValueError:
                return "Не понял дату. Пример: /date 06.10 или /date 06.10.2026"
            return summary_for(report_date)
        return "Неизвестная команда. Доступны /svod, /today, /missing, /date."

    bot = TelegramBot(settings.telegram_bot_token, settings.telegram_chat_id, handle_command)

    app = FastAPI(title="Сводка отчётов", version="1.0.0")
    app.state.settings = settings
    app.state.store = store
    app.state.bot = bot

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def save_report_from_payload(payload: dict, *, delivery: str | None = None) -> dict:
        try:
            report = parse_report(payload, tz=settings.tz)
        except ParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        submitted_at = datetime.now(settings.tz)
        store.upsert_report(report, submitted_at)
        row = next(
            row
            for row in store.reports_for(report.report_date)
            if row["employee_key"] == report.employee_key
        )
        if after_deadline(report.report_date, submitted_at):
            try:
                send_to_manager(build_supplement(row, submitted_at, settings.tz))
            except Exception:
                log.exception("Failed to send late report to Telegram")
        return {
            "ok": True,
            "employee": report.employee,
            "date": report.report_date.isoformat(),
            "delivery": delivery,
        }

    @app.get("/report", response_class=HTMLResponse)
    def report_form(key: str | None = Query(default=None)) -> HTMLResponse:
        if not check_form_key(settings, key):
            raise HTTPException(status_code=403, detail="invalid or missing key")
        today = datetime.now(settings.tz).date()
        token = form_access_token(settings)
        html_page = render_report_page(
            employees=settings.employees,
            default_date=today,
            access_key=token,
        )
        return HTMLResponse(html_page)

    @app.post("/report/submit", response_class=HTMLResponse)
    async def report_submit(request: Request) -> HTMLResponse:
        form = await request.form()
        data = {k: str(v) for k, v in form.items()}
        if not check_form_key(settings, data.get("access_key")):
            raise HTTPException(status_code=403, detail="invalid or missing key")
        try:
            save_report_from_payload(payload_from_form(data))
        except HTTPException as exc:
            today = datetime.now(settings.tz).date()
            token = form_access_token(settings)
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            page = render_report_page(
                employees=settings.employees,
                default_date=today,
                access_key=token,
                error=detail,
            )
            return HTMLResponse(page, status_code=exc.status_code)
        today = datetime.now(settings.tz).date()
        token = form_access_token(settings)
        page = render_report_page(
            employees=settings.employees,
            default_date=today,
            access_key=token,
            success="Отчёт сохранён. Спасибо! Можно отправить ещё один или закрыть страницу.",
        )
        return HTMLResponse(page)

    @app.get("/")
    def root(key: str | None = Query(default=None)):
        if check_form_key(settings, key):
            return RedirectResponse(url=f"/report?key={key}" if key else "/report", status_code=302)
        return RedirectResponse(url="/health", status_code=302)

    @app.post("/webhook/forms")
    async def forms_webhook(
        request: Request,
        x_webhook_secret: str | None = Header(default=None),
        x_delivery_id: str | None = Header(default=None),
    ) -> JSONResponse:
        if settings.forms_webhook_secret:
            if x_webhook_secret != settings.forms_webhook_secret:
                raise HTTPException(status_code=401, detail="invalid secret")
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid json") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="json object expected")
        body = save_report_from_payload(payload, delivery=x_delivery_id)
        return JSONResponse(body)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if background:
            scheduler.add_job(
                send_daily_summary,
                CronTrigger(
                    hour=settings.summary_hour,
                    minute=settings.summary_minute,
                    timezone=settings.tz,
                ),
                id="daily_summary",
                replace_existing=True,
            )
            scheduler.start()
            if settings.telegram_bot_token:
                start_polling(bot, stop)
        yield
        stop.set()
        if scheduler.running:
            scheduler.shutdown(wait=False)

    app.router.lifespan_context = lifespan
    return app


def _parse_command_date(raw: str, today: date) -> date:
    from datetime import datetime as dt

    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return dt.strptime(raw, fmt).date()
        except ValueError:
            continue
    parsed = dt.strptime(raw, "%d.%m")
    return date(today.year, parsed.month, parsed.day)


app = create_app()
