from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

METRIC_FIELDS = (
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
)

_ALIASES: dict[str, tuple[str, ...]] = {
    "employee": ("сотрудник", "employee", "фио"),
    "report_date": ("дата отчета", "дата отчёта", "report_date", "дата"),
    "meetings_ab": ("встречи ab", "встречи аб", "встречиab", "meetings_ab"),
    "stars": ("звезды", "stars"),
    "passives": ("пассивы", "passives"),
    "pl_credit": ("pl по кредитованию", "pl по кредиту", "pl_credit"),
    "issues": ("выдачи", "issues"),
    "leasing": ("лизинг", "leasing"),
    "salary": ("зп", "salary"),
    "te": ("тэ", "te"),
    "knk": ("кнк", "knk"),
    "chkd_blago": ("чкд благо", "chkd_blago"),
    "chkd_sberhealth": (
        "чкд сберздоровье",
        "чкд сбер здоровье",
        "chkd_sberhealth",
    ),
    "chkd_accreds": ("чкд аккреды", "chkd_accreds"),
}


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def _normalize_label(value: str) -> str:
    text = value.casefold().replace("ё", "е")
    out = []
    prev_space = False
    for char in text:
        if char.isalnum():
            out.append(char)
            prev_space = False
        elif not prev_space:
            out.append(" ")
            prev_space = True
    return "".join(out).strip()


_LOOKUP = {
    _normalize_label(alias): field
    for field, aliases in _ALIASES.items()
    for alias in aliases
}


def _unwrap_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "value" in value:
            return _unwrap_value(value["value"])
        if "start" in value:
            return _unwrap_value(value["start"])
        if "text" in value:
            return _unwrap_value(value["text"])
    if isinstance(value, list):
        return _unwrap_value(value[0]) if value else None
    return value


def _question_label(item: dict[str, Any], fallback: str) -> str:
    question = item.get("question") if isinstance(item.get("question"), dict) else {}
    options = question.get("options") if isinstance(question.get("options"), dict) else {}
    for candidate in (
        item.get("label"),
        item.get("text"),
        item.get("title"),
        question.get("label"),
        question.get("text"),
        question.get("title"),
        options.get("label"),
        options.get("title"),
        question.get("slug"),
        fallback,
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return fallback


def extract_pairs(payload: dict[str, Any]) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    data = payload.get("data")
    if isinstance(data, dict):
        for key, item in data.items():
            if isinstance(item, dict):
                pairs[_question_label(item, str(key))] = _unwrap_value(item)
            else:
                pairs[str(key)] = item
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            label = _question_label(item, "")
            if label:
                pairs[label] = _unwrap_value(item.get("answer", item.get("value")))
    answers = payload.get("answers")
    if isinstance(answers, list):
        for item in answers:
            if not isinstance(item, dict):
                continue
            label = _question_label(item, "")
            if label:
                pairs[label] = _unwrap_value(item.get("answer", item.get("value")))
    skip = {"id", "uid", "survey", "created", "cloud_uid", "data", "answers"}
    for key, value in payload.items():
        if key in skip:
            continue
        pairs[str(key)] = _unwrap_value(value)
    return pairs


def _parse_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise ValueError("invalid integer")
    if isinstance(value, int):
        return value
    text = str(value).strip().replace(" ", "").replace(",", ".")
    if not text:
        return 0
    number = float(text)
    if not number.is_integer():
        raise ValueError(f"expected integer, got {value!r}")
    return int(number)


def _parse_date(value: Any, *, today: date) -> date:
    if value is None or value == "":
        return today
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return today
    if "T" in text:
        text = text.split("T", 1)[0]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"cannot parse date {value!r}")


@dataclass(frozen=True)
class ParsedReport:
    employee: str
    report_date: date
    metrics: dict[str, int]
    form_answer_id: str | None

    @property
    def employee_key(self) -> str:
        return normalize_name(self.employee)


class ParseError(ValueError):
    pass


def parse_report(payload: dict[str, Any], *, today: date | None = None, tz: ZoneInfo | None = None) -> ParsedReport:
    if today is None:
        zone = tz or ZoneInfo("Europe/Moscow")
        today = datetime.now(zone).date()
    mapped: dict[str, Any] = {}
    for label, value in extract_pairs(payload).items():
        field = _LOOKUP.get(_normalize_label(label))
        if field:
            mapped[field] = value
    employee = str(mapped.get("employee") or "").strip()
    if not employee:
        raise ParseError("не указан сотрудник")
    metrics = {field: _parse_int(mapped.get(field)) for field in METRIC_FIELDS}
    answer_id = payload.get("id")
    form_answer_id = str(answer_id) if answer_id not in (None, "") else None
    return ParsedReport(
        employee=employee,
        report_date=_parse_date(mapped.get("report_date"), today=today),
        metrics=metrics,
        form_answer_id=form_answer_id,
    )
