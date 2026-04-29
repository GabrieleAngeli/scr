# Rapporto tecnico sul gating SCR

## Sintesi esecutiva

Il punto principale emerso dall’analisi è netto: **il problema oggi non è più `src/scr/runtime.py`**, perché nel codice ispezionato il runtime implementa già il pattern corretto **una sola unità per tick** tramite `ActivationPolicy.select_next_unit(...)`. Il vero collo di bottiglia è invece **il benchmark**, che continua a usare `_run_scr()` come **pipeline di sei runtime separati a unità singola**, partendo ogni volta da un `FieldState` vuoto. In questa configurazione, su `task_001`, vedere **6 tick** e **tutte le 6 competenze attivate** è atteso, non è la prova che il gating abbia fallito. fileciteturn0file0 fileciteturn0file4

I benchmark caricati sono coerenti tra loro: **BASELINE vince** con `efficiency_score = 0.8333`, mentre **SCR resta a 0.3125**, con `resource_cost_score = 3.2`, `ticks = 6`, `activated_competences = 6` e `storage_footprint_estimate` nell’intervallo ~10.7k–12.1k byte, a seconda del run. Questo conferma che, **sul task fresco e lineare**, SCR paga tutto il costo della pipeline, mentre la baseline beneficia del caso semplice. fileciteturn0file0 fileciteturn0file4

La conclusione ingegneristica corretta è quindi questa:

1. **Il gating è presente nel runtime**.
2. **Il benchmark attuale non lo misura nel punto giusto**.
3. **Il prossimo step non è riscrivere ancora il loop del runtime**, ma:
   - mettere sotto test il gating su **FieldState parzialmente popolati**;
   - correggere **`BenchmarkRunner._run_scr()`** o introdurre un percorso benchmark separato che faccia emergere i benefici del gating;
   - esplicitare che su `task_001` “fresh-from-zero” il post-patch **potrebbe non cambiare quasi nulla**, perché tutte le fasi servono davvero.

## Verifica dello stato attuale

Dal tuo output Git ufficiale il repository locale risulta **sano e pulito**:

- branch: `main`
- branch allineato a `origin/main`
- nessun tracked change in working tree
- unico file non tracciato: `SCR.7z`
- `git diff --stat` vuoto

Questa è la fonte più autorevole sulla pulizia del repository locale. È importante notare che il contenuto del pacchetto `SCR.7z` che ho ispezionato **non coincide perfettamente con quello stato Git pulito**: l’archivio contiene una working tree e un `.git` interni che, se riestratti separatamente, mostrano modifiche non committate. Per l’analisi funzionale del codice ho usato l’archivio; per lo stato ufficiale del progetto ho preso come riferimento il tuo `git status` incollato in chat.

La struttura file che hai riportato conferma che il progetto è completo nei punti critici:

- `src/scr/` contiene `application_benchmark.py`, `baseline.py`, `benchmark.py`, `delta.py`, `field.py`, `learning.py`, `replay.py`, `runtime.py`
- `src/scr/units/` contiene `base.py`, `competition.py`, `consolidation.py`, `divergence.py`, `input_structuring.py`, `standardization.py`, `validation.py`
- `tests/` contiene, tra gli altri, `test_benchmark.py`, `test_application_thread_benchmark.py`, `test_runtime_activation_policy.py`

Nel codice ispezionato ho verificato inoltre che la suite contiene **79 test raccolti**, e che il file critico `tests/test_runtime_activation_policy.py` contiene **5 test**. In esecuzione locale sulla snapshot dell’archivio, i due test più significativi e “pesanti” del gating (`test_tick_count_is_not_greater_than_units_really_needed` e `test_trace_shows_sequential_activation`) passano; nella stessa snapshot, l’esecuzione del file mostrava anche i primi tre test già in stato `PASSED` prima del completamento. Questo mi consente di affermare con buona confidenza che **la suite specifica del gating è 5/5 sulla snapshot ispezionata**. Non ho però una prova completa, nello spazio di questo report, dell’intera suite 79/79.

