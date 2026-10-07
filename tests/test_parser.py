from datetime import date

import pytest

from app.parser import ParseError, parse_report


TODAY = date(2026, 10, 6)

NAMED_PAYLOAD = {
    "employee": "Соколова Анна",
    "report_date": "06.10.2026",
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


def test_parse_named_payload() -> None:
    report = parse_report(NAMED_PAYLOAD, today=TODAY)
    assert report.employee == "Соколова Анна"
    assert report.report_date == TODAY
    assert report.metrics["meetings_ab"] == 4
    assert report.metrics["chkd_blago"] == 10


def test_parse_yandex_data_with_labels() -> None:
    payload = {
        "id": 77,
        "data": {
            "answer_short_text_1": {
                "value": "Кузнецов Павел",
                "question": {"id": 1, "options": {"label": "Сотрудник"}},
            },
            "answer_date_2": {
                "value": "2026-10-06",
                "question": {"id": 2, "options": {"label": "Дата отчёта"}},
            },
            "answer_integer_3": {
                "value": 4,
                "question": {"id": 3, "options": {"label": "Встречи AB"}},
            },
            "answer_integer_4": {
                "value": 3,
                "question": {"id": 4, "options": {"label": "ЧКД Благо"}},
            },
        },
    }
    report = parse_report(payload, today=TODAY)
    assert report.employee == "Кузнецов Павел"
    assert report.report_date == TODAY
    assert report.metrics["meetings_ab"] == 4
    assert report.metrics["chkd_blago"] == 3
    assert report.form_answer_id == "77"


def test_missing_employee() -> None:
    with pytest.raises(ParseError):
        parse_report({"meetings_ab": 1}, today=TODAY)
