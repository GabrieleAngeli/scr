# Validazione severa Fasi A-B-C

## Contesto branch
- Branch consolidata: `codex/analyze-documentation-and-propose-action-plan`
- Stato: contiene i cambiamenti operativi e test introdotti nelle fasi A, B e C.

## Fase A — Riallineamento benchmark
### Requisiti verificati
1. Modalità SCR unificata disponibile e default.
2. Modalità legacy mantenuta per confronto controllato.
3. Modalità invalidata con errore esplicito.
4. Metadati output benchmark (`scr_mode`, `scr_execution_model`) presenti.

### Evidenze
- `BenchmarkRunner` con `ALLOWED_SCR_MODES` e dispatch `_run_scr`.
- `ApplicationThreadBenchmark` allineato al `scr_mode`.
- Test su mode handling e payload mode fields verdi.

## Fase B — Test matrix gating scenario-based
### Requisiti verificati
1. Sequenza completa su campo fresh.
2. Riduzione tick su campi prepopolati.
3. Salto diretto verso unit downstream in base allo stato campo.
4. Copertura terminale (`outcome` già definito).

### Evidenze
- Suite `tests/test_runtime_activation_policy.py` con casi:
  - fresh -> 6 step;
  - post input -> start standardization;
  - post standardization -> start divergence;
  - hypothesis pool -> start competition;
  - active hypotheses -> validation;
  - validation_results -> consolidation;
  - outcome defined -> no run.

## Fase C — Segmentazione KPI
### Requisiti verificati
1. Segmentazione KPI per scenario (`task_fresh` vs `thread_prestructured`).
2. Segmentazione basata su stato iniziale del campo (non su campo mutato).
3. Bucket KPI stabile (`kpi_bucket`).
4. Test di regressione dedicati verdi.

### Evidenze
- `BenchmarkRunner.run` usa `initial_field` per `kpi_segmentation` e `run_field` separato.
- Test: `test_benchmark_payload_contains_kpi_segmentation`, `test_field_profile_classification_progression`, `test_kpi_segmentation_marks_prestructured_scenarios`.

## Esecuzione test severa
- Comando target fasi A-B-C:
  - `pytest -q tests/test_benchmark.py tests/test_application_thread_benchmark.py tests/test_runtime_activation_policy.py`
  - Esito: **39 passed**.

## Nota ambiente
- Esecuzione `pytest -q` full suite nel container: errore di collection su import `tests.*` in `test_learning.py` e `test_replay_loader_validator.py` (problema di import path, non regressione dei moduli A-B-C).
