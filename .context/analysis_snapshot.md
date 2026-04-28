# Analysis Snapshot

Date: 2026-04-28
Source: `SCR_POC_REQUIREMENTS.md`

## What The File Defines Well

- Obiettivo del PoC chiaro: dimostrare un runtime verificabile, non una AGI.
- Dominio ristretto e testabile: micro bug fixing Python con validazione reale.
- Campo condiviso gia scomposto in segnali, ipotesi, energia, tensione, stabilita e trace.
- Runtime a tick coerente con un modello dinamico a operatori.
- Criteri V0 concreti: almeno 10 task, multi-ipotesi, pruning, riapertura, tracing, baseline.

## Strong Architectural Signals

- Le unita non sono semplici mapper input/output ma operatori che deformano il campo.
- La validation reale con `pytest/parse` e il cuore del criterio di verita.
- Il learning layer e pensato come ottimizzazione del processo, non del mapping diretto.

## Main Risks

- Requisiti concettualmente solidi ma ancora non tradotti in interfacce software.
- Nessuna definizione operativa di stabilita, tensione, energia e decay.
- Possibile deriva di complessita se si tenta di implementare learning e core runtime insieme.
- Mancano benchmark tasks e baseline, quindi non e ancora misurabile il valore del sistema.

## Recommended V0 Interpretation

- Escludere il learning dall'implementazione iniziale, ma lasciare hook e trace utili.
- Formalizzare `Field`, `Unit`, `Hypothesis`, `Runtime`, `Validator`, `TraceEvent`.
- Rendere `competition` un ranking/pruning esplicito prima della validation.
- Rendere `consolidation` il passaggio che promuove una ipotesi validata a soluzione finale.

## Implementation Progress

- Letti i documenti guida nella cartella `.context`.
- Rimosso lo scaffold non allineato al protocollo `FieldState -> FieldDelta`.
- Introdotti `src/scr/field.py` e `src/scr/delta.py` come modelli minimi ADR-compliant.
- Il runtime applica i delta ed esegue un solo tick utile, coerente con il vincolo di minimalita.
- Implementata solo `InputStructuringUnit`, che legge `bug.py`, `test_bug.py` e `meta.txt`.
- Aggiunti test che verificano sia l'isolamento della unita sia l'applicazione del delta da parte del runtime.
- Test eseguiti con `python -m pytest`: `2 passed`.
- Adattata la modellazione dataclass alla compatibilita del Python 3.9 disponibile nel workspace.
- La trace di `InputStructuringUnit` ora include metadati minimi per replay: `seq`, `tick`, `unit`, `reason`, `input_summary`, `changes`.
- Aggiunti file `.vscode` per eseguire i test dal pannello Testing o Run and Debug di VS Code.
- I test ora dimostrano anche che il `FieldState` risultante e serializzabile in JSON via `dataclasses.asdict`.
- La trace distingue ora semanticamente l'inizio tick (`tick_start`) dall'applicazione delta unita (`unit_delta_applied`).
- `StandardizationUnit` opera solo su `FieldState` gia popolato, produce un `FieldDelta` con artifact normalizzati e non modifica i file sorgenti.
- Il repo ora ignora cache Python, artefatti di build e stato locale non essenziale di VS Code, mantenendo versionati i file workspace utili ai test.
- `DivergenceUnit` usa solo artifact gia presenti nel `context_map`, non applica patch e aggiunge ipotesi minime e serializzabili tramite `FieldDelta`.
- `CompetitionUnit` aggiorna il `hypothesis_pool` senza eliminare ipotesi, usando un replace esplicito nel delta e una trace replayable con attive e pruned.
- `ValidationUnit` valida solo le ipotesi attive in una copia temporanea del task e riporta risultati serializzabili nel campo e nella trace.
- `ConsolidationUnit` deriva l'esito finale senza rieseguire test: `SUCCESS`, `REOPENED` o `FAILED_NO_VALID_HYPOTHESIS`, con selezione esplicita della prima ipotesi passata.
- `ReplayRecorder` e separato dal runtime decisionale e persiste solo lo stato finale necessario al replay in formato JSON.

## Open Questions

- Qual e il formato di una ipotesi: patch testuale, AST edit, o mutazione file?
- Ogni tick attiva tutte le unita o solo quelle sopra soglia?
- La riapertura nasce da failure di validation o da instabilita del campo?
- Il baseline lineare deve usare gli stessi operatori in pipeline fissa o una strategia piu semplice?
