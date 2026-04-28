# SCR V0 Architecture

## Goal

Tradurre i requisiti del PoC SCR in un'architettura minima implementabile, mantenendo fuori scope il learning adattivo ma preservando hook e trace per introdurlo dopo.

## V0 Scope

- Dominio: micro bug fixing Python
- Input per task: `bug.py`, `test_bug.py`, `meta.txt`
- Runtime stateful a tick
- Multi-ipotesi con pruning prima della validation
- Validation reale tramite `pytest`
- Consolidation o fallimento esplicito
- Benchmark contro baseline lineare

## Core Concepts

### Field

Oggetto mutabile condiviso da tutte le unit.

Campi minimi:

- `task_signal`
- `context_map`
- `salience_map`
- `hypothesis_pool`
- `energy_map`
- `tension_map`
- `stability_score`
- `activation_levels`
- `trace`
- `tick`
- `status`

### Unit

Operatore che osserva il campo e, se attivato, lo deforma.

Interfaccia minima:

- `name`
- `threshold`
- `sensitivity`
- `decay`
- `observe(field) -> ActivationDecision`
- `apply(field) -> None`

### Hypothesis

Rappresenta una possibile correzione del bug.

Campi minimi:

- `id`
- `summary`
- `patch`
- `score`
- `origin_unit`
- `state`
- `validation_result`

### Runtime

Esegue cicli a tick:

1. osservazione del campo
2. attivazione selettiva delle unit
3. trasformazione del campo
4. aggiornamento stabilita/energia/tensione
5. pruning o validation quando necessario
6. consolidamento o riapertura

## Units Planned For V0

- `InputStructuringUnit`
- `StandardizationUnit`
- `DivergenceUnit`
- `CompetitionUnit`
- `ValidationUnit`
- `ConsolidationUnit`

## Status Model

- `PENDING`
- `RUNNING`
- `SUCCESS`
- `REOPENED`
- `FAILED_NO_VALID_HYPOTHESIS`
- `FAILED_TIMEOUT`
- `FAILED_UNSTABLE_FIELD`
- `FAILED_VALIDATION`

## Stability Heuristic For V0

Definizione pragmatica iniziale:

- stabilita alta quando le attivazioni convergono, il numero di ipotesi scende e la tensione cala
- instabilita quando il campo continua a oscillare senza migliorare ranking, validation o pruning

Possibile criterio iniziale di fail:

- `tick >= max_ticks`
- nessuna ipotesi promossa
- tensione media sopra soglia per `n` tick consecutivi

## Competition Strategy For V0

Ranking euristico con punteggio combinato:

- rilevanza rispetto al failure parsing
- coerenza con il file e il contesto
- costo stimato della patch
- novita rispetto ad altre ipotesi

Solo le top `k` ipotesi passano a validation.

## Validation Strategy For V0

- materializzare patch in workspace temporaneo
- eseguire `pytest` sul task
- salvare esito, output e costo nel trace

## Consolidation Strategy For V0

- se una ipotesi passa, diventa soluzione consolidata
- se tutte falliscono ma ci sono segnali utili, runtime puo riaprire
- se non restano ipotesi utili, fallimento esplicito

## Baseline

Pipeline lineare senza campo dinamico:

1. parse input
2. genera una o poche ipotesi
3. valida in ordine fisso
4. ritorna il primo successo o il fallimento

## Proposed Layout

```text
SCR/
  .context/
  src/
    scr/
      __init__.py
      models.py
      runtime.py
      validator.py
      units/
        __init__.py
        base.py
        input_structuring.py
        standardization.py
        divergence.py
        competition.py
        validation.py
        consolidation.py
  tasks/
  tests/
```
