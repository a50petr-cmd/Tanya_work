from datetime import date

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.parser import normalize_name


def _settings(tmp_path, **overrides) -> Settings:
    values = dict(
        telegram_bot_token="",
        telegram_chat_id="",
        forms_webhook_secret="page-secret",
        form_page_token="",
        employees=("Соколова Анна",),
        summary_hour=18,
        summary_minute=0,
        timezone="Europe/Moscow",
        database_path=str(tmp_path / "reports.db"),
        host="0.0.0.0",
        port=8080,
    )
    values.update(overrides)
    return Settings(**values)


def test_report_form_requires_key(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path), background=False))
    assert client.get("/report").status_code == 403
    assert client.get("/report", params={"key": "page-secret"}).status_code == 200
    assert "Ежедневный отчёт" in client.get("/report", params={"key": "page-secret"}).text


def test_report_submit_stores_row(tmp_path) -> None:
    app = create_app(_settings(tmp_path), background=False)
    client = TestClient(app)
    response = client.post(
        "/report/submit",
        data={
            "access_key": "page-secret",
            "employee": "Соколова Анна",
            "report_date": "2026-10-07",
            "meetings_ab": "1",
            "stars": "0",
            "passives": "0",
            "pl_credit": "0",
            "issues": "0",
            "leasing": "0",
            "salary": "0",
            "te": "0",
            "knk": "0",
            "chkd_blago": "10",
            "chkd_sberhealth": "10",
            "chkd_accreds": "0",
        },
    )
    assert response.status_code == 200
    assert "сохранён" in response.text.lower()
    rows = app.state.store.reports_for(date(2026, 10, 7))
    assert len(rows) == 1
    assert rows[0]["employee_key"] == normalize_name("Соколова Анна")