Sul comportamento runtime ho verificato dinamicamente questi casi:

- **campo fresco** → `6` tick, unità selezionate in sequenza:
  `input_structuring → standardization → divergence → competition → validation → consolidation`
- **campo già dopo input structuring** → `5` tick
- **campo già dopo standardization** → `4` tick
- **campo già dopo divergence** → `3` tick
- **campo già dopo competition** → `2` tick
- **campo già dopo validation** → `1` tick
- **campo con `outcome` già definito** → `0` tick

Questo dimostra che **il runtime scala effettivamente in funzione dello stato del campo**. Il fatto che il benchmark caricato mostri sempre `6` tick deriva dal modo in cui il benchmark costruisce ed esegue SCR, non dall’assenza di gating nel runtime. I file benchmark caricati mostrano infatti stabilmente `scr_ticks = 6`, `activated_competences = 6`, `resource_cost_score = 3.2`, `efficiency_score = 0.3125`, con baseline a `0.8333`. fileciteturn0file0 fileciteturn0file4

## Analisi statica del runtime e della vera causa

### Situazione reale di `src/scr/runtime.py`

Nel codice ispezionato, `src/scr/runtime.py` **implementa già** il modello corretto “single-unit-per-tick”.

Le sezioni rilevanti sono queste:

- **`ActivationPolicy.select_next_unit`**: righe **15–20**
- **`ActivationPolicy._select_unit_name`**: righe **23–42**
- **`SCRRuntime.run`**: righe **55–66**
- **`SCRRuntime.run_tick`**: righe **68–119**

La logica è:

- `SCRRuntime.run()` entra in un `while True`
- interrompe su:
  - `field.outcome is not None`
  - `field.tick >= self.config.max_ticks`
  - `selected_unit is None`
- per ogni iterazione:
  - seleziona **una sola** unità con `self.activation_policy.select_next_unit(...)`
  - incrementa `field.tick`
  - esegue `run_tick(field, selected_unit)`

Dentro `run_tick()`, il runtime:

- scrive l’evento `tick_start`
- scrive l’evento `activation_policy` con `changes["selected_unit"]`
- calcola l’attivazione **della sola unità selezionata**
- se sotto soglia, emette `unit_skipped`
- altrimenti chiama `selected_unit.transform(field)` e applica il delta

Il dato più importante è questo: **non c’è più nessun `for unit in self.units` nel percorso esecutivo del tick**. La vecchia forma pipeline-wide non è presente nella snapshot analizzata.

### Dove si trova il problema vero

Il punto che oggi falsifica il benchmark è **`src/scr/benchmark.py`**, non `runtime.py`.

La sezione problematica è:

- **`BenchmarkRunner._run_scr`**: righe **58–77**

Lì il benchmark fa questo:

- crea un `FieldState` vuoto
- istanzia:
  - `SCRRuntime(units=[InputStructuringUnit()])`
  - `SCRRuntime(units=[StandardizationUnit()])`
  - `SCRRuntime(units=[DivergenceUnit()])`
  - `SCRRuntime(units=[CompetitionUnit()])`
  - `SCRRuntime(units=[ValidationUnit()])`
  - `SCRRuntime(units=[ConsolidationUnit()])`
- li esegue **in serie**, uno dopo l’altro

Architetturalmente questo significa che il benchmark non sta misurando “un runtime che decide dinamicamente cosa attivare tra sei competenze”, ma una **composizione manuale di sei runtime monofase**.

Conseguenze:

- su un task fresco, `task_001`, **6 tick sono normali**
- il benchmark **non può dimostrare** la riduzione tick del gating su un thread già parzialmente lavorato
- le metriche `activated_competences` e `ticks` del benchmark restano confinate a uno scenario “from scratch”

C’è un secondo punto importante in:

- **`src/scr/application_benchmark.py`**: riga **48**

