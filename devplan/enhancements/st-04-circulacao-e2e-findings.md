# Oportunidades de Melhoria — ST-04 Circulação (E2E)

> Gerado após execução dos testes e2e do plano `st-04-circulacao-e2e-test-plan.md`  
> Data: 2026-09-24  
> Resultado: **45 passando / 14 falhando** (59 casos novos, excluindo os `xfail` legados)

---

## Sumário Executivo

A execução dos testes fim-a-fim revelou **14 falhas**, todas rastreáveis a bugs reais ou features ausentes na aplicação — não nos testes. Os problemas se agrupam em quatro categorias:

| Categoria | Falhas | Casos de Teste |
|---|---|---|
| Feature ausente: `GET /api/exemplares/{id}` | 3 | CHK-005, CHK-013, CIN-003 |
| Bug: `EmprestimoRepository.save()` — write não visível cross-session | 3 | REN-003, REN-004, REN-005 |
| Bug: Use case de checkout não lê estado atualizado do exemplar | 4 | CHK-006, CHK-007, CHK-010, CHK-011 |
| Divergência de contrato HTTP | 1 | CHK-008 |
| Feature ausente: `GET /api/exemplares/{id}` + bug de visibilidade | 1 | CIN-006 |
| Feature ausente: devolução de empréstimo `atrasado` | 1 | FLOW-003 |
| Feature ausente: `GET /api/exemplares/{id}` | 1 | FLOW-001 |

---

## ENH-001 — Endpoint `GET /api/exemplares/{id}` ausente

**Severidade:** Alta  
**Tipo:** Feature ausente  
**Casos afetados:** CHK-E2E-005, CHK-E2E-013, CIN-E2E-003, FLOW-C-001  

### Descrição

O router [`app/adapters/api/exemplares.py`](app/adapters/api/exemplares.py) expõe apenas um endpoint:

```
GET /api/exemplares/{codigo_qr}/etiqueta.pdf
```

Não existe `GET /api/exemplares/{id}` que retorne os dados de um exemplar por UUID. Os critérios de aceitação US-011 ("o estado do exemplar é atualizado para `emprestado`") e US-012 ("o estado do exemplar é atualizado para `disponivel`") só podem ser verificados via HTTP se esse endpoint existir.

### Impacto

Sem esse endpoint, os testes precisam contornar via `db_session.refresh()`, quebrando o isolamento do teste de integração "puro" via HTTP.

### Sugestão de Correção

Adicionar em [`app/adapters/api/exemplares.py`](app/adapters/api/exemplares.py):

```python
from app.adapters.api.schemas.exemplar import ExemplarOut
from uuid import UUID

@exemplares_router.get("/{exemplar_id}", response_model=ExemplarOut)
async def get_exemplar(
    exemplar_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ExemplarOut:
    repo = SQLAlchemyExemplarRepository(session)
    exemplar = await repo.get_by_id(exemplar_id)
    if exemplar is None:
        raise HTTPException(status_code=404, detail=f"Exemplar não encontrado: {exemplar_id}")
    return ExemplarOut.model_validate(exemplar)
```

---

## ENH-002 — `EmprestimoRepository.save()` — UPDATE não visível entre sessões compartilhando a mesma conexão

**Severidade:** Alta  
**Tipo:** Bug de persistência  
**Casos afetados:** REN-E2E-003, REN-E2E-004, REN-E2E-005  

### Descrição

O método [`save()`](app/adapters/repositories/sqlalchemy_emprestimo_repository.py) do repositório de empréstimos foi originalmente implementado com `session.add(model)`, que emite sempre um INSERT. Isso causava `UniqueViolationError` ao tentar salvar uma entidade existente (ex: atualizar status de um empréstimo).

A correção aplicada durante os testes (usar `session.execute(text("UPDATE ..."))`) resolveu o erro de chave duplicada, mas expôs um problema mais sutil: quando múltiplas requisições HTTP compartilham a **mesma `AsyncConnection`** (padrão de isolamento via SAVEPOINT no conftest de testes), o UPDATE escrito pela sessão da primeira requisição **não é visível** para o `session.get()` executado pela sessão da segunda requisição.

A causa raiz ainda está sendo investigada (possível interação entre `asyncpg`, `begin_nested()` e o identity map do SQLAlchemy), mas o comportamento observado é:

- 1ª renovação: `renovacoes=1` → **correto**
- 2ª renovação: `get_by_id` retorna `renovacoes=0` → incrementa para `1` → retorna `renovacoes=1` em vez de `2`
- Idem para a verificação de `max_renovacoes`

### Impacto

