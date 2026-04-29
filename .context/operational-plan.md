# Piano operativo SCR basato sulla documentazione e deep-research-report

## 1) Scope applicativo ricostruito

Il progetto SCR è un PoC di runtime a competenze segregate per **micro bug fixing Python** con criterio di verità esterno: l'esito reale di `pytest`.

Pilastri funzionali:
- comunicazione indiretta via `FieldState` (niente chiamate dirette tra unit);
- ciclo a tick con attivazione selettiva;
- divergenza multi-ipotesi, competizione, validazione reale e consolidamento;
- osservabilità/replay per diagnosi e, in roadmap, apprendimento incrementale.

## 2) Evidenze chiave dal deep-research-report

Il report identifica che:
1. il runtime implementa già il gating “una unità per tick”;
2. il collo di bottiglia prestazionale è nel benchmark attuale, che esegue SCR come 6 runtime monounità in serie;
3. su task lineari/freschi il costo di SCR resta alto (6 tick, 6 competenze attivate), quindi la baseline risulta più efficiente;
4. il valore del gating emerge solo su campi preformati/parzialmente popolati;
5. priorità quindi su rifattorizzazione benchmark + test di scenario, non su nuovo rewrite del loop runtime.

## 3) Gap strategici attuali

- **Misallineamento metrica-architettura**: benchmark non misura la decisione dinamica del runtime multi-unità.
- **Copertura test incompleta lato applicativo**: ci sono test gating, ma manca una batteria chiara end-to-end su stati campo progressivi.
- **Narrativa prodotto fragile**: senza benchmark coerente, SCR appare sempre meno efficiente della baseline anche quando il gating è corretto.
- **Roadmap learning scollegata**: prima di tuning adattivo serve stabilizzare misure e segnali osservabili.

## 4) Piano operativo (4 fasi)

### Fase A — Riallineamento benchmark (priorità massima, 3–5 giorni)

Obiettivo: misurare SCR come **singolo runtime con tutte le unità**, non come pipeline manuale di runtime separati.

Attività:
1. introdurre percorso benchmark “orchestrazione unificata” in `BenchmarkRunner`;
2. mantenere eventualmente il percorso legacy dietro flag per confronto storico;
3. aggiornare `ApplicationThreadBenchmark` per usare il nuovo percorso;
4. rendere esplicito `max_ticks` nei chiamanti benchmark.

Deliverable:
- metriche `ticks`, `activated_competences`, `efficiency_score` coerenti con gating reale;
- report comparativo legacy-vs-unified.

### Fase B — Test matrix orientata al gating reale (3–4 giorni)

Obiettivo: dimostrare in modo deterministico che i tick diminuiscono con campo più prestrutturato.

Attività:
1. aggiungere test su stati: fresh, post-input, post-standardization, post-divergence, post-competition, post-validation, outcome già presente;
2. asserire sia conteggio tick sia sequenza `selected_unit` nel trace;
3. consolidare test benchmark per evitare regressioni verso la pipeline monounità.

Deliverable:
- suite di regressione gating applicativo;
- criteri pass/fail leggibili per QA.

### Fase C — Ricalibrazione KPI e acceptance V0 (2–3 giorni)

Obiettivo: aggiornare criteri di successo con metriche non fuorvianti.

Attività:
1. separare KPI “task fresco” da KPI “thread parzialmente lavorato”;
2. fissare soglie minime su riduzione tick/costo nei casi preformati;
3. mantenere confronto baseline ma con segmentazione scenario-based.

Deliverable:
- tabella KPI V0 aggiornata;
- protocollo benchmark ufficiale versionato.

### Fase D — Preparazione Learning Layer V1 (4–6 giorni)

Obiettivo: abilitare adaptive tuning solo dopo stabilità metrica.

Attività:
1. rafforzare schema replay con feature utili al credit assignment;
2. definire primo set di parametri apprendibili (threshold/sensitivity/decay);
3. introdurre ciclo offline di valutazione “prima/dopo tuning” su task visti/simili.

Deliverable:
- specifica tecnica V1 learning-ready;
- piano sperimentale con guardrail anti-collasso.

## 5) Backlog eseguibile (ordine consigliato)

1. Refactor `_run_scr` in modalità runtime unificato.
2. Aggiornamento `application_benchmark` al nuovo entrypoint.
3. Nuovi test gating scenario-based.
4. Aggiornamento documentazione benchmark e KPI.
5. Solo dopo: spike su adaptive tuning.

## 6) Rischi e mitigazioni

- Rischio: regressioni su test benchmark esistenti.
  - Mitigazione: mantenere path legacy transitorio con confronto controllato.
- Rischio: miglioramenti non visibili su task troppo semplici.
  - Mitigazione: separare dashboard per complessità e stato iniziale campo.
- Rischio: introdurre learning troppo presto.
  - Mitigazione: gate formale “benchmark stabile” prima della fase V1.

## 7) Definition of Done (operativa)

Il piano è considerato completato quando:
1. benchmark misura SCR come runtime unico e produce metriche tracciabili;
2. esiste test matrix che prova la riduzione tick con campo preformato;
3. KPI V0 sono segmentati per scenario e approvati;
4. replay/trace espongono segnali minimi per il tuning V1.