Questa classe richiama direttamente `BenchmarkRunner._run_scr(...)`, quindi **eredita lo stesso bias**.

### Linee da cambiare

Se la domanda è “dove devo intervenire adesso?”, la risposta è:

- **non prioritariamente in `runtime.py`** per il loop
- **sicuramente in `benchmark.py`**:
  - `BenchmarkRunner._run_scr`, righe **58–77**
- **di riflesso in `application_benchmark.py`**:
  - `ApplicationThreadBenchmark.run`, attorno alla riga **48**
- **nei test benchmark**:
  - `tests/test_benchmark.py`
  - `tests/test_application_thread_benchmark.py`

C’è anche un caveat importante in `runtime.py`:

- **`RuntimeConfig.max_ticks = 1`** alla riga **12**

Questo non è un bug nel runtime attuale, perché molti chiamanti passano `max_ticks` esplicitamente. Ma se in futuro colleghi il benchmark a un **singolo runtime con tutte le unità** e dimentichi di impostare `max_ticks >= 6`, il run si fermerà al primo tick. Quindi o:
- lasci il default a `1` ma **imponi** `max_ticks` espliciti nei chiamanti benchmark;
- oppure alzi il default solo per i percorsi benchmark, non globalmente.

## Piano di test dinamico

La suite esistente del gating è buona, ma non basta ancora per dimostrare il valore applicativo. Serve una batteria di test molto più deterministica e leggibile, esplicitamente centrata sulla **riduzione dei tick al crescere della preformazione del campo**.

### Test da aggiungere subito

#### `test_gating_fresh_field_requires_full_chain`

**Input**

- `FieldState(task_signal={"task_id": "task_001", "task_path": ...})`
- campo vuoto
- runtime con tutte le 6 unità
- `max_ticks=10`

**Atteso**

- `result.tick == 6`
- sequenza selezioni:
  `["input_structuring", "standardization", "divergence", "competition", "validation", "consolidation"]`
- nessun `unit_skipped`

**Assertion**

```python
assert result.tick == 6
assert selected_units == [
    "input_structuring",
    "standardization",
    "divergence",
    "competition",
    "validation",
    "consolidation",
]
assert not skipped_events
```

#### `test_gating_skips_input_structuring_when_context_is_preloaded`

**Input**

Campo già popolato come output di `InputStructuringUnit`:

- `context_map["files"]`
- `context_map["artifacts"]`
- `context_map["expected_failure"]`
- `task_id`, `task_path`

**Atteso**

- `result.tick == 5`
- prima unità selezionata: `standardization`
- `input_structuring` assente dalla selezione

**Assertion**

```python
assert result.tick == 5
assert selected_units[0] == "standardization"
assert "input_structuring" not in selected_units
```

#### `test_gating_skips_standardization_when_normalized_artifacts_exist`

**Input**

Campo già popolato come output di `StandardizationUnit`:

- `normalized_artifacts`
- `code_artifact`
- `test_artifact`
- `metadata_artifact`
- più i campi derivati da input structuring

**Atteso**

- `result.tick == 4`
- sequenza:
  `["divergence", "competition", "validation", "consolidation"]`

**Assertion**

```python
assert result.tick == 4
assert selected_units == [
    "divergence",
    "competition",
    "validation",
    "consolidation",
]
```

#### `test_gating_skips_divergence_when_hypothesis_pool_already_exists`

**Input**

Campo con:

- contesto standardizzato completo
- `hypothesis_pool` già presente

**Atteso**

- `result.tick == 3`
- sequenza:
  `["competition", "validation", "consolidation"]`

**Assertion**

```python
assert result.tick == 3
assert selected_units == ["competition", "validation", "consolidation"]
```

#### `test_gating_goes_directly_to_validation_when_active_hypotheses_exist`

**Input**

Campo con:

- contesto standardizzato completo
- `hypothesis_pool` già classificato
- `context_map["active_hypotheses"]` presente
- `validation_results` assente

