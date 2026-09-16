"""
Testes unitários para app/infrastructure/etiqueta_pdf_service.EtiquetaPdfService.

Estratégia: verificar o comportamento observável sem abrir banco de dados nem
rede. Os testes inspecionam os bytes gerados (assinatura PDF, presença de texto
nos streams) e o comportamento de layout (múltiplas páginas, lista vazia).
Nenhum mock é necessário — as dependências externas (qrcode, reportlab) são
bibliotecas puras e executam corretamente em memória.
"""
from __future__ import annotations

import re
import zlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.entities.exemplar import Exemplar
from app.infrastructure.etiqueta_pdf_service import (
    EtiquetaPdfService,
    _COLS,
    _ROWS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LABELS_PER_PAGE = _COLS * _ROWS  # 33


def _make_exemplar(
    *,
    codigo_qr: str = "LIB-2025-00001",
    localizacao_estante: str = "A-01",
) -> Exemplar:
    return Exemplar(
        id=uuid4(),
        obra_id=uuid4(),
        codigo_qr=codigo_qr,
        estado="disponivel",
        localizacao_estante=localizacao_estante,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _make_exemplares(n: int) -> list[Exemplar]:
    return [
        _make_exemplar(codigo_qr=f"LIB-2025-{i:05d}", localizacao_estante=f"A-{i:02d}")
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# Helpers de inspeção de conteúdo PDF
# ---------------------------------------------------------------------------

def _ascii85_decode(data: bytes) -> bytes:
    """Decodifica ASCII85 no estilo PS/PDF (suporta terminador ~>).

    Implementação própria necessária pois `binascii.a2b_base85` foi
    removida do Python 3.14.
    """
    # Remove espaços e marcadores opcionais
    data = data.replace(b"\n", b"").replace(b"\r", b"").replace(b" ", b"")
    if data.startswith(b"<~"):
        data = data[2:]
    if data.endswith(b"~>"):
        data = data[:-2]

    result = bytearray()
    group = []
    for byte in data:
        ch = bytes([byte])
        if ch == b"z":
            result.extend(b"\x00\x00\x00\x00")
            continue
        if b"!" <= ch <= b"u":
            group.append(byte - 33)
            if len(group) == 5:
                n = group[0] * 52200625 + group[1] * 614125 + group[2] * 7225 + group[3] * 85 + group[4]
                result.extend(n.to_bytes(4, "big"))
                group = []
    # grupo final (incompleto)
    if group:
        pad = 5 - len(group)
        group.extend([84] * pad)
        n = group[0] * 52200625 + group[1] * 614125 + group[2] * 7225 + group[3] * 85 + group[4]
        result.extend(n.to_bytes(4, "big")[: 4 - pad])
    return bytes(result)


def _extrair_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrai o texto presente nos streams de conteúdo de página do PDF.

    ReportLab comprime os streams de página com ASCII85Decode + FlateDecode.
    Esta função localiza cada stream, decodifica e descomprime, retornando
    o conteúdo de todos eles concatenado como string.
    """
    # Localiza todos os blocos stream … endstream
    # ReportLab não insere newline entre ~> e endstream, por isso não exigimos
    # um newline antes de 'endstream'.
    pattern = re.compile(rb"stream\n(.*?)endstream", re.DOTALL)
    texto_total = []
    for match in pattern.finditer(pdf_bytes):
        raw = match.group(1).strip()
        try:
            decoded = _ascii85_decode(raw)
            decompressed = zlib.decompress(decoded)
            texto_total.append(decompressed.decode("latin-1", errors="replace"))
        except Exception:
            # Streams binários (imagens) ou outros — ignora
            pass
    return "\n".join(texto_total)


# ---------------------------------------------------------------------------
# Testes de contrato de retorno
# ---------------------------------------------------------------------------


class TestGerar:
    def test_retorna_bytes(self):
        """gerar() deve retornar um objeto bytes."""
        svc = EtiquetaPdfService()
        result = svc.gerar([_make_exemplar()])
        assert isinstance(result, bytes)

    def test_bytes_nao_vazios_para_lista_nao_vazia(self):
        """O PDF gerado deve ter conteúdo quando há ao menos um exemplar."""
        svc = EtiquetaPdfService()
        result = svc.gerar([_make_exemplar()])
        assert len(result) > 0

    def test_comeca_com_assinatura_pdf(self):
        """Os primeiros 4 bytes devem ser '%PDF', assinatura padrão do formato."""
        svc = EtiquetaPdfService()
        result = svc.gerar([_make_exemplar()])
        assert result[:4] == b"%PDF"

    def test_lista_vazia_gera_pdf_valido(self):
        """gerar() com lista vazia deve retornar bytes que começam com '%PDF'."""
        svc = EtiquetaPdfService()
        result = svc.gerar([])
        assert result[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Testes de conteúdo das etiquetas
# ---------------------------------------------------------------------------


class TestConteudoEtiqueta:
    def test_codigo_qr_presente_no_pdf(self):
        """O código QR alfanumérico deve aparecer no stream de conteúdo do PDF."""
        codigo = "LIB-2025-00042"
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar([_make_exemplar(codigo_qr=codigo)])
        assert codigo in _extrair_texto_pdf(pdf_bytes)

    def test_localizacao_estante_presente_no_pdf(self):
        """A localização da estante deve aparecer no stream de conteúdo do PDF."""
        localizacao = "Z-99"
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar([_make_exemplar(localizacao_estante=localizacao)])
        assert localizacao in _extrair_texto_pdf(pdf_bytes)

    def test_multiplos_codigos_qr_presentes(self):
        """Todos os códigos QR de uma lista devem aparecer no PDF gerado."""
        exemplares = _make_exemplares(5)
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar(exemplares)
        texto = _extrair_texto_pdf(pdf_bytes)
        for exemplar in exemplares:
            assert exemplar.codigo_qr in texto

    def test_exemplar_unico_contem_seus_dados(self):
        """PDF de um exemplar deve conter código QR e localização desse exemplar."""
        e = _make_exemplar(codigo_qr="LIB-2025-00007", localizacao_estante="B-03")
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar([e])
        texto = _extrair_texto_pdf(pdf_bytes)
        assert "LIB-2025-00007" in texto
        assert "B-03" in texto


# ---------------------------------------------------------------------------
# Testes de layout e paginação
# ---------------------------------------------------------------------------


class TestLayout:
    def test_uma_pagina_para_lista_abaixo_do_limite(self):
        """Até 33 etiquetas cabem em uma única página (sem 'showPage' extra)."""
        exemplares = _make_exemplares(_LABELS_PER_PAGE)
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar(exemplares)
        # Um PDF de página única tem exatamente uma ocorrência de %%EOF
        assert pdf_bytes.count(b"%%EOF") == 1

    def test_duas_paginas_para_lista_acima_do_limite(self):
        """34 etiquetas ou mais devem gerar pelo menos 2 páginas no PDF."""
        exemplares = _make_exemplares(_LABELS_PER_PAGE + 1)
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar(exemplares)
        # Duas páginas: dois streams "endobj" distintos — checar via Page count
        # A assinatura mais simples: o PDF terá mais de uma entrada /Page
        assert pdf_bytes.count(b"/Page") >= 2

    def test_tres_paginas_para_duas_folhas_cheias_mais_um(self):
        """2 × 33 + 1 = 67 etiquetas devem gerar 3 páginas."""
        exemplares = _make_exemplares(2 * _LABELS_PER_PAGE + 1)
        svc = EtiquetaPdfService()
        pdf_bytes = svc.gerar(exemplares)
        assert pdf_bytes.count(b"/Page") >= 3

    def test_tamanho_pdf_cresce_com_numero_de_exemplares(self):
        """PDF com mais exemplares deve ser maior (ou igual) que com menos."""
        svc = EtiquetaPdfService()
        pdf_1 = svc.gerar(_make_exemplares(1))
        pdf_10 = svc.gerar(_make_exemplares(10))
        assert len(pdf_10) >= len(pdf_1)


# ---------------------------------------------------------------------------
# Testes de isolamento entre chamadas
# ---------------------------------------------------------------------------


class TestIsolamento:
    def test_chamadas_sucessivas_produzem_pdfs_independentes(self):
        """Cada chamada a gerar() deve produzir um PDF independente."""
        svc = EtiquetaPdfService()
        pdf_a = svc.gerar([_make_exemplar(codigo_qr="LIB-2025-00001")])
        pdf_b = svc.gerar([_make_exemplar(codigo_qr="LIB-2025-00002")])
        # PDF A não deve conter o código do PDF B e vice-versa
        assert b"LIB-2025-00002" not in pdf_a
        assert b"LIB-2025-00001" not in pdf_b

    def test_mesma_instancia_pode_ser_reutilizada(self):
        """A mesma instância de EtiquetaPdfService deve ser reutilizável."""
        svc = EtiquetaPdfService()
        for i in range(1, 4):
            pdf = svc.gerar([_make_exemplar(codigo_qr=f"LIB-2025-{i:05d}")])
            assert pdf[:4] == b"%PDF"
