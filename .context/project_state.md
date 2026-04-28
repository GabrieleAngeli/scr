# Project State

Date: 2026-04-28
Project: Segregated Competence Runtime (SCR) PoC
Status: InputStructuringUnit implemented

## Current Focus

Allineamento all'ADR con implementazione della sola InputStructuringUnit.

## Completed

- Analizzato il documento `SCR_POC_REQUIREMENTS.md`.
- Verificato che il workspace contiene al momento solo il file requisiti.
- Identificata la necessita di una memoria di progetto persistente per multi-scope LLM.
- Creata la cartella `.context`.
- Definita una architettura V0 operativa in `ARCHITECTURE_V0.md`.
- Letti `SCR_CODEX_IMPLEMENTATION_PACK.md` e `ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md`.
- Riallineato il codice al contratto `FieldState -> FieldDelta`.
- Implementati `FieldState`, `FieldDelta`, runtime minimale e `InputStructuringUnit`.
- Aggiunto task demo `tasks/task_001`.
- Aggiunti test pytest per delta e applicazione al campo.
- Aggiunto README breve con comando di esecuzione.
- Installato `pytest` nell'ambiente locale Python 3.9.
- Eseguiti test con esito verde: `2 passed`.
- Rafforzato il formato trace di `InputStructuringUnit` per replay/debug futuro.
- Aggiunto test semantico sui campi minimi di trace richiesti.
- Aggiunta configurazione VS Code per discovery ed esecuzione test pytest.
- Aggiunto test esplicito di serializzabilita JSON del `FieldState`.
- Corretto `expected_failure_present`: ora riflette la presenza di `meta.txt` non vuoto.
- Aggiunto `event_type` agli eventi trace di runtime e InputStructuringUnit.
- Implementata `StandardizationUnit` come normalizzazione del `context_map` gia popolato.
- Aggiunti test pytest mirati per artifact detection, trace e immutabilita dei file sorgenti.
- Aggiunto `.gitignore` standard per Python, cache test e stato locale VS Code.
- Implementata `DivergenceUnit` per generare almeno 3 ipotesi serializzabili nel `hypothesis_pool`.
- Aggiunti test pytest dedicati a schema ipotesi, target file, immutabilita dei file e trace replayable.
- Implementata `CompetitionUnit` per ordinare le ipotesi per confidence, mantenerne massimo 2 attive e marcare le restanti come `pruned`.
- Esteso `FieldDelta` con supporto minimale alla sostituzione controllata del `hypothesis_pool`.
- Implementata `ValidationUnit` con validazione deterministica su copia temporanea del task tramite `pytest`.
- Aggiunti test pytest per validazione delle sole ipotesi attive, isolamento dei file originali e trace replayable.
- Implementata `ConsolidationUnit` per determinare `outcome` e `selected_hypothesis` dal risultato della validation.
- Esteso `FieldState` e `FieldDelta` con supporto minimale a `outcome` e `selected_hypothesis`.
- Implementato `ReplayRecorder` per serializzare una run completa in `.scr/runs/{run_id}.json`.
- Aggiunti test pytest per file JSON replay, serializzabilita, trace, outcome e selected hypothesis.
- Implementati `ReplayLoader` e `ReplayValidator` per caricare replay JSON e verificarne la coerenza minima.
- Aggiunti test pytest per caricamento replay e failure modes di validazione.
- Implementato `L1LearningUpdater` come update post-run da replay validati verso `learning_state.json`.
- Aggiunti test pytest per creazione file stato, reward/penalty, clamp e determinismo.
- Implementati `BaselineRunner` e `BenchmarkRunner` per confrontare pipeline lineare minima e SCR sullo stesso task.
- Aggiunti test pytest per copia temporanea baseline, benchmark JSON e winner deterministico.
- Aggiornato `BenchmarkRunner` per usare di default path isolati per run in `.scr/benchmarks/{run_id}/{task_id}.json`.
- Mantenuta compatibilita piena con `output_path` esplicito.
- Esteso `BenchmarkRunner` a un confronto a tre livelli: baseline, SCR e reference model caricato da JSON.
- Aggiunte metriche comparative: quality, cost, storage footprint, competenze attivate/non usate ed efficiency score.
- Introdotto `ApplicationThreadBenchmark` separato da `BenchmarkRunner`, con modello `ApplicationThread` e metriche orientate al valore su thread applicativi.
- Creati 3 task benchmark complessi: `task_multi_branch_logic`, `task_network_retry_logic`, `task_stateful_computation`.
- Ogni task include `bug.py`, `test_bug.py` e `meta.txt` pensati per mettere in difficolta una baseline lineare.
- Introdotta `ActivationPolicy` nel runtime SCR per attivare solo le unita necessarie in base allo stato del campo.
- Aggiunti test runtime dedicati su attivazione selettiva, riduzione tick e trace delle sole unita attivate.
- Corretto il runtime per fare vero gating: una sola unita per tick tramite `ActivationPolicy.select_next_unit`.
- Migliorata `CompetitionUnit` con scoring informativo basato su rilevanza sul codice, tipo di fix e penalita per ipotesi generiche.
- Il ranking delle ipotesi ora usa `score` calcolato e mantiene massimo 2 ipotesi attive.

## Inferred Scope

- PoC Python 3.11+ per micro bug fixing su task con test reali.
- Runtime stateful a tick con campo condiviso.
- Pipeline base: activation, divergence, competition, validation, consolidation.
- Benchmark richiesto contro baseline lineare.

## Open Decisions

- Estensione del runtime a ulteriori unita oltre InputStructuring.
- Politica di normalizzazione per `meta.txt`.
- Struttura definitiva dei trace event per replay futuro.
- Definizione di energy, tension e stability quando entreranno altre unita.

## Next Suggested Steps

1. Se richiesto, implementare la prossima unita mantenendo il protocollo a delta.
2. Introdurre loader dedicato del task quando servira una CLI.
3. Valutare riallineamento a Python 3.11 quando l'ambiente lo rendera disponibile.

## Assumptions

- Il focus immediato e la sola InputStructuringUnit.
- Learning, divergence e validation restano fuori scope.
- I test attuali girano su Python 3.9 locale, quindi il codice evita costrutti non compatibili come `dataclass(slots=True)`.
