from __future__ import annotations

import html
from datetime import date

from app.parser import METRIC_FIELDS

# (field, label, подсказка)
FORM_METRICS: tuple[tuple[str, str, str], ...] = (
    ("meetings_ab", "Встречи AB", "целое число"),
    ("stars", "Звезды", "целое число"),
    ("passives", "Пассивы", "целое число"),
    ("pl_credit", "PL по кредитованию", "целое число"),
    ("issues", "Выдачи", "целое число"),
    ("leasing", "Лизинг", "целое число"),
    ("salary", "ЗП", "целое число"),
    ("te", "ТЭ", "целое число"),
    ("knk", "КНК", "целое число"),
    ("chkd_blago", "ЧКД Благо", "исходное число для расчёта"),
    ("chkd_sberhealth", "ЧКД СберЗдоровье", "исходное число для расчёта"),
    ("chkd_accreds", "ЧКД Аккреды", "целое число"),
)


def form_access_token(settings) -> str:
    explicit = getattr(settings, "form_page_token", "") or ""
    if explicit:
        return explicit
    return settings.forms_webhook_secret or ""


def check_form_key(settings, key: str | None) -> bool:
    token = form_access_token(settings)
    if not token:
        return True
    return (key or "").strip() == token


def payload_from_form(form: dict[str, str]) -> dict[str, str | int]:
    payload: dict[str, str | int] = {
        "employee": form.get("employee", "").strip(),
        "report_date": form.get("report_date", "").strip(),
    }
    for field, _, _ in FORM_METRICS:
        raw = form.get(field, "").strip()
        payload[field] = raw if raw != "" else 0
    return payload


def render_report_page(
    *,
    employees: tuple[str, ...],
    default_date: date,
    access_key: str,
    error: str | None = None,
    success: str | None = None,
) -> str:
    esc = html.escape
    key = esc(access_key)
    date_val = default_date.isoformat()

    employee_options = []
    if employees:
        for name in employees:
            employee_options.append(f'<option value="{esc(name)}">{esc(name)}</option>')
        employee_field = (
            '<label>Сотрудник<select name="employee" required>'
            '<option value="">— выберите —</option>'
            + "".join(employee_options)
            + "</select></label>"
        )
    else:
        employee_field = (
            '<label>Фамилия и имя<input name="employee" type="text" required '
            'autocomplete="name" placeholder="Как в списке команды"></label>'
        )

    metric_fields = []
    for field, label, hint in FORM_METRICS:
        metric_fields.append(
            f'<label>{esc(label)}'
            f'<span class="hint">{esc(hint)}</span>'
            f'<input name="{esc(field)}" type="number" inputmode="numeric" '
            f'min="0" step="1" value="0" required></label>'
        )

    banner = ""
    if error:
        banner = f'<p class="banner error">{esc(error)}</p>'
    elif success:
        banner = f'<p class="banner ok">{esc(success)}</p>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ежедневный отчёт</title>
  <style>
    :root {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
    body {{ margin: 0; background: #f4f6f8; color: #1a1a1a; }}
    main {{ max-width: 420px; margin: 0 auto; padding: 16px 16px 32px; }}
    h1 {{ font-size: 1.25rem; margin: 0 0 8px; }}
    p.lead {{ margin: 0 0 16px; color: #555; font-size: 0.9rem; }}
    form {{ display: flex; flex-direction: column; gap: 14px; }}
    label {{ display: flex; flex-direction: column; gap: 4px; font-size: 0.95rem; font-weight: 600; }}
    .hint {{ font-weight: 400; font-size: 0.75rem; color: #666; }}
    input, select {{
      font: inherit; font-weight: 400; padding: 10px 12px; border: 1px solid #ccd;
      border-radius: 8px; background: #fff;
    }}
    button {{
      margin-top: 8px; padding: 14px; font: inherit; font-weight: 600;
      background: #0077ff; color: #fff; border: 0; border-radius: 10px;
    }}
    .banner {{ padding: 12px; border-radius: 8px; font-size: 0.9rem; }}
    .banner.error {{ background: #ffe8e8; color: #a00; }}
    .banner.ok {{ background: #e6f7ed; color: #065; }}
  </style>
</head>
<body>
  <main>
    <h1>Ежедневный отчёт</h1>
    <p class="lead">ЧКД Благо и СберЗдоровье: вводите исходное число — в сводке пересчитаем.</p>
    {banner}
    <form method="post" action="/report/submit">
      <input type="hidden" name="access_key" value="{key}">
      {employee_field}
      <label>Дата отчёта
        <input name="report_date" type="date" value="{date_val}" required>
      </label>
      {"".join(metric_fields)}
      <button type="submit">Отправить отчёт</button>
    </form>
  </main>
</body>
</html>"""