**Atteso**

- `result.tick == 2`
- sequenza:
  `["validation", "consolidation"]`

**Assertion**

```python
assert result.tick == 2
assert selected_units == ["validation", "consolidation"]
```

#### `test_gating_goes_directly_to_consolidation_when_validation_results_exist`

**Input**

Campo con:

- `validation_results` presente
- `hypothesis_pool` presente
- `outcome` assente

**Atteso**

- `result.tick == 1`
- sequenza:
  `["consolidation"]`

**Assertion**

```python
assert result.tick == 1
assert selected_units == ["consolidation"]
```

#### `test_runtime_stops_immediately_when_outcome_is_already_defined`

**Input**

Campo con:

- `field.outcome = "SUCCESS"`

**Atteso**

- `result.tick == 0`
- nessun evento `activation_policy`

**Assertion**

```python
assert result.tick == 0
assert not policy_events
```

### Test benchmark da aggiungere

Qui c’è il controllo più importante dell’intero progetto.

#### `test_benchmark_run_scr_can_show_tick_reduction_on_prepopulated_field`

Se scegli di introdurre un `_run_scr(field=optional_field)` o un benchmark helper specifico, questo test deve dimostrare che:

- su campo fresco: `ticks == 6`
- su campo già dopo input structuring: `ticks == 5`
- su campo già dopo standardization: `ticks == 4`

Questo test è più importante di molti test unitari “fine-grained”, perché impedisce future regressioni concettuali del benchmark.

#### `test_application_thread_benchmark_reflects_prepopulated_thread_state`

Dato che `ApplicationThreadBenchmark` dovrebbe misurare thread applicativi, non task appena nati, va verificato che:

- un thread “ripreso” o “parzialmente strutturato” produca meno tick
- `activated_competences` rifletta solo le unità davvero passate
- `resource_cost_score` scenda di conseguenza

## Patch minima e sicurezza regressiva

### Patch minima realmente necessaria

Poiché il pattern corretto è già presente in `runtime.py`, la patch minima da fare **oggi** non è la sostituzione del loop del runtime, ma il **rewiring del benchmark**.

La modifica minima è in `src/scr/benchmark.py`.

### Diff consigliato per `benchmark.py`

```diff
diff --git a/src/scr/benchmark.py b/src/scr/benchmark.py
@@
     @staticmethod
     def _run_scr(task_dir: Path, task_id: str) -> tuple[FieldState, float]:
-        field = FieldState(task_signal={"task_id": task_id, "task_path": str(task_dir)})
-        input_runtime = SCRRuntime(units=[InputStructuringUnit()])
-        standardization_runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))
-        divergence_runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))
-        competition_runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))
-        validation_runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))
-        consolidation_runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))
-
-        field = input_runtime.run(field)
-        field = standardization_runtime.run(field)
-        field = divergence_runtime.run(field)
-        field = competition_runtime.run(field)
-
-        validation_start = time.perf_counter()
-        field = validation_runtime.run(field)
-        validation_time_ms = round((time.perf_counter() - validation_start) * 1000, 3)
-
-        field = consolidation_runtime.run(field)
-        return field, validation_time_ms
+        field = FieldState(task_signal={"task_id": task_id, "task_path": str(task_dir)})
+        runtime = SCRRuntime(
+            units=[
+                InputStructuringUnit(),
+                StandardizationUnit(),
+                DivergenceUnit(),
+                CompetitionUnit(),
+                ValidationUnit(),
+                ConsolidationUnit(),
+            ],
+            config=RuntimeConfig(max_ticks=10),
+        )
+
+        run_start = time.perf_counter()
+        field = runtime.run(field)
+        validation_time_ms = round((time.perf_counter() - run_start) * 1000, 3)
+        return field, validation_time_ms
```

### Osservazione importante sulla semantica di `validation_time_ms`

Questa patch è minima ma introduce una tensione semantica: il campo `validation_time_ms` non misura più solo la validazione, bensì l’intero runtime SCR.

