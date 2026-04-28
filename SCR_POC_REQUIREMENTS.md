# Segregated Competence Runtime (SCR) --- PoC Requirements

------------------------------------------------------------------------

# 1. Obiettivo

Dimostrare un runtime con: - campo condiviso - competenze segregate -
attivazione selettiva - divergenza - competizione - validazione reale -
consolidamento

Non AGI, ma modello computazionale verificabile.

------------------------------------------------------------------------

# 2. Dominio

Micro bug fixing Python.

Struttura: task/ bug.py test_bug.py meta.txt

------------------------------------------------------------------------

# 3. Architettura

## Campo condiviso

-   task_signal
-   context_map
-   salience_map
-   hypothesis_pool
-   energy_map
-   tension_map
-   stability_score
-   activation_levels
-   trace

## Unità come operatori

-   nessun DTO/API
-   deformano il campo
-   hanno soglia, sensibilità, effetto, decadimento

## Runtime a tick

osserva → attiva → trasforma → aggiorna → verifica

------------------------------------------------------------------------

# 4. Funzionalità

-   InputStructuring
-   Standardization
-   Divergence (≥3 ipotesi)
-   Competition
-   Validation (pytest/parse)
-   Consolidation

------------------------------------------------------------------------

# 5. Fallimento

-   SUCCESS
-   REOPENED
-   FAILED_NO_VALID_HYPOTHESIS
-   FAILED_TIMEOUT
-   FAILED_UNSTABLE_FIELD
-   FAILED_VALIDATION

------------------------------------------------------------------------

# 6. Benchmark

Baseline lineare vs SCR

Metriche: - success rate - false positives - tick medi - costo -
riaperture utili

------------------------------------------------------------------------

# 7. Osservabilità

Traccia completa: - attivazioni (chi/perché) - ipotesi (nascita/morte) -
energia/tensione - validazioni - esito

------------------------------------------------------------------------

# 8. Tecnologie

Python 3.11+ pytest, ast, subprocess, tempfile

------------------------------------------------------------------------

# 9. Struttura

scr-demo/ src/scr/ tasks/ tests/

------------------------------------------------------------------------

# 10. Apprendimento (Learning Layer)

## 10.1 Obiettivo

Ottimizzare il **processo**: - attivazioni - divergenza - competizione -
validazione - convergenza

## 10.2 Principio

Apprendimento su **campo e dinamica**, non su mapping input→output.

## 10.3 Tipi

### L1 --- Locale (unità)

-   soglie attivazione
-   sensibilità segnali
-   intensità trasformazione
-   decay

### L2 --- Campo

-   priorità regioni
-   pattern di stabilità/instabilità
-   bias su configurazioni

### L3 --- Relazionale

-   sinergie/inibizioni tra unità
-   sequenze efficaci

### L4 --- Sistemico (episodico)

-   successo/fallimento
-   costo
-   numero tick/rami

## 10.4 Meccanismi

### Replay (obbligatorio)

Salvataggio completo della run e possibilità di rigioco.

### Hindsight labeling

A posteriori: - ipotesi corretta - errori unità - segnali mancati

### Reward/Penalità

-   reward globale (successo, costo)
-   reward locali (qualità ipotesi, pruning)
-   penalità (rami inutili, validazioni sprecate, convergenza prematura)

## 10.5 Parametri apprendibili

-   per unità: threshold, weight, sensitivity, decay
-   per campo: priorità/penalità configurazioni
-   per runtime: max rami, ordine operatori, criteri stop

## 10.6 Modalità (roadmap)

-   V0: statico
-   V1: adaptive tuning (soglie/pesi)
-   V2: bandit/RL leggero
-   V3: moduli neurali mirati (standardization/divergence/competition)

## 10.7 Sicurezza

-   evitare collasso (tutte le unità uguali)
-   evitare dominanza singola
-   evitare instabilità del campo
-   evitare overfitting sui task

## 10.8 Metriche learning

-   ↑ success rate
-   ↓ falsi positivi
-   ↓ rami inutili
-   ↓ tick/costo
-   ↑ stabilità convergenza

## 10.9 Criteri accettazione learning

-   miglioramento su task visti e simili nuovi
-   riduzione costo medio
-   convergenza più stabile
-   pruning più efficace

------------------------------------------------------------------------

# 11. Flusso finale

input → field init → activation cycle → divergence → competition →
validation → consolidation → outcome → replay → learning update → next
run

------------------------------------------------------------------------

# 12. Criteri di accettazione V0

1.  ≥10 task
2.  validatore reale funzionante
3.  multi-ipotesi
4.  pruning prima della validation
5.  riaperture possibili
6.  consolidamento corretto o fallimento esplicito
7.  confronto con baseline
8.  tracing completo
9.  miglioramenti misurabili vs baseline