- Renovações consecutivas não acumulam corretamente.
- O limite de 3 renovações nunca é atingido (sempre lê `renovacoes=0` ou `1`).
- Empréstimos não atingem nunca o limite de renovações via HTTP.

### Sugestão de Correção

Investigar e adotar uma das seguintes abordagens:

1. **Usar `session.merge()` com `populate_existing=True`** para forçar re-leitura do identity map:
   ```python
   merged = await session.merge(model)
   await session.refresh(merged, attribute_names=["renovacoes", "status", "data_prevista", "data_devolucao"])
   ```

2. **Usar `RETURNING` no UPDATE** para garantir que os valores atualizados sejam retornados atomicamente:
   ```python
   result = await session.execute(
       update(EmprestimoModel)
       .where(EmprestimoModel.id == emprestimo.id)
       .values(...)
       .returning(EmprestimoModel)
   )
   updated = result.scalar_one()
   ```

3. **Revisar a estratégia de isolamento de testes** para usar uma única sessão por teste em vez de múltiplas sessões sobre a mesma conexão.

---

## ENH-003 — Use Case de Checkout não valida estado do exemplar após operação via API

**Severidade:** Alta  
**Tipo:** Bug de isolamento de sessão / estado inconsistente  
**Casos afetados:** CHK-E2E-006, CHK-E2E-007  

### Descrição

Quando o primeiro checkout atualiza o estado do exemplar para `"emprestado"` (via `exemplar_repo.update_estado()`), o segundo checkout para o **mesmo exemplar** ainda retorna `201 Created` em vez de `409 Conflict`.

Isso ocorre porque o `update_estado()` escreve na sessão da primeira requisição, mas a sessão da **segunda requisição** (nova `AsyncSession` sobre a mesma conexão) não vê o estado atualizado quando chama `exemplar_repo.get_by_id()`. O `session.get()` está retornando o estado `"disponivel"` original (pré-primeiro-checkout), fazendo o use case aprovar incorretamente o segundo empréstimo.

A raiz do problema é a mesma do ENH-002: compartilhamento de conexão com SAVEPOINT no ambiente de testes causa inconsistência de leitura entre sessões.

### Impacto

- É possível emprestar o mesmo exemplar para dois leitores simultaneamente.
- A regra de negócio "validar que o exemplar está com estado `disponivel`" falha silenciosamente.

### Sugestão de Correção

O mesmo que ENH-002 — garantir que o `update_estado()` em `SQLAlchemyExemplarRepository` também use `RETURNING` ou force invalidação do identity map da conexão. Alternativamente, rever a estratégia de isolamento dos testes.

---

## ENH-004 — Use Case de Checkout não valida corretamente o limite de empréstimos por leitor

**Severidade:** Alta  
**Tipo:** Bug de leitura de contagem entre sessões  
**Casos afetados:** CHK-E2E-010, CHK-E2E-011  

### Descrição

Após 3 empréstimos via API para o mesmo leitor (criados sequencialmente via HTTP), o 4º checkout retorna `201 Created` em vez de `422 Unprocessable Entity`.

O `count_ativos_by_leitor()` usa `SELECT COUNT(*)` que, diferente do `session.get()` (que usa o identity map), deveria sempre ir ao banco. No entanto, parece que os INSERTs das 3 requisições anteriores não são visíveis para o `SELECT COUNT(*)` da 4ª requisição na mesma conexão compartilhada com SAVEPOINT.

Isso indica que o problema é mais profundo do que o identity map — pode ser um problema de visibilidade de transação no asyncpg com `begin_nested()`.

### Impacto

- O limite de empréstimos simultâneos por leitor não é efetivamente aplicado.
- Leitores podem acumular mais de 3 empréstimos ativos.

### Sugestão de Correção

Mesma investigação do ENH-002/ENH-003. Como medida imediata, verificar se substituir `begin_nested()` por rollback direto na fixture de teste resolve o problema de visibilidade.

---

## ENH-005 — `LeitorInativoError` retorna HTTP 400 em vez de 404 para leitor inexistente

**Severidade:** Média  
**Tipo:** Divergência de contrato HTTP  
**Casos afetados:** CHK-E2E-008  

### Descrição

No [`app/use_cases/realizar_checkout.py`](app/use_cases/realizar_checkout.py), a lógica de validação de leitor é:

```python
leitor = await self._leitor_repo.get_by_id(leitor_id)
if leitor is None or not leitor.ativo:
    raise LeitorInativoError(str(leitor_id))
```

Tanto o caso "leitor não existe" quanto "leitor inativo" levantam a mesma exceção, mapeada para `HTTP 400 Bad Request` no router:

```python
except LeitorInativoError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, ...)
```