Se vuoi **preservare** davvero il significato del nome, hai due strade:

- **strada rapida**: accetti temporaneamente la metrica come “runtime_time_ms” mantenendo il nome storico per compatibilità, e lo documenti;
- **strada corretta**: aggiungi una strumentazione benchmark-side che misuri davvero il tempo della sola `ValidationUnit`, senza cambiare l’interfaccia delle unità.

La mia raccomandazione pratica è:

- in questa iterazione: **non rompere il formato JSON esistente**
- aggiungi invece un nuovo campo:
  - `scr_runtime_time_ms`
- lascia `validation_time_ms` invariato finché non lo puoi misurare correttamente

### Diff opzionale per evitare ambiguità

```diff
diff --git a/src/scr/benchmark.py b/src/scr/benchmark.py
@@
-        scr_field, scr_validation_time_ms = self._run_scr(task_dir, task_id)
+        scr_field, scr_runtime_time_ms = self._run_scr(task_dir, task_id)
@@
-            "scr_validation_time_ms": scr_validation_time_ms,
+            "scr_validation_time_ms": scr_runtime_time_ms,
@@
-        scr_result = self._build_scr_result(scr_field, scr_validation_time_ms)
+        scr_result = self._build_scr_result(scr_field, scr_runtime_time_ms)
```

### Canonical loop del runtime

Per completezza: se in un branch secondario esistesse ancora la vecchia forma pipeline, la sostituzione corretta resterebbe questa. Nella snapshot ispezionata, però, è **già presente**.

```diff
- while field.tick < self.config.max_ticks:
-     field.tick += 1
-     active_deltas = self.run_tick(field)
-     if field.outcome is not None or not active_deltas:
-         break
+ while True:
+     if field.outcome is not None:
+         break
+     if field.tick >= self.config.max_ticks:
+         break
+     selected_unit = self.activation_policy.select_next_unit(field, self.unit_by_name)
+     if selected_unit is None:
+         break
+     field.tick += 1
+     self.run_tick(field, selected_unit)
```

### Procedura sicurezza regressiva

Comandi consigliati prima e dopo la patch:

```bash
git status
git diff --stat
git ls-files --deleted
python -m pytest --collect-only -q | tail -1
```

Dopo la patch:

```bash
git diff --stat
git diff -- src/scr/runtime.py src/scr/benchmark.py src/scr/application_benchmark.py tests/test_runtime_activation_policy.py tests/test_benchmark.py tests/test_application_thread_benchmark.py
git ls-files --deleted
```

La sequenza pytest da usare, in ordine:

```bash
python -m pytest -q tests/test_runtime_activation_policy.py
python -m pytest -q tests/test_benchmark.py
python -m pytest -q tests/test_application_thread_benchmark.py
python -m pytest -q
```

Controlli minimi di sicurezza:

- `git ls-files --deleted` deve restituire **vuoto**
- `git diff --stat` deve mostrare solo i file attesi
- nessun file in `src/scr/units/` deve sparire o cambiare interfaccia
- il formato trace deve rimanere compatibile:
  - `tick_start`
  - `activation_policy`
  - `unit_skipped` opzionale
  - `unit_delta_applied`

## Piano di benchmark e tabelle comparative

### Cosa misurano oggi i benchmark caricati

I benchmark caricati mostrano una situazione stabile:

- **Baseline**
  - `activated_competences = ["baseline_runner"]`
  - `resource_cost_score = 1.2`
  - `storage_footprint_estimate = 393`
  - `efficiency_score = 0.8333`
- **SCR**
  - `ticks = 6`
  - `activated_competences = 6`
  - `resource_cost_score = 3.2`
  - `efficiency_score = 0.3125`
  - `storage_footprint_estimate` variabile tra circa `10736` e `12118`
- vincitore: `BASELINE` fileciteturn0file0 fileciteturn0file4

### Tabella attuale

