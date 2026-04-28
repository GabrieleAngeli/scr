# SCR PoC — Codex Implementation Pack

> Target: implementare un PoC verificabile del **Segregated Competence Runtime (SCR)** partendo dai requisiti già definiti in `SCR_POC_REQUIREMENTS.md`.
>
> Dominio iniziale: **micro bug fixing Python** con struttura `task/bug.py`, `test_bug.py`, `meta.txt`.

---

## 1. Obiettivo del task per Codex

Implementare un runtime Python minimale ma reale in cui:

1. un task viene trasformato in un **campo condiviso**;
2. più unità di competenza osservano il campo;
3. ogni unità decide se attivarsi in base a soglia, sensibilità, energia e tensione;
4. le unità non si chiamano tra loro e non scambiano DTO diretti;
5. ogni unità produce solo una trasformazione del campo (`FieldDelta`);
6. il runtime applica i delta, aggiorna lo stato e avanza a tick;
7. vengono generate almeno 3 ipotesi divergenti;
8. le ipotesi competono prima della validazione reale;
9. la validazione usa `pytest`, `ast` o parser reali;
10. l'esito viene consolidato, tracciato e salvato per replay/learning.

Il PoC non deve dimostrare AGI. Deve dimostrare un **modello computazionale verificabile**.

---

## 2. Vincoli architetturali non negoziabili

### 2.1 Le unità non sono microservizi

Non implementare:

- REST API tra unità;
- code/event bus tra unità;
- DTO unit-to-unit;
- orchestrazione diretta tipo pipeline fissa.

Ogni unità deve rispettare questo contratto:

```python
Field -> FieldDelta
```

### 2.2 Comunicazione solo tramite campo

Le unità possono:

- leggere `FieldState`;
- produrre `FieldDelta`;
- aggiungere eventi al trace;
- proporre, rafforzare, indebolire o rimuovere ipotesi.

Le unità non possono:

- chiamare altre unità;
- leggere memoria privata di altre unità;
- modificare direttamente il campo senza passare da `FieldDelta`;
- validare modifiche fuori dal runtime.

### 2.3 Learning non end-to-end

Per il PoC evitare training neurale globale.

Implementare invece:

- V0: parametri statici configurabili;
- V1: adaptive tuning semplice su soglie, pesi e decay;
- salvataggio episodi per replay;
- attribution locale dei reward.

---

## 3. Struttura repository attesa

Creare o adeguare questa struttura:

```text
scr-demo/
  pyproject.toml
  README.md
  src/
    scr/
      __init__.py
      field.py
      delta.py
      runtime.py
      trace.py
      validation.py
      learning.py
      replay.py
      baseline.py
      units/
        __init__.py
        base.py
        input_structuring.py
        standardization.py
        divergence.py
        competition.py
        validation_gate.py
        consolidation.py
  tasks/
    task_001/
      bug.py
      test_bug.py
      meta.txt
  tests/
    test_field_delta.py
    test_runtime_tick.py
    test_divergence.py
    test_competition.py
    test_validation.py
    test_replay.py
    test_learning.py
```

---

## 4. Data model minimo

### 4.1 FieldState

Implementare in `src/scr/field.py`:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class FieldState:
    task_signal: dict[str, Any]
    context_map: dict[str, Any] = field(default_factory=dict)
    salience_map: dict[str, float] = field(default_factory=dict)
    hypothesis_pool: list[dict[str, Any]] = field(default_factory=list)
    energy_map: dict[str, float] = field(default_factory=dict)
    tension_map: dict[str, float] = field(default_factory=dict)
    stability_score: float = 1.0
    activation_levels: dict[str, float] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    tick: int = 0
```

### 4.2 FieldDelta

Implementare in `src/scr/delta.py`:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class FieldDelta:
    source_unit: str
    salience_updates: dict[str, float] = field(default_factory=dict)
    tension_updates: dict[str, float] = field(default_factory=dict)
    energy_updates: dict[str, float] = field(default_factory=dict)
    hypotheses_add: list[dict[str, Any]] = field(default_factory=list)
    hypotheses_remove: list[str] = field(default_factory=list)
    context_updates: dict[str, Any] = field(default_factory=dict)
    stability_shift: float = 0.0
    trace_events: list[dict[str, Any]] = field(default_factory=list)
```

### 4.3 Hypothesis

Usare dizionari serializzabili per il PoC:

```python
{
    "id": "hyp-001",
    "origin_unit": "divergence",
    "description": "Replace wrong operator",
    "patch": "...",
    "score": 0.42,
    "energy": 0.8,
    "tension": 0.1,
    "status": "candidate"
}
```

Stati ammessi:

```text
candidate | pruned | validating | valid | invalid | consolidated
```

---

## 5. Unità di competenza richieste

### 5.1 Base interface

Implementare in `src/scr/units/base.py`:

```python
from abc import ABC, abstractmethod
from scr.field import FieldState
from scr.delta import FieldDelta

class CompetenceUnit(ABC):
    name: str
    threshold: float
    sensitivity: float
    weight: float
    decay: float

    @abstractmethod
    def activation(self, field: FieldState) -> float:
        pass

    @abstractmethod
    def transform(self, field: FieldState) -> FieldDelta:
        pass
```

### 5.2 InputStructuringUnit

Responsabilità:

- leggere `task_signal`;
- estrarre nomi file;
- estrarre errore atteso da `meta.txt`, se presente;
- popolare `context_map`.

Output:

- `context_updates`;
- salience su `code`, `tests`, `failure_signal`.

