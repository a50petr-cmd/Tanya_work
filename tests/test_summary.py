from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.summary import build_supplement, build_summary, format_metric_line


def test_calculated_lines_use_formulas() -> None:
    assert format_metric_line("chkd_blago", 10) == "ЧКД Благо: 6,67 (введено 10)"
    assert format_metric_line("chkd_sberhealth", 10) == "ЧКД СберЗдоровье: 6,50 (введено 10)"
    assert format_metric_line("meetings_ab", 4) == "Встречи AB: 4"


def test_summary_lists_missing() -> None:
    rows = [
        {
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
    ]
    text = build_summary(date(2026, 10, 6), rows, ["Иванов", "Петрова"], 10)
    assert "Сводка за 06.10.2026" in text
    assert "Сдали 1 из 10" in text
    assert "Не сдали: Иванов, Петрова" in text
    assert "ЧКД Благо: 6,67 (введено 10)" in text


def test_supplement_mentions_time() -> None:
    row = {
        "employee": "Соколова Анна",
        "report_date": "2026-10-06",
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
        "chkd_accreds": 0,
    }
    tz = ZoneInfo("Europe/Moscow")
    text = build_supplement(row, datetime(2026, 10, 6, 18, 40, tzinfo=tz), tz)
    assert "18:40" in text
    assert "Дополнение к сводке" in text