| Variante | ticks | activated_competences_count | resource_cost | storage_footprint | efficiency |
|---|---:|---:|---:|---:|---:|
| Baseline attuale | — | 1 | 1.2 | 393 | 0.8333 |
| SCR attuale su `task_001` fresh | 6 | 6 | 3.2 | 10736–12118 | 0.3125 |

Valori tratti dai benchmark caricati. fileciteturn0file0 fileciteturn0file4

### Tabella attesa dopo il rewiring del benchmark sullo stesso `task_001` fresh

Qui va detta una verità controintuitiva ma importante: **sullo stesso `task_001`, partendo da zero, non mi aspetto un miglioramento significativo**.

| Variante | ticks | activated_competences_count | resource_cost | storage_footprint | efficiency |
|---|---:|---:|---:|---:|---:|
| Baseline post-patch | — | 1 | 1.2 | 393 | 0.8333 |
| SCR post-patch su `task_001` fresh | ~6 | ~6 | ~3.2 | ~invariato | ~0.3125 |

Perché? Perché nel task fresco tutte le fasi sono davvero necessarie. Quindi il valore del gating **non emerge qui**.

### Dove il gating inizia davvero a produrre valore

Usando il runtime corretto con `FieldState` parzialmente popolati, il costo teorico secondo la formula benchmark attuale scende così:

`resource_cost_score = 1.0 + tick*0.15 + validated_hypothesis_count*0.35 + activated_competences_count*0.1`

Assumendo `quality_score = 1.0` e due ipotesi validate, il quadro diventa:

| Stato del campo SCR | ticks | activated_competences_count | resource_cost | efficiency |
|---|---:|---:|---:|---:|
| Fresh | 6 | 6 | 3.20 | 0.3125 |
| Dopo input structuring | 5 | 5 | 2.95 | 0.3390 |
| Dopo standardization | 4 | 4 | 2.70 | 0.3704 |
| Dopo divergence | 3 | 3 | 2.45 | 0.4082 |
| Dopo competition | 2 | 2 | 2.20 | 0.4545 |
| Dopo validation | 1 | 1 | 1.95 | 0.5128 |

Questi valori di costo/efficienza derivano direttamente dalla formula attuale di `benchmark.py` applicata ai tick e alle competenze attive osservate nel runtime. La colonna `storage_footprint` va **misurata** dopo il rerun, non stimata a tavolino.

### Comandi locali per rerun benchmark

Prima della patch:

```bash
PYTHONPATH=src python - <<'PY'
from scr.benchmark import BenchmarkRunner
path = BenchmarkRunner(output_path=".scr/benchmarks/manual_before/task_001.json").run("tasks/task_001")
print(path)
PY
```

Dopo la patch:

```bash
PYTHONPATH=src python - <<'PY'
from scr.benchmark import BenchmarkRunner
path = BenchmarkRunner(output_path=".scr/benchmarks/manual_after/task_001.json").run("tasks/task_001")
print(path)
PY
```

Confronto locale:

```bash
python - <<'PY'
import json
from pathlib import Path

before = json.loads(Path(".scr/benchmarks/manual_before/task_001.json").read_text())
after = json.loads(Path(".scr/benchmarks/manual_after/task_001.json").read_text())

for label, payload in [("before", before), ("after", after)]:
    b = payload["baseline_result"]
    s = payload["scr_result"]
    print(label)
    print("  baseline:", {
        "ticks": b.get("ticks"),
        "activated_competences_count": len(b["activated_competences"]),
        "resource_cost": b["resource_cost_score"],
        "storage_footprint": b["storage_footprint_estimate"],
        "efficiency": b["efficiency_score"],
    })
    print("  scr:", {
        "ticks": s.get("ticks"),
        "activated_competences_count": len(s["activated_competences"]),
        "resource_cost": s["resource_cost_score"],
        "storage_footprint": s["storage_footprint_estimate"],
        "efficiency": s["efficiency_score"],
    })
PY
```

## Flusso corretto del runtime

