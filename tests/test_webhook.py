from datetime import date

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.parser import normalize_name


def _settings(tmp_path, **overrides) -> Settings:
    values = dict(
        telegram_bot_token="",
        telegram_chat_id="100",
        forms_webhook_secret="secret",
        form_page_token="",
        employees=("Иванов", "Соколова Анна"),
        summary_hour=18,
        summary_minute=0,
        timezone="Europe/Moscow",
        database_path=str(tmp_path / "reports.db"),
        host="0.0.0.0",
        port=8080,
    )
    values.update(overrides)
    return Settings(**values)


PAYLOAD = {
    "employee": "Соколова Анна",
    "report_date": "2026-10-06",
    "meetings_ab": 4,
    "stars": 1,
    "passives": 0,
    "pl_credit": 1,
    "issues": 0,
    "leasing": 1,
    "salary": 0,
    "te": 0,
    "knk": 2,
    "chkd_blago": 10,
    "chkd_sberhealth": 10,
    "chkd_accreds": 0,
}


def test_health(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path), background=False))
    assert client.get("/health").json() == {"status": "ok"}


def test_rejects_bad_secret(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path), background=False))
    response = client.post("/webhook/forms", json=PAYLOAD, headers={"X-Webhook-Secret": "nope"})
    assert response.status_code == 401


def test_stores_report(tmp_path) -> None:
    app = create_app(_settings(tmp_path), background=False)
    client = TestClient(app)
    response = client.post("/webhook/forms", json=PAYLOAD, headers={"X-Webhook-Secret": "secret"})
    assert response.status_code == 200
    rows = app.state.store.reports_for(date(2026, 10, 6))
    assert len(rows) == 1
    assert rows[0]["employee_key"] == normalize_name("Соколова Анна")
    assert rows[0]["chkd_blago"] == 10
    missing = app.state.store.missing_for(date(2026, 10, 6), app.state.settings.employees)
    assert missing == ["Иванов"]