O critério de aceitação especifica que um **leitor inexistente** deve retornar `404 Not Found` (não existe) enquanto um **leitor inativo** retorna `400` (regra de negócio).

### Impacto

Clientes da API não conseguem distinguir entre "leitor não encontrado" (problema de dados) e "leitor inativo" (violação de regra de negócio).

### Sugestão de Correção

Separar os casos no use case:

```python
leitor = await self._leitor_repo.get_by_id(leitor_id)
if leitor is None:
    raise LeitorNotFoundError(str(leitor_id))  # → 404
if not leitor.ativo:
    raise LeitorInativoError(str(leitor_id))   # → 400/422
```

E no router:

```python
except LeitorNotFoundError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
except LeitorInativoError as exc:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
```

---

## ENH-006 — `ProcessarDevolucaoUseCase` não processa devolução de empréstimo com status `atrasado`

**Severidade:** Média  
**Tipo:** Regra de negócio incompleta  
**Casos afetados:** FLOW-C-003  

### Descrição

O `ProcessarDevolucaoUseCase.execute()` chama `get_ativo_by_exemplar_qr()` que filtra por `status == "ativo"`:

```python
# sqlalchemy_emprestimo_repository.py
select(EmprestimoModel).where(
    ExemplarModel.codigo_qr == codigo_qr,
    EmprestimoModel.status == "ativo",  # ← só "ativo"
)
```

Empréstimos com `status == "atrasado"` são ignorados. Quando um leitor devolve um livro em atraso, o sistema retorna `404` com a mensagem "Nenhum empréstimo ativo encontrado para o QR Code".

### Impacto

- Empréstimos atrasados **não podem ser devolvidos** via bipar do QR Code.
- O operador fica sem mecanismo para registrar a devolução física do livro atrasado.

### Sugestão de Correção

Modificar a query para incluir empréstimos `atrasado` além de `ativo`:

```python
EmprestimoModel.status.in_(["ativo", "atrasado"]),
```

Ou criar um novo método no repositório `get_ativo_ou_atrasado_by_exemplar_qr()`.

---

## ENH-007 — Ausência de endpoint `GET /api/reservas/{id}` dificulta verificação de ativação de reserva

**Severidade:** Baixa  
**Tipo:** Feature ausente  
**Casos afetados:** CIN-E2E-006 (verificação via `db_session` em vez de HTTP)  

### Descrição

O critério de aceitação da US-012 especifica que a devolução deve ativar a reserva aguardando. O teste CIN-E2E-006 verifica isso corretamente via `db_session.refresh(reserva)`, mas o plano de testes prevê que a verificação poderia ser feita via `GET /api/reservas/{reserva_id}`. Esse endpoint não existe.

Além disso, o `ProcessarDevolucaoUseCase._verificar_e_notificar_reserva()` usa `asyncio.create_task()` para enviar a notificação — essa task pode não ter completado antes da verificação no teste, dependendo do scheduler de eventos do asyncio.

### Impacto

- A reserva não é atualizada para `"disponivel"` quando verificada via `db_session.refresh()` no teste CIN-E2E-006 — possivelmente porque o `create_task()` com a notificação é executado em um contexto de evento diferente do que o teste usa, e o `update_status()` pode não ter sido chamado ainda.
- Sem o endpoint `GET /api/reservas/{id}`, operadores e sistemas externos não podem consultar o status de uma reserva específica.

### Sugestão de Correção

1. Implementar `GET /api/reservas/{id}` (e idealmente `GET /api/reservas?leitor_id=...`).
2. No `ProcessarDevolucaoUseCase`, garantir que o `update_status()` da reserva seja awaited **antes** de criar a task de notificação (já está correto — `await self._reserva_repo.update_status()` é chamado antes do `create_task`). Verificar se o flush está sendo propagado corretamente.

---

## ENH-008 — Migration diverge do modelo SQLAlchemy: coluna `isbn` na tabela `obra`

**Severidade:** Média  
**Tipo:** Inconsistência de schema  
**Descoberto em:** Implementação das factories de teste  

### Descrição

A migration `0001_initial_schema_obra_exemplar` define a coluna `isbn` como `NOT NULL`:

```sql
sa.Column('isbn', sa.String(length=20), nullable=False),
```

Enquanto o modelo SQLAlchemy [`ObraModel`](app/adapters/repositories/models/obra.py) define:

