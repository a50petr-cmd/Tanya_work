from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")


def _as_decimal(value: int | float | str | Decimal) -> Decimal:
    return Decimal(str(value))


def money(value: int | float | str | Decimal) -> Decimal:
    return _as_decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def chkd_blago(raw: int | float | str | Decimal) -> Decimal:
    """ЧКД Благо: введённое число × 0,8 / 1,2."""
    return money(_as_decimal(raw) * Decimal("0.8") / Decimal("1.2"))


def chkd_sberhealth(raw: int | float | str | Decimal) -> Decimal:
    """ЧКД СберЗдоровье: введённое число × 0,65."""
    return money(_as_decimal(raw) * Decimal("0.65"))
