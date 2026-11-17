"""Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).

Complétez ce fichier : objectif >= 90 % de couverture sur minishop/pricing.py.
"""

from decimal import Decimal

import pytest

from minishop.pricing import coupon_discount, line_total, money, quote, shipping_cost

pytestmark = pytest.mark.unit


def test_money_arrondi_commercial():
    """0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12."""
    assert money("0.125") == Decimal("0.13")


def test_line_total_sans_remise():
    assert line_total(Decimal("12.50"), 2) == Decimal("25.00")


def test_quote_panier_vide():
    """Un panier vide coûte 0 € : pas de frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


# TODO Atelier 1 :
#  - remise volume à partir de 10 unités (et pas à 9 !)
@pytest.mark.parametrize("qty, expected", [(9, 90), (10, 95)])
def test_remise_panier_10_unites(qty, expected):
    assert line_total(Decimal('10'), qty) == expected

#  - quantités invalides (0, 100, -1, "2", True) -> ValueError   (astuce : @pytest.mark.parametrize)
@pytest.mark.parametrize("qty", [0, 100, -1, "2", True])
def test_qty_invalide(qty):
    with pytest.raises(ValueError):
        line_total(Decimal("10"), qty)

#  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
@pytest.mark.parametrize(
    "subtotal, coupon, expected_discount",
    [
        (Decimal("19.99"), "WELCOME10", Decimal("0.00")),  # Seuil non atteint (< 20)
        (Decimal("20.00"), "WELCOME10", Decimal("2.00")),  # Seuil inclus (20)
        (Decimal("29.99"), "FIXED5", Decimal("0.00")),     # Seuil non atteint (< 30)
        (Decimal("30.00"), "FIXED5", Decimal("5.00")),     # Seuil inclus (30)
        (Decimal("40.00"), "FREESHIP", Decimal("0.00")),   # FREESHIP n'offre pas de remise en € sur le sous-total
    ],
)
def test_coupons_seuils(subtotal, coupon, expected_discount):
    assert coupon_discount(subtotal, coupon) == expected_discount
def test_coupon_inconnu():
    with pytest.raises(ValueError):
        coupon_discount(Decimal("50.00"), "UNKNOWN_COUPON")


#  - livraison offerte à partir de 50 € APRÈS remise
@pytest.mark.parametrize(
    "after_discount, coupon, empty, expected_shipping",
    [
        (Decimal("49.99"), None, False, Decimal("4.90")),   # Sous 50 € après remise -> frais de port
        (Decimal("50.00"), None, False, Decimal("0.00")),   # 50 € pile après remise -> port offert
        (Decimal("20.00"), "FREESHIP", False, Decimal("0.00")),  # FREESHIP -> port offert
        (Decimal("10.00"), None, True, Decimal("0.00")),    # Panier vide -> port offert (0)
    ],
)
def test_shipping_cost(after_discount, coupon, empty, expected_shipping):
    assert shipping_cost(after_discount, coupon, empty) == expected_shipping

#  - produit inconnu -> KeyError
def test_produit_inconnu():
    with pytest.raises(KeyError):
        quote([{"product_id": "PRODUIT_INEXISTANT", "qty": 1}])


# TDD
@pytest.mark.parametrize(
    "subtotal, expected_discount",
    [
        (Decimal("10.00"), Decimal("1.50")),
        (Decimal("100.00"), Decimal("15.00")),
    ],
)
def test_student15_coupon(subtotal, expected_discount):
    """STUDENT15 offre -15% sans minimum d'achat."""
    assert coupon_discount(subtotal, "STUDENT15") == expected_discount


# Couverture complémentaire
def test_money_bug_rounding(monkeypatch):
    """Avec MINISHOP_BUG=rounding, l'arrondi bancaire est utilisé (0.125 -> 0.12)."""
    monkeypatch.setenv("MINISHOP_BUG", "rounding")
    assert money("0.125") == Decimal("0.12")


@pytest.mark.parametrize("coupon", [None, ""])
def test_coupon_absent(coupon):
    assert coupon_discount(Decimal("100.00"), coupon) == Decimal("0.00")


@pytest.mark.parametrize("coupon", ["welcome10", "  Welcome10  "])
def test_coupon_casse_et_espaces(coupon):
    assert coupon_discount(Decimal("20.00"), coupon) == Decimal("2.00")


def test_quote_avec_lignes_et_coupon():
    from minishop.catalog import list_products

    product = list_products()[0]
    product_id = product.id
    q = quote([{"product_id": product_id, "qty": 2}], coupon=" freeship ")
    assert q.coupon == "FREESHIP"
    assert q.subtotal == money(product.price * 2)
    assert q.discount == Decimal("0.00")
    assert q.shipping == Decimal("0.00")
    assert q.total == q.subtotal
    d = q.as_dict()
    assert d["coupon"] == "FREESHIP"
    assert d["lines"] == [
        {"product_id": product_id, "qty": 2, "unit_price": str(product.price), "total": str(q.subtotal)}
    ]
    assert d["total"] == str(q.total)
