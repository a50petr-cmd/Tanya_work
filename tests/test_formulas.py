from decimal import Decimal

from app.formulas import chkd_blago, chkd_sberhealth


def test_chkd_blago_example() -> None:
    assert chkd_blago(10) == Decimal("6.67")
    assert chkd_blago(0) == Decimal("0.00")


def test_chkd_sberhealth_example() -> None:
    assert chkd_sberhealth(10) == Decimal("6.50")
    assert chkd_sberhealth(0) == Decimal("0.00")