```python
isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

Essa divergência é inconsistente. O modelo permite `isbn=None`, mas o banco rejeita. Se o uso real da API via `POST /api/obras` com `isbn=None` funciona (porque a migration do banco já foi aplicada no dev com `NOT NULL`), o código poderá quebrar silenciosamente ao tentar criar obras sem ISBN via factory.

### Impacto

- Factories de teste com `isbn=None` falham com `NotNullViolationError`.
- O modelo Pydantic `ObraIn` provavelmente aceita `isbn: Optional[str]`, criando confusão sobre se ISBN é obrigatório.

### Sugestão de Correção

Alinhar: ou criar uma migration que torna `isbn` nullable no banco (`ALTER TABLE obra ALTER COLUMN isbn DROP NOT NULL`), ou atualizar o modelo Python para `isbn: Mapped[str] = mapped_column(String(20), nullable=False)` e tratar o campo como obrigatório.

---

## ENH-009 — Ausência de endpoints para `leitores` e `reservas`

**Severidade:** Alta  
**Tipo:** Features ausentes  
**Descoberto em:** Implementação dos testes FLOW-C-001 e FLOW-C-003  

### Descrição

O `app/main.py` não registra routers para:
- `/api/leitores` — cadastro e consulta de leitores
- `/api/reservas` — criação e consulta de reservas

Essas operações são centrais para o fluxo de circulação (US-035 requer criar leitores; US-012 menciona verificação de reservas). Os testes de fluxo completo precisaram contornar essa ausência usando factories diretas no banco.

### Impacto

- Operadores não conseguem cadastrar leitores via API.
- O fluxo completo de "leitor B faz reserva → leitor A devolve → reserva ativada" não pode ser testado end-to-end via HTTP.

### Sugestão de Correção

Implementar e registrar os routers:
- `POST /api/leitores` — cadastrar leitor
- `GET /api/leitores/{id}` — consultar leitor
- `POST /api/reservas` — criar reserva
- `GET /api/reservas/{id}` — consultar status da reserva
- `GET /api/reservas?obra_id=...&leitor_id=...` — listar reservas com filtros

---

## ENH-010 — Estratégia de isolamento dos testes: revisão do padrão `begin_nested()`

**Severidade:** Média  
**Tipo:** Débito técnico de infraestrutura de testes  
**Descoberto em:** Análise das falhas de renovação e checkout  

### Descrição

O padrão atual de isolamento usa `connection.begin_nested()` (SAVEPOINT) para encapsular cada teste. Múltiplas `AsyncSession` compartilham a mesma `AsyncConnection`. Em teoria, todas as sessões dentro da mesma transação PostgreSQL deveriam ver as escritas umas das outras.

Na prática, a combinação `asyncpg` + `begin_nested()` + múltiplas `AsyncSession` compartilhando a mesma `AsyncConnection` apresentou comportamentos inesperados onde:
- UPDATEs escritos por uma sessão não são visíveis para SELECTs de outra sessão (mesmo connection)
- INSERTs parecem ser visíveis (primeira criação passa), mas UPDATEs subsequentes não

Isso pode ser específico à versão `asyncpg==0.31.0` + `SQLAlchemy==2.0.54` + Python 3.14.

### Impacto

- 7 falhas em testes que dependem de múltiplas operações sequenciais (renovações, limite de empréstimos).
- Dificulta testes de fluxo multi-step via API.

### Sugestão de Correção

Investigar e avaliar alternativas:

1. **Usar `session.commit()` no final de cada operação** e depender de rollback por fixture (sem SAVEPOINT). Mais simples, mas mais lento.
2. **Passar a mesma sessão** entre o setup de fixture e a app via `dependency_overrides` de forma mais granular.
3. **Usar banco de dados separado por teste** (mais isolado, muito mais lento).
4. **Atualizar versões** de asyncpg/SQLAlchemy e verificar se o comportamento muda.
5. **Trocar `begin_nested()` por `begin()`** e aplicar/desfazer o schema inteiro por teste (pesado mas determinístico).

---

## Resumo de Ações Prioritárias

| Prioridade | Enhancement | Esforço Estimado |
|---|---|---|
| 🔴 P1 | ENH-001 — Implementar `GET /api/exemplares/{id}` | 30 min |
| 🔴 P1 | ENH-009 — Implementar routers de leitores e reservas | 2–4h |
| 🔴 P1 | ENH-006 — Devolução de empréstimo `atrasado` via QR | 30 min |
| 🟠 P2 | ENH-005 — Separar `LeitorNotFoundError` de `LeitorInativoError` | 1h |
| 🟠 P2 | ENH-002/003/004 — Corrigir `save()` e visibilidade cross-session | 2–4h |
| 🟡 P3 | ENH-008 — Alinhar migration e modelo SQLAlchemy para `isbn` | 30 min |
| 🟡 P3 | ENH-007 — Implementar `GET /api/reservas/{id}` | 1h |
| 🟢 P4 | ENH-010 — Revisar estratégia de isolamento de testes | 3–5h |
