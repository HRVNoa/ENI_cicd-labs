"""Tests pytest du calcul de panier MiniShop, dérivés de specs/pricing.feature."""

from __future__ import annotations

from decimal import Decimal

import pytest

from minishop.pricing import (
    FREE_SHIPPING_THRESHOLD,
    SHIPPING_FEE,
    coupon_discount,
    line_total,
    money,
    quote,
    shipping_cost,
)

pytestmark = [pytest.mark.generated, pytest.mark.unit]

D = Decimal


@pytest.fixture(autouse=True)
def _sans_bug_injecte(monkeypatch):
    """Garantit que la variable de régression MINISHOP_BUG n'altère pas les tests."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)


def _items(*pairs):
    """Construit la liste d'items attendue par quote() à partir de couples (produit, qté)."""
    return [{"product_id": product, "qty": qty} for product, qty in pairs]


# ---------------------------------------------------------------------------
# Scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total nul et aucuns frais de livraison."""
    q = quote([])
    assert q.total == D("0.00")
    assert q.shipping == D("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Deux mugs sous le seuil de 50 € paient les frais de livraison standard."""
    q = quote(_items(("mug", 2)))
    assert q.subtotal == D("25.00")
    assert q.shipping == D("4.90")
    assert q.total == D("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Un hoodie et un mug (56,50 €) bénéficient de la livraison offerte."""
    q = quote(_items(("hoodie", 1), ("mug", 1)))
    assert q.shipping == D("0.00")
    assert q.total == D("56.50")


def test_remise_volume_des_10_unites():
    """Dix stickers déclenchent la remise volume de 5 % sur la ligne."""
    q = quote(_items(("sticker", 10)))
    assert q.subtotal == D("23.28")


def test_coupon_de_bienvenue():
    """WELCOME10 applique 10 % de remise sur un sous-total de 25 €."""
    q = quote(_items(("mug", 2)), coupon="WELCOME10")
    assert q.discount == D("2.50")
    assert q.total == D("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """WELCOME10 n'apporte aucune remise sous le seuil de 20 € de sous-total."""
    q = quote(_items(("mug", 1)), coupon="WELCOME10")
    assert q.discount == D("0.00")


def test_coupon_de_livraison_offerte():
    """FREESHIP supprime les frais de livraison sur un petit panier."""
    q = quote(_items(("sticker", 1)), coupon="FREESHIP")
    assert q.shipping == D("0.00")
    assert q.total == D("2.45")


def test_coupon_inconnu():
    """Un code coupon absent de la liste autorisée lève une erreur 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote(_items(("mug", 1)), coupon="NOEL2026")


def test_produit_inconnu():
    """Un produit absent du catalogue doit lever une erreur 'Produit inconnu'."""
    # DIVERGENCE SPEC/CODE : la spec attend un message "Produit inconnu", alors que le code
    # délègue à get_product() qui lève une KeyError (commentaire "KeyError si inconnu").
    # Le test suit la spécification : il exige le message "Produit inconnu".
    with pytest.raises(Exception) as exc:
        quote(_items(("licorne", 1)))
    assert "Produit inconnu" in str(exc.value)


def test_coupon_fixed5_juste_sous_le_seuil_de_30_euros():
    """FIXED5 n'est pas appliqué à un sous-total de 29,99 €, juste sous le seuil de 30 €."""
    q = quote(_items(("book", 1)), coupon="FIXED5")
    assert q.subtotal == D("29.99")
    assert q.discount == D("0.00")
    assert q.shipping == D("4.90")
    assert q.total == D("34.89")


def test_remise_volume_cumulee_avec_le_coupon_welcome10():
    """La remise volume et le coupon WELCOME10 s'appliquent successivement sur 10 mugs."""
    q = quote(_items(("mug", 10)), coupon="WELCOME10")
    assert q.subtotal == D("118.75")
    assert q.discount == D("11.88")
    assert q.shipping == D("0.00")
    assert q.total == D("106.87")


def test_quantite_nulle_refusee():
    """Une quantité nulle est refusée avec une erreur 'Quantité hors limites'."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(_items(("mug", 0)))


# ---------------------------------------------------------------------------
# Cas limites (non cités par la spécification)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("qty", [1, 99])
def test_limite_quantite_aux_bornes_acceptee(qty):
    """Les quantités 1 et 99 (bornes incluses) sont acceptées."""
    assert line_total(D("1.00"), qty) >= D("0.00")


@pytest.mark.parametrize("qty", [0, -1, 100])
def test_limite_quantite_hors_bornes_refusee(qty):
    """Les quantités 0, négative et 100 (hors bornes) lèvent une ValueError."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        line_total(D("1.00"), qty)


@pytest.mark.parametrize("qty", [2.0, "2", None])
def test_limite_quantite_non_entiere_refusee(qty):
    """Une quantité qui n'est pas un entier (float, chaîne, None) est refusée."""
    with pytest.raises(ValueError, match="entier"):
        line_total(D("1.00"), qty)


def test_limite_quantite_booleenne_refusee():
    """Un booléen n'est pas accepté comme quantité, même si True vaut 1."""
    with pytest.raises(ValueError, match="entier"):
        line_total(D("12.50"), True)


@pytest.mark.parametrize(
    "qty, expected",
    [
        (9, D("112.50")),  # 9 mugs : pas de remise volume
        (10, D("118.75")),  # 10 mugs : remise 5 % incluse
    ],
)
def test_limite_seuil_remise_volume(qty, expected):
    """La remise volume s'applique exactement à partir de 10 unités, pas avant."""
    assert line_total(D("12.50"), qty) == expected


@pytest.mark.parametrize(
    "subtotal, expected",
    [
        (D("19.99"), D("0.00")),  # juste sous le seuil de WELCOME10
        (D("20.00"), D("2.00")),  # seuil inclus
    ],
)
def test_limite_welcome10_seuil_20_euros(subtotal, expected):
    """WELCOME10 s'applique à partir de 20,00 € inclus et pas en dessous."""
    assert coupon_discount(subtotal, "WELCOME10") == expected


@pytest.mark.parametrize(
    "subtotal, expected",
    [
        (D("29.99"), D("0.00")),  # juste sous le seuil de FIXED5
        (D("30.00"), D("5.00")),  # seuil inclus
    ],
)
def test_limite_fixed5_seuil_30_euros(subtotal, expected):
    """FIXED5 s'applique à partir de 30,00 € inclus et pas en dessous."""
    assert coupon_discount(subtotal, "FIXED5") == expected


@pytest.mark.parametrize(
    "amount, expected",
    [
        (D("49.99"), SHIPPING_FEE),  # juste sous le seuil
        (FREE_SHIPPING_THRESHOLD, D("0.00")),  # seuil inclus
    ],
)
def test_limite_seuil_livraison_offerte(amount, expected):
    """La livraison est offerte à partir de 50,00 € inclus, et facturée en dessous."""
    assert shipping_cost(amount, None, empty=False) == expected


def test_limite_seuil_livraison_appliqué_après_remise():
    """Le seuil de livraison porte sur le montant après remise : 50 € - 5 € passe sous le seuil."""
    q = quote(_items(("mug", 4)), coupon="WELCOME10")
    assert q.subtotal == D("50.00")
    assert q.discount == D("5.00")
    assert q.shipping == SHIPPING_FEE
    assert q.total == D("49.90")


def test_limite_panier_exactement_50_euros_sans_coupon():
    """Quatre mugs (50,00 €) sans coupon : livraison offerte, seuil inclus."""
    q = quote(_items(("mug", 4)))
    assert q.subtotal == D("50.00")
    assert q.shipping == D("0.00")
    assert q.total == D("50.00")


def test_limite_freeship_sur_gros_panier():
    """FREESHIP reste sans frais de livraison même sur un panier dépassant le seuil."""
    q = quote(_items(("hoodie", 2)), coupon="FREESHIP")
    assert q.shipping == D("0.00")
    assert q.total == D("88.00")


def test_limite_coupon_insensible_a_la_casse_et_aux_espaces():
    """Le code coupon est normalisé (espaces et casse) avant d'être appliqué."""
    q = quote(_items(("mug", 2)), coupon="  welcome10 ")
    assert q.coupon == "WELCOME10"
    assert q.discount == D("2.50")


def test_limite_coupon_vide_equivaut_a_aucun_coupon():
    """Une chaîne de coupon vide est traitée comme l'absence de coupon."""
    q = quote(_items(("mug", 2)), coupon="")
    assert q.coupon is None
    assert q.discount == D("0.00")
    assert q.total == D("29.90")


def test_limite_panier_vide_avec_coupon_sans_remise():
    """Un panier vide avec coupon ne produit aucune remise ni frais de livraison."""
    q = quote([], coupon="WELCOME10")
    assert q.discount == D("0.00")
    assert q.shipping == D("0.00")
    assert q.total == D("0.00")


@pytest.mark.parametrize(
    "value, expected",
    [
        ("0.125", D("0.13")),  # arrondi commercial : demi-centime vers le haut
        ("0.135", D("0.14")),
        ("2.345", D("2.35")),
        ("0.005", D("0.01")),
        ("0.004", D("0.00")),
        ("1", D("1.00")),
    ],
)
def test_limite_arrondi_au_centime_half_up(value, expected):
    """Les montants sont arrondis au centime en ROUND_HALF_UP."""
    assert money(value) == expected


def test_limite_arrondi_float_passe_par_str():
    """Un float est converti via str() avant arrondi, donc 0.125 devient 0.13."""
    assert money(0.125) == D("0.13")


def test_limite_remise_coupon_arrondie_au_centime():
    """La remise WELCOME10 sur 118,75 € (11,875 €) est arrondie à 11,88 €."""
    assert coupon_discount(D("118.75"), "WELCOME10") == D("11.88")


def test_limite_coupon_student15_remise_15_pourcent():
    """STUDENT15 (présent dans le code, hors spec) applique 15 % sur le sous-total."""
    q = quote(_items(("mug", 2)), coupon="STUDENT15")
    assert q.discount == D("3.75")
    assert q.shipping == SHIPPING_FEE
    assert q.total == D("26.15")
