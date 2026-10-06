import assert from "node:assert/strict";
import test from "node:test";

import {
  afterDeadline,
  buildSummary,
  buildTotals,
  chkdBlago,
  chkdSberhealth,
  formatMetricLine,
  normalizeIncomingText,
  parseReport,
} from "../cloudflare/worker.js";

test("formulas match the agreed examples", () => {
  assert.equal(chkdBlago(10), 6.67);
  assert.equal(chkdSberhealth(10), 6.5);
  assert.equal(chkdBlago(0), 0);
});

test("parses named form payload", () => {
  const report = parseReport(
    {
      employee: "Соколова Анна",
      report_date: "06.10.2026",
      meetings_ab: 4,
      stars: 1,
      passives: 0,
      pl_credit: 1,
      issues: 0,
      leasing: 1,
      salary: 0,
      te: 0,
      knk: 2,
      chkd_blago: 10,
      chkd_sberhealth: 10,
      chkd_accreds: 0,
    },
    "2026-10-06",
  );
  assert.equal(report.employee, "Соколова Анна");
  assert.equal(report.report_date, "2026-10-06");
  assert.equal(report.metrics.meetings_ab, 4);
  assert.equal(report.metrics.chkd_blago, 10);
});

test("summary uses calculated CHKD lines", () => {
  assert.equal(formatMetricLine("chkd_blago", 10), "ЧКД Благо: 6,67 (введено 10)");
  assert.equal(formatMetricLine("chkd_sberhealth", 10), "ЧКД СберЗдоровье: 6,50 (введено 10)");
  const text = buildSummary(
    "2026-10-06",
    [
      {
        employee: "Соколова Анна",
        report_date: "2026-10-06",
        meetings_ab: 4,
        stars: 1,
        passives: 0,
        pl_credit: 1,
        issues: 0,
        leasing: 1,
        salary: 0,
        te: 0,
        knk: 2,
        chkd_blago: 10,
        chkd_sberhealth: 10,
        chkd_accreds: 0,
      },
    ],
    ["Иванов"],
    10,
  );
  assert.match(text, /Сдали 1 из 10/);
  assert.match(text, /Не сдали: Иванов/);
});

test("late report is after 18:00 Moscow", () => {
  const late = new Date("2026-10-06T15:40:00Z");
  assert.equal(afterDeadline("2026-10-06", late, 18, 0, null), true);
  const early = new Date("2026-10-06T12:00:00Z");
  assert.equal(afterDeadline("2026-10-06", early, 18, 0, null), false);
});

test("keyboard labels map to commands", () => {
  assert.equal(normalizeIncomingText("Сводный"), "/svod");
  assert.equal(normalizeIncomingText("Сегодня"), "/today");
  assert.equal(normalizeIncomingText("Не сдали"), "/missing");
  assert.equal(normalizeIncomingText("За дату"), "/date");
  assert.equal(normalizeIncomingText("Помощь"), "/start");
});

test("totals sum employee metrics and apply formulas", () => {
  const text = buildTotals(
    "2026-10-07",
    [
      {
        employee: "Алексеев",
        report_date: "2026-10-07",
        meetings_ab: 2,
        stars: 3,
        passives: 2,
        pl_credit: 3,
        issues: 4,
        leasing: 2,
        salary: 4,
        te: 2,
        knk: 4,
        chkd_blago: 10,
        chkd_sberhealth: 12,
        chkd_accreds: 34,
      },
      {
        employee: "Соколова Анна",
        report_date: "2026-10-07",
        meetings_ab: 4,
        stars: 1,
        passives: 0,
        pl_credit: 1,
        issues: 0,
        leasing: 1,
        salary: 0,
        te: 0,
        knk: 2,
        chkd_blago: 10,
        chkd_sberhealth: 10,
        chkd_accreds: 0,
      },
    ],
    ["Иванов"],
    10,
  );
  assert.match(text, /Сводный отчёт за 07.10.2026/);
  assert.match(text, /Сдали 2 из 10/);
  assert.match(text, /Не сдали: Иванов/);
  assert.match(text, /Встречи AB: 6/);
  assert.match(text, /ЧКД Благо: 13,33 \(введено 20\)/);
  assert.match(text, /ЧКД СберЗдоровье: 14,30 \(введено 22\)/);
  assert.match(text, /Сдали: Алексеев, Соколова Анна/);
});