```mermaid
flowchart TD
    A[Start run(field)] --> B{outcome già definito?}
    B -- sì --> Z[Stop]
    B -- no --> C{tick >= max_ticks?}
    C -- sì --> Z
    C -- no --> D[select_next_unit(field, available_units)]
    D --> E{unit is None?}
    E -- sì --> Z
    E -- no --> F[tick += 1]
    F --> G[trace: tick_start]
    G --> H[trace: activation_policy with selected_unit]
    H --> I[activation = selected_unit.activation(field)]
    I --> J{activation < threshold?}
    J -- sì --> K[trace: unit_skipped]
    K --> B
    J -- no --> L[delta = selected_unit.transform(field)]
    L --> M[apply_delta(field, delta)]
    M --> B
```

## Rischi e mitigazioni

Il rischio principale, oggi, è **fare la patch sbagliata**: tornare ancora a toccare il runtime quando il dato mostra che il problema architetturale immediato è il benchmark.

Un secondo rischio concreto è **spostare il benchmark su un single-runtime** ma dimenticare `max_ticks`. Con `RuntimeConfig.max_ticks = 1`, il benchmark si fermerebbe subito al primo step. La mitigazione è semplice: nei percorsi benchmark usare sempre `RuntimeConfig(max_ticks=10)` o simile.

C’è poi un rischio di **mismatch semantico delle metriche**. Se il benchmark passa a un unico runtime, il campo `validation_time_ms` non rappresenterà più davvero la sola validazione, a meno che non venga strumentato in modo specifico. La mitigazione corretta è aggiungere `scr_runtime_time_ms` oppure misurare separatamente il tempo della `ValidationUnit`.

Un altro rischio è che **`ActivationPolicy` selezioni sempre la prima unità attivabile** ma il campo non muti nel modo previsto: in quel caso si genererebbe una pseudo-livelock fino a `max_ticks`. Oggi non ho evidenza che succeda su `task_001`, ma è una classe di errore reale. Le mitigazioni migliori sono:

- test espliciti di monotonicità del campo
- assert che la sequenza delle unità avanzi di fase
- opzionalmente, guardia diagnostica su ripetizione della stessa unità con stesso snapshot logico del campo

C’è poi il rischio di **doppia verità tra repo locale e archivio**. Il tuo `git status` ufficiale dice che il repo è pulito; l’archivio che ho ispezionato mostra invece uno stato Git interno diverso. La mitigazione pratica è semplice: quando applichi la patch reale, fidati del tuo repo locale, non dello storico Git interno al `.7z`.

Infine, il rischio più strategico è voler dimostrare il vantaggio di SCR su `task_001` fresh. Questo task, per come è costruito, è troppo lineare e parte da zero: anche con gating corretto, **tenderà comunque a usare tutte le fasi**. La mitigazione è cambiare il benchmark target:

- thread ripresi
- campi già parzialmente strutturati
- task multi-dominio
- scenari con riuso di stato

## Questioni aperte e limiti

Non ho una prova completa 79/79 dell’intera suite nel perimetro di questo report; ho però verificato la raccolta di **79 test** e il passaggio della suite critica del gating sulla snapshot ispezionata.

Non ho misurato i nuovi `storage_footprint_estimate` per gli stati parzialmente popolati dopo il rewiring benchmark; qui sarebbe scorretto inventare numeri. Mi aspetto una discesa, ma va confermata con rerun reali.

La decisione più delicata resta semantica, non meccanica: bisogna decidere se il benchmark deve misurare

- **il runtime SCR generale**
- oppure **la pipeline SCR da task fresco**
- oppure entrambe le cose, ma in due percorsi separati

Da tutto quello che emerge qui, la scelta migliore è **tenerli separati**. Su `task_001` fresh il risultato continuerà probabilmente a premiare la baseline; il vero valore del gating emergerà sui thread applicativi **ripresi o parzialmente completati**, non sui task “vergini” lineari.