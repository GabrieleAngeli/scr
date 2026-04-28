# ADR-0001 — Field-Based Competence Runtime e Standard di Comunicazione tra Unità

## Stato

Accepted for PoC

## Data

2026-04-28

## Contesto

Il progetto **Segregated Competence Runtime (SCR)** vuole dimostrare un runtime in cui più competenze distinte cooperano e competono senza diventare un unico modello monolitico.

Il dominio del PoC è volutamente ristretto: **micro bug fixing Python**.

Il rischio principale è che l'architettura degeneri in uno dei seguenti modelli non desiderati:

1. orchestratore lineare classico;
2. rule engine statico;
3. insieme di microservizi con API/DTO;
4. LLM monolitico mascherato da più unità;
5. sistema instabile senza criteri di convergenza.

Per evitare questi fallimenti, il PoC adotta un principio centrale:

> Le unità non comunicano tra loro direttamente. Comunicano solo deformando un campo condiviso.

---

## Decisione

Adottiamo un'architettura **Field-Based Competence Runtime**.

Ogni unità di competenza implementa il contratto:

```text
FieldState -> FieldDelta
```

Il runtime è l'unico componente autorizzato ad applicare i delta al campo.

Le unità sono operatori locali con:

- soglia di attivazione;
- sensibilità;
- peso;
- decay;
- funzione di attivazione;
- funzione di trasformazione.

Il sistema evolve a tick:

```text
observe -> activate -> transform -> update -> validate -> consolidate -> learn
```

---

## Standard di comunicazione

### Nome

**Field Transformation Protocol (FTP-SCR)**

Nota: non è un protocollo di rete. È un protocollo semantico interno al runtime.

### Regola base

Una unità non invia messaggi a un'altra unità.

Una unità può solo produrre un `FieldDelta`.

### Input standard

```python
FieldState
```

Contiene almeno:

```text
task_signal
context_map
salience_map
hypothesis_pool
energy_map
tension_map
stability_score
activation_levels
trace
tick
```

### Output standard

```python
FieldDelta
```

Contiene almeno:

```text
source_unit
salience_updates
tension_updates
energy_updates
hypotheses_add
hypotheses_remove
context_updates
stability_shift
trace_events
```

---

## Regole di isolamento delle unità

Ogni unità può:

- leggere una snapshot del campo;
- calcolare il proprio livello di attivazione;
- proporre un delta;
- aggiungere eventi di trace;
- proporre ipotesi;
- rafforzare o indebolire regioni del campo.

Ogni unità non può:

- modificare direttamente `FieldState`;
- chiamare metodi di altre unità;
- leggere memoria privata di altre unità;
- validare e consolidare bypassando il runtime;
- accedere a risorse esterne non dichiarate;
- cambiare i parametri di learning di altre unità.

---

## Modello di apprendimento

### Decisione

Per il PoC non adottiamo training neurale end-to-end.

Adottiamo un apprendimento incrementale a livelli:

| Livello | Oggetto appreso | Metodo PoC |
|---|---|---|
| L1 Locale | threshold, sensitivity, weight, decay | adaptive tuning |
| L2 Campo | pattern di stabilità/instabilità | pattern memory |
| L3 Relazionale | sinergie/inibizioni tra unità | influence matrix |
| L4 Episodico | esiti, costi, rami, replay | episode store |

---

## Perché non usare training end-to-end

Il training end-to-end viene escluso dal PoC perché:

- rende difficile attribuire responsabilità alle unità;
- tende a far collassare le competenze in un unico comportamento medio;
- rende opaca la comunicazione;
- rende difficile il replay deterministico;
- aumenta i costi e riduce la verificabilità.

Il PoC deve prima dimostrare la dinamica computazionale.

---

## Reward model

Il reward è ritardato e attribuito sulla base del trace.

Esempi:

