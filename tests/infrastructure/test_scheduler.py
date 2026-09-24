"""
Testes unitários para o módulo scheduler.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.infrastructure.scheduler import (
    executar_job_marcar_atrasados,
    scheduler,
    setup_scheduler,
)


class TestScheduler:
    def test_setup_scheduler_registers_job(self):
        sched = setup_scheduler()
        assert isinstance(sched, AsyncIOScheduler)
        job = sched.get_job("marcar_emprestimos_atrasados")
        assert job is not None
        assert job.name == "Marcar empréstimos atrasados diariamente"

    @pytest.mark.asyncio
    async def test_executar_job_marcar_atrasados(self):
        mock_session = AsyncMock()
        mock_tx = AsyncMock()
        mock_tx.__aenter__.return_value = mock_tx
        mock_tx.__aexit__.return_value = None
        mock_session.begin = MagicMock(return_value=mock_tx)

        mock_session_local = MagicMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.infrastructure.scheduler.AsyncSessionLocal", mock_session_local), \
             patch("app.infrastructure.scheduler.MarcarAtrasadosUseCase") as mock_use_case_cls:
            mock_use_case_instance = AsyncMock()
            mock_use_case_instance.execute.return_value = 5
            mock_use_case_cls.return_value = mock_use_case_instance

            total = await executar_job_marcar_atrasados()

            assert total == 5
            mock_use_case_cls.assert_called_once()
            mock_use_case_instance.execute.assert_awaited_once()
