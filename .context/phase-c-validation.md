# Phase C Validation (strict)

## Requisiti fase C
1. KPI segmentati per scenario (`task_fresh` vs `thread_prestructured`).
2. Segmentazione basata sullo **stato iniziale del campo**, non sul campo mutato a fine run.
3. Tracciabilità del bucket KPI (`kpi_bucket`) per analisi offline.
4. Regressione: benchmark e gating test verdi.

## Verifiche implementate
- `BenchmarkRunner.run` crea un `initial_field` e usa quello per `kpi_segmentation`.
- `_build_kpi_segmentation` produce `field_profile`, `scenario`, `kpi_bucket`.
- `_field_profile` classifica stati progressivi del field.
- Test automated coprono:
  - payload default con `task_fresh:fresh_from_zero`;
  - classificazione stati progressivi;
  - scenario prestrutturato con bucket coerente.

## Esito
Phase C validata sui requisiti minimi: segmentazione scenario-aware, profilazione campo iniziale, bucket stabile e suite test passata.
