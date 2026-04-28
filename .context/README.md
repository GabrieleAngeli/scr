# Context Workspace

Questa cartella mantiene lo stato operativo del progetto SCR per permettere lavoro distribuito su piu scope LLM senza perdere continuita.

## File

- `project_state.md`: stato corrente, progressi, prossimi passi, assunzioni.
- `analysis_snapshot.md`: ultima analisi sintetica di requisiti, rischi e decisioni aperte.

## Regola operativa

Ogni avanzamento sostanziale deve aggiornare almeno:

1. `project_state.md`
2. `analysis_snapshot.md` se cambia la comprensione architetturale o dei requisiti

## Convenzione

- Stato breve e orientato all'azione.
- Nessun log verboso di tool.
- Data in formato `YYYY-MM-DD`.
