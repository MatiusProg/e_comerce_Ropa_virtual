"""Los importes que lee el usuario van en Bs y con formato boliviano.

Bugs de las capturas de la P3: el aviso «Pago confirmado» decía «3600.00 USD»
(se armaba con `PAGO_MONEDA`, que es la moneda de la prueba de Stripe) y el PDF
de reportes mostraba 2,732.00.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.core import moneda
from app.modules.notificaciones import service as notificaciones
from app.modules.reportes.exportador import _texto


def test_numero_y_bs_usan_punto_de_miles_y_coma_decimal() -> None:
    assert moneda.numero(Decimal("2732")) == "2.732,00"
    assert moneda.numero(1234567.5) == "1.234.567,50"
    assert moneda.numero(12) == "12,00"
    assert moneda.bs(Decimal("3600.00")) == "Bs 3.600,00"


def test_el_pdf_de_reportes_escribe_los_importes_en_formato_boliviano() -> None:
    assert _texto(Decimal("2732.00")) == "2.732,00"
    assert _texto(2732.0) == "2.732,00"


def test_el_aviso_de_pago_confirmado_va_en_bs_aunque_stripe_cobre_en_usd(monkeypatch) -> None:
    monkeypatch.setattr(notificaciones.settings, "PAGO_MONEDA", "usd")
    monkeypatch.setattr(notificaciones, "_usuario_del_cliente", lambda db, cid: object())
    capturado: dict = {}
    monkeypatch.setattr(notificaciones, "notificar", lambda db, **kw: capturado.update(kw))

    venta = SimpleNamespace(id=1, codigo="WEB-000001", cliente_id=7, total=Decimal("3600.00"))
    notificaciones.avisar_pedido_pagado(None, venta)

    assert "Bs 3.600,00" in capturado["cuerpo"]
    assert "USD" not in capturado["cuerpo"]