### 5.3 StandardizationUnit

Responsabilità:

- normalizzare task;
- parse AST del file `bug.py`;
- identificare funzioni/classi/moduli;
- estrarre failure hints.

Output:

- `context_map["ast_summary"]`;
- `context_map["symbols"]`;
- aumento salience su regioni sospette.

### 5.4 DivergenceUnit

Responsabilità:

- generare almeno 3 ipotesi diverse;
- ogni ipotesi deve avere patch o strategia distinta;
- evitare duplicati troppo simili.

Esempi di ipotesi:

- fix operatore errato;
- fix boundary condition;
- fix tipo/None handling;
- fix nome variabile;
- fix return value.

### 5.5 CompetitionUnit

Responsabilità:

- assegnare score alle ipotesi;
- penalizzare ipotesi duplicate;
- fare pruning prima della validazione;
- mantenere almeno una candidata se possibile.

### 5.6 ValidationGateUnit

Responsabilità:

- selezionare ipotesi validate-ready;
- applicare patch in workspace temporaneo;
- eseguire `pytest`;
- aggiornare stato ipotesi.

Questa unità non deve consolidare il risultato finale. Deve solo validare.

### 5.7 ConsolidationUnit

Responsabilità:

- scegliere ipotesi valida migliore;
- produrre outcome finale;
- registrare metriche;
- salvare episodio.

---

## 6. Runtime a tick

Implementare in `src/scr/runtime.py`.

Loop richiesto:

```python
while not stop_condition:
    observe_field()
    compute_activations()
    select_active_units()
    collect_deltas()
    apply_deltas()
    update_energy_tension_stability()
    append_trace()
    maybe_validate()
    maybe_consolidate()
```

Il runtime deve produrre esiti espliciti:

```text
SUCCESS
REOPENED
FAILED_NO_VALID_HYPOTHESIS
FAILED_TIMEOUT
FAILED_UNSTABLE_FIELD
FAILED_VALIDATION
```

---

## 7. Learning layer V0/V1

Implementare in `src/scr/learning.py`.

### 7.1 Parametri apprendibili per unità

Ogni unità deve avere:

```python
{
    "threshold": 0.5,
    "sensitivity": 1.0,
    "weight": 1.0,
    "decay": 0.05
}
```

### 7.2 Reward assignment

Reward minimo:

```text
+1.0  ipotesi validata con successo
+0.3  pruning corretto prima della validazione
-0.5  validazione sprecata
-0.3  aumento instabilità campo
-1.0  fallimento per timeout o campo instabile
```

### 7.3 Update rule semplice

Implementare adaptive tuning:

```python
new_value = old_value + learning_rate * reward * influence
```

Applicare clamp:

```python
threshold:   0.05..0.95
sensitivity: 0.10..5.00
weight:      0.10..5.00
decay:       0.00..0.50
```

### 7.4 Anti-collasso

Implementare almeno:

- penalità per uso eccessivo di una singola unità;
- limite massimo di activation consecutiva;
- diversity check sulle ipotesi;
- nessun update se il trace non contiene attribution sufficiente.

---

## 8. Replay

Implementare in `src/scr/replay.py`.

Ogni run deve salvare:

```json
{
  "run_id": "...",
  "task_id": "...",
  "initial_field": {},
  "ticks": [],
  "final_field": {},
  "outcome": "SUCCESS",
  "metrics": {},
  "learning_updates": []
}
```

Il replay deve poter:

- rileggere una run;
- ricostruire i tick;
- confrontare final field e outcome;
- usare gli episodi come base per learning successivo.

---

## 9. Baseline lineare

Implementare in `src/scr/baseline.py`.

Baseline minima:

```text
input -> parse -> single hypothesis -> pytest -> success/failure
```

Metriche di confronto:

- success rate;
- false positives;
- tick medi;
- costo stimato;
- numero validazioni;
- riaperture utili.

---

## 10. Test richiesti

Implementare test Pytest per verificare:

1. `FieldDelta` viene applicato correttamente;
2. le unità non modificano direttamente il campo;
3. il runtime avanza a tick;
4. divergence genera almeno 3 ipotesi;
5. competition fa pruning prima della validation;
6. validation usa realmente `pytest`;
7. consolidation produce esito esplicito;
8. replay salva e rilegge una run;
9. learning aggiorna parametri con clamp;
10. anti-collasso impedisce dominanza singola.

---

## 11. Definition of Done

Il lavoro è completo solo se:

- `pytest` passa;
- esistono almeno 10 task demo;
- almeno una run produce `SUCCESS`;
- almeno una run produce fallimento esplicito;
- il trace mostra chi si è attivato, perché e con quale delta;
- il replay è serializzato su file;
- esiste confronto baseline vs SCR;
- il README spiega come lanciare demo e test.

---

## 12. Comandi attesi

```bash
python -m pytest
python -m scr.runtime --task tasks/task_001
python -m scr.baseline --task tasks/task_001
```

Se il packaging non supporta ancora `python -m scr.runtime`, creare CLI minimale o script equivalente documentato nel README.

---

## 13. Note operative per Codex

- Procedere in piccoli commit logici.
- Non introdurre framework pesanti.
- Non usare LLM esterne nel PoC V0/V1.
- Privilegiare codice leggibile, serializzabile e testabile.
- Se una scelta è ambigua, seguire l'ADR `ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md`.
- Non ottimizzare prematuramente.
- La priorità è rendere verificabile la dinamica: field, unit, delta, tick, trace, replay, learning.
