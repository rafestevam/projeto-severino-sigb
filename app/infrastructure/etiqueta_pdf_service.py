"""Geração de PDF de etiquetas QR Code no formato Pimaco 6180.

Layout: 3 colunas × 11 linhas, etiqueta 63.5 mm × 38.1 mm, margem 8 mm.
Suporte de papel: Letter (612 pt × 792 pt).
"""
from __future__ import annotations

from io import BytesIO

import qrcode
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.domain.entities.exemplar import Exemplar

# ── Constantes de layout Pimaco 6180 ─────────────────────────────────────────
_LABEL_W = 63.5 * mm   # ≈ 180 pt
_LABEL_H = 38.1 * mm   # ≈ 108 pt
_COLS = 3
_ROWS = 11
_MARGIN_LEFT = 8.0 * mm
_MARGIN_TOP = 8.0 * mm
_PAGE_W = 612.0          # Letter width  (pt)
_PAGE_H = 792.0          # Letter height (pt)

# Espaçamento entre colunas / linhas com base no espaço restante
_GAP_H = (_PAGE_W - 2 * _MARGIN_LEFT - _COLS * _LABEL_W) / (_COLS - 1)
_GAP_V = (_PAGE_H - 2 * _MARGIN_TOP - _ROWS * _LABEL_H) / (_ROWS - 1)

_QR_SIZE = 28.0 * mm    # lado da imagem QR dentro da etiqueta
_PADDING = 2.0 * mm     # padding interno horizontal/vertical

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"


class EtiquetaPdfService:
    """Produz PDF binário com etiquetas QR Code para os exemplares fornecidos."""

    def gerar(self, exemplares: list[Exemplar]) -> bytes:
        """Gera o PDF e retorna os bytes resultantes.

        Cada página comporta até 33 etiquetas (3 × 11). Uma nova página é
        adicionada automaticamente quando a capacidade é excedida.

        Args:
            exemplares: objetos Exemplar a serem impressos como etiquetas.

        Returns:
            Bytes do PDF gerado.
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(_PAGE_W, _PAGE_H))

        for idx, exemplar in enumerate(exemplares):
            page_position = idx % (_COLS * _ROWS)
            col = page_position % _COLS
            row = page_position // _COLS

            if idx > 0 and page_position == 0:
                c.showPage()

            x = _MARGIN_LEFT + col * (_LABEL_W + _GAP_H)
            y_base = _PAGE_H - _MARGIN_TOP - (row + 1) * _LABEL_H - row * _GAP_V

            self._desenhar_etiqueta(c, x, y_base, exemplar)

        c.save()
        return buffer.getvalue()

    # ── helpers privados ──────────────────────────────────────────────────────

    def _gerar_qr_image(self, codigo_qr: str) -> ImageReader:
        img = qrcode.make(codigo_qr)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)

    def _desenhar_etiqueta(
        self,
        c: canvas.Canvas,
        x: float,
        y_base: float,
        exemplar: Exemplar,
    ) -> None:
        """Desenha uma etiqueta individual com QR Code, código e localização."""
        qr_buf = self._gerar_qr_image(exemplar.codigo_qr)

        # Imagem QR — canto inferior-esquerdo da etiqueta
        c.drawImage(
            qr_buf,
            x + _PADDING,
            y_base + _PADDING,
            width=_QR_SIZE,
            height=_QR_SIZE,
        )

        # Bloco de texto à direita do QR
        text_x = x + _PADDING + _QR_SIZE + _PADDING

        # Código QR em destaque
        c.setFont(_FONT_BOLD, 7)
        c.drawString(text_x, y_base + _LABEL_H - _PADDING - 8, exemplar.codigo_qr)

        # Localização da estante
        c.setFont(_FONT, 6)
        c.drawString(text_x, y_base + _PADDING + 4, exemplar.localizacao_estante)
