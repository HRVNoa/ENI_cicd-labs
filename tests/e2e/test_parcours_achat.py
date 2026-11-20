"""Test E2E Playwright — POINT DE DÉPART (Atelier 8).

Prérequis : application lancée (make run) ; BASE_URL=http://localhost:8000 par défaut.
Lancer :   pytest -m e2e --headed        (pour voir le navigateur)
"""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_page_accueil(page: Page, app_url):
    page.goto(app_url)
    expect(page).to_have_title(re.compile("MiniShop"))
    expect(page.get_by_test_id("products").locator("li")).to_have_count(5)


def test_parcours_achat_welcome10(page: Page, app_url):
    """2 mugs + WELCOME10 -> total 27.40 € -> commande confirmée."""
    page.goto(app_url)

    # Ajouter 2 mugs
    add_mug = page.get_by_test_id("add-mug")
    add_mug.click()
    add_mug.click()
    expect(page.get_by_test_id("cart-mug")).to_have_text(re.compile(r"× 2$"))

    # Appliquer le coupon et calculer le total
    page.get_by_test_id("coupon").fill("WELCOME10")
    page.get_by_role("button", name="Calculer le total").click()
    expect(page.get_by_test_id("subtotal")).to_have_text("25.00")
    expect(page.get_by_test_id("discount")).to_have_text("2.50")
    expect(page.get_by_test_id("shipping")).to_have_text("4.90")
    expect(page.get_by_test_id("total")).to_have_text("27.40")

    # Commander
    page.get_by_role("button", name="Commander").click()
    expect(page.get_by_test_id("confirmation")).to_have_text(re.compile(r"^Commande .+ confirmée$"))
