from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from app.formulas import chkd_blago, chkd_sberhealth

METRIC_LABELS = (
    ("meetings_ab", "Встречи AB"),
    ("stars", "Звезды"),
    ("passives", "Пассивы"),
    ("pl_credit", "PL по кредитованию"),
    ("issues", "Выдачи"),
    ("leasing", "Лизинг"),
    ("salary", "ЗП"),
    ("te", "ТЭ"),
    ("knk", "КНК"),
    ("chkd_blago", "ЧКД Благо"),
    ("chkd_sberhealth", "ЧКД СберЗдоровье"),
    ("chkd_accreds", "ЧКД Аккреды"),
)

CALCULATED = {
    "chkd_blago": chkd_blago,
    "chkd_sberhealth": chkd_sberhealth,
}


def format_ru_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def format_ru_number(value: Any) -> str:
    text = f"{value:.2f}" if hasattr(value, "quantize") else f"{value:.2f}"
    if text.endswith(".00"):
        return text[:-3]
    return text.replace(".", ",")


def format_metric_line(field: str, raw: int) -> str:
    label = dict(METRIC_LABELS)[field]
    if field in CALCULATED:
        calculated = CALCULATED[field](raw)
        return f"{label}: {format_ru_number(calculated)} (введено {raw})"
    return f"{label}: {raw}"


def format_report_block(row: dict[str, Any], index: int) -> str:
    report_date = date.fromisoformat(row["report_date"])
    lines = [f"{index}. {escape(row['employee'])}, {format_ru_date(report_date)}"]
    for field, _label in METRIC_LABELS:
        lines.append(format_metric_line(field, int(row[field])))
    return "\n".join(lines)


def build_summary(
    report_date: date,
    rows: list[dict[str, Any]],
    missing: list[str],
    expected_count: int,
) -> str:
    header = [f"<b>Сводка за {format_ru_date(report_date)}</b>"]
    if expected_count:
        header.append(f"Сдали {len(rows)} из {expected_count}")
    else:
        header.append(f"Сдали {len(rows)}")
    if missing:
        header.append("Не сдали: " + ", ".join(escape(name) for name in missing))
    blocks = [format_report_block(row, index) for index, row in enumerate(rows, start=1)]
    if not blocks:
        blocks = ["Отчётов пока нет."]
    return "\n".join(header) + "\n\n" + "\n\n".join(blocks)


def build_supplement(row: dict[str, Any], submitted_at: datetime, tz: ZoneInfo) -> str:
    local = submitted_at.astimezone(tz)
    report_date = date.fromisoformat(row["report_date"])
    title = (
        f"<b>Дополнение к сводке за {format_ru_date(report_date)}</b>\n"
        f"{escape(row['employee'])} сдал отчёт в {local.strftime('%H:%M')}"
    )
    return title + "\n\n" + format_report_block(row, 1)


def sum_metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals = {field: 0 for field, _label in METRIC_LABELS}
    for row in rows:
        for field, _label in METRIC_LABELS:
            totals[field] += int(row[field] or 0)
    return totals


def build_totals(
    report_date: date,
    rows: list[dict[str, Any]],
    missing: list[str],
    expected_count: int,
) -> str:
    header = [f"<b>Сводный отчёт за {format_ru_date(report_date)}</b>"]
    if expected_count:
        header.append(f"Сдали {len(rows)} из {expected_count}")
    else:
        header.append(f"Сдали {len(rows)}")
    if missing:
        header.append("Не сдали: " + ", ".join(escape(name) for name in missing))
    elif expected_count and len(rows) >= expected_count:
        header.append("Не сдали: никого")
    if not rows:
        return "\n".join(header) + "\n\nОтчётов пока нет."
    totals = sum_metrics(rows)
    lines = ["<b>Итого</b>"]
    for field, _label in METRIC_LABELS:
        lines.append(format_metric_line(field, totals[field]))
    submitted = ", ".join(escape(row["employee"]) for row in rows)
    lines.extend(["", f"Сдали: {submitted}"])
    return "\n".join(header) + "\n\n" + "\n".join(lines)