```text
+1.0  ipotesi validata con successo
+0.3  pruning utile
+0.2  riduzione tensione senza perdita di ipotesi valide
-0.5  validazione sprecata
-0.3  aumento instabilità
-1.0  timeout o campo instabile
```

Il learning update è consentito solo se il trace permette attribution minima.

---

## Anti-collasso

Il runtime deve impedire:

1. dominanza di una singola unità;
2. convergenza prematura su una sola ipotesi;
3. ipotesi duplicate mascherate da divergenza;
4. instabilità crescente del campo;
5. overfitting sui task visti.

Meccanismi richiesti:

- usage penalty per unità troppo frequenti;
- limite massimo di attivazioni consecutive;
- similarity check sulle ipotesi;
- clamp dei parametri apprendibili;
- replay su task visti e nuovi;
- outcome esplicito in caso di fallimento.

---

## Runtime ownership

Il runtime possiede:

- applicazione dei delta;
- ordine dei tick;
- regole di stop;
- validazione reale;
- consolidamento;
- persistenza replay;
- invocazione del learning update.

Le unità possiedono:

- logica di attivazione;
- logica di trasformazione;
- parametri locali;
- contributo semantico al trace.

---

## Validation policy

La validazione deve essere reale.

Nel dominio Python micro bug fixing sono ammessi:

- `pytest`;
- `ast.parse`;
- esecuzione in directory temporanea;
- confronto output/errore;
- controlli statici minimali.

Non è ammesso marcare una ipotesi come valida solo perché ha score alto.

---

## Replay policy

Ogni run deve essere serializzata.

Il replay deve includere:

- campo iniziale;
- lista tick;
- unità attivate;
- delta prodotti;
- ipotesi create/rimosse;
- validation result;
- outcome finale;
- parametri prima/dopo learning.

Il replay è parte del modello di apprendimento, non solo logging.

---

## Conseguenze positive

Questa decisione produce:

- separazione reale delle competenze;
- tracciabilità delle attivazioni;
- debugging più semplice;
- possibilità di benchmark contro baseline lineare;
- learning locale e interpretabile;
- possibilità di estendere in futuro con moduli neurali mirati.

---

## Conseguenze negative

Questa decisione introduce:

- maggiore complessità rispetto a una pipeline classica;
- necessità di progettare bene le feature del campo;
- rischio di instabilità se energy/tension sono mal calibrate;
- performance inizialmente inferiori a euristiche hardcoded;
- più lavoro sui test di osservabilità.

Questi costi sono accettati perché il PoC deve dimostrare il modello SCR, non solo risolvere bug Python.

---

## Alternative considerate

### Alternativa A — Pipeline lineare

Scartata perché non dimostra attivazione selettiva, divergenza e competizione.

### Alternativa B — Microservizi per competenza

Scartata perché reintroduce API/DTO e sposta il problema sulla comunicazione distribuita.

### Alternativa C — Singolo LLM orchestratore

Scartata perché collassa il concetto di competenze segregate.

### Alternativa D — Rule engine statico

Scartata perché non supporta apprendimento e adattamento.

---

## Criteri di accettazione collegati all'ADR

L'implementazione rispetta questo ADR se:

1. ogni unità implementa `FieldState -> FieldDelta`;
2. nessuna unità chiama direttamente un'altra unità;
3. il runtime è l'unico componente che applica delta;
4. ogni run produce trace completo;
5. esistono almeno 3 ipotesi divergenti;
6. esiste pruning prima della validation;
7. la validation è reale;
8. il replay è persistito;
9. il learning aggiorna parametri locali con clamp;
10. il sistema produce fallimenti espliciti.

---

## Decisione finale

Per il PoC SCR adottiamo il **Field Transformation Protocol** come unico standard di comunicazione tra unità e un learning layer incrementale, locale, tracciabile e replayable.

L'obiettivo non è massimizzare subito la capacità di bug fixing, ma dimostrare che competenze segregate possono produrre convergenza verificabile attraverso un campo condiviso.
