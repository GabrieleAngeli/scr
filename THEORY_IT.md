# Segregated Competence Runtime — Documentazione Teorica

> Versione: 0.1 — Allineata al PoC V0  
> Data: 2026-04-28  
> Riferimenti normativi: `ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md`, `SCR_POC_REQUIREMENTS.md`, `ARCHITECTURE_V0.md`

---

## 1. Obiettivo

Il **Segregated Competence Runtime (SCR)** è un runtime computazionale progettato per dimostrare che competenze specializzate distinte possono cooperare e competere per produrre convergenza verificabile **senza diventare un sistema monolitico**.

L'obiettivo non è costruire un sistema di intelligenza artificiale generale (AGI). L'obiettivo è dimostrare un **modello computazionale verificabile** con le seguenti proprietà:

| Proprietà | Descrizione |
| --- | --- |
| Campo condiviso | Tutte le unità leggono e deformano un unico oggetto di stato mutabile |
| Competenze segregate | Ogni unità ha un dominio di responsabilità circoscritto e non può invocare direttamente altre unità |
| Attivazione selettiva | Le unità si attivano solo quando il campo supera la loro soglia di sensibilità |
| Divergenza controllata | Il sistema esplora almeno 3 ipotesi indipendenti prima di convergere |
| Competizione e pruning | Le ipotesi competono per score prima di essere sottoposte a validazione reale |
| Validazione reale | La verità non è definita da uno score interno ma dall'esito di `pytest` |
| Consolidamento esplicito | Ogni run termina con un outcome dichiarato: `SUCCESS`, `REOPENED` o uno stato di fallimento specifico |
| Tracciabilità completa | Ogni attivazione, delta e decisione è registrata in un trace serializzabile |
| Replay deterministico | Ogni run può essere riletta e confrontata, costituendo la base del learning |

Il dominio del PoC è volutamente ristretto: **micro bug fixing Python**. La scelta non è limitazione ma strategia: un dominio piccolo e verificabile permette di misurare la dinamica computazionale senza rumore.

---

## 2. Teoria

### 2.1 Il problema che SCR intende risolvere

I sistemi di ragionamento automatico tendono a degenerare in uno di questi pattern non desiderati:

1. **Orchestratore lineare**: le competenze vengono eseguite in sequenza fissa, senza feedback dinamico tra stadi.
2. **Rule engine statico**: le regole sono hardcoded, il sistema non apprende e non si adatta.
3. **Insieme di microservizi**: le unità si chiamano tramite API/DTO, spostando il problema sulla comunicazione distribuita.
4. **LLM monolitico mascherato**: un singolo modello neurale simula più unità ma collassa le competenze in un comportamento medio.
5. **Sistema instabile**: il campo oscilla senza criteri di convergenza, producendo output non deterministici.

SCR adotta un principio radicalmente diverso: **le unità non comunicano tra loro**. Comunicano solo deformando un campo condiviso.

### 2.2 Il modello del campo

Il campo (`FieldState`) è l'unico mezzo di comunicazione tra unità. Non è un database passivo: è un oggetto di stato dinamico che porta informazione semantica su ogni dimensione.

```text
FieldState
├── task_signal          # input grezzo: task_id, task_path
├── context_map          # artefatti strutturati: codice, AST, simboli, fallimenti attesi
├── salience_map         # rilevanza percepita di regioni del campo (float 0–1)
├── hypothesis_pool      # ipotesi attive, pruned, validate
├── energy_map           # energia disponibile per unità/regione
├── tension_map          # tensione interna: indicatore di contraddizione o incertezza
├── stability_score      # punteggio di convergenza complessivo del campo
├── activation_levels    # livello di attivazione corrente di ogni unità
├── trace                # log strutturato di ogni evento semantico
├── tick                 # contatore temporale del runtime
├── outcome              # esito finale della run
└── selected_hypothesis  # ipotesi consolidata come soluzione
```

Ogni dimensione ha un significato computazionale preciso:

- **salience_map**: segnala quali regioni del campo meritano attenzione. Le unità la leggono per decidere se attivarsi. Le unità la scrivono per orientare le unità successive.
- **tension_map**: rappresenta la contraddizione interna. Alta tensione su un'ipotesi segnala che le unità sono in disaccordo sul suo valore. Il runtime usa la tensione per decidere se forzare pruning o riapertura.
- **energy_map**: modella il costo computazionale assegnato a unità e ipotesi. Un'unità con energia bassa tende a decadere.
- **stability_score**: misura globale di convergenza. Scende quando il campo oscilla, sale quando le ipotesi si stabilizzano.

### 2.3 Le unità come operatori locali

Un'unità di competenza (`CompetenceUnit`) è un operatore che osserva una snapshot del campo e produce una trasformazione localizzata.

Il contratto formale è:

```text
FieldState → FieldDelta
```

L'interfaccia minima implementata è:

```python
class CompetenceUnit(ABC):
    name: str
    threshold: float    # soglia di attivazione minima
    sensitivity: float  # amplificazione del segnale in ingresso
    weight: float       # peso del contributo al campo
    decay: float        # tasso di decadimento dell'energia propria

    def activation(self, field: FieldState) -> float: ...
    def transform(self, field: FieldState) -> FieldDelta: ...
```

Il runtime chiama `activation(field)` per ogni unità e attiva solo quelle il cui valore supera `threshold`. L'unità attivata chiama `transform(field)` e restituisce un `FieldDelta`. Il runtime è l'unico componente autorizzato ad applicare i delta al campo.

Un'unità **non può**:

- modificare `FieldState` direttamente;
- chiamare metodi di altre unità;
- leggere memoria privata di altre unità;
- validare o consolidare bypassando il runtime;
- accedere a risorse esterne non dichiarate.

### 2.4 Il ciclo a tick

Il runtime esegue cicli discreti chiamati **tick**. Ogni tick segue la sequenza:

```text
observe → activate → transform → apply → update → validate → consolidate
```

In dettaglio:

1. **observe**: ogni unità calcola il proprio livello di attivazione leggendo il campo.
2. **activate**: il runtime seleziona le unità con `activation >= threshold`.
3. **transform**: le unità selezionate producono i loro `FieldDelta`.
4. **apply**: il runtime applica tutti i delta al campo nell'ordine di raccolta.
5. **update**: il runtime ricalcola `stability_score`, aggiorna `energy_map` e `tension_map`.
6. **validate**: se ci sono ipotesi `validating`, il runtime le sottopone a `pytest`.
7. **consolidate**: se esiste un'ipotesi validata, il runtime la promuove a soluzione e termina.

Il runtime produce esiti espliciti:

| Outcome | Significato |
| --- | --- |
| `SUCCESS` | Almeno un'ipotesi ha superato la validazione reale |
| `REOPENED` | Tutte le ipotesi attuali hanno fallito, ma il campo contiene segnali utili per riapertura |
| `FAILED_NO_VALID_HYPOTHESIS` | Nessuna ipotesi è rimasta nel pool dopo pruning e validazione |
| `FAILED_TIMEOUT` | Il numero massimo di tick è stato raggiunto senza convergenza |
| `FAILED_UNSTABLE_FIELD` | La tensione media è rimasta sopra soglia per troppi tick consecutivi |
| `FAILED_VALIDATION` | Le ipotesi esistono ma nessuna ha superato la validazione |

### 2.5 Le unità di competenza del PoC

Il PoC V0 implementa sei unità distinte, ciascuna con responsabilità circoscritta:

```text
InputStructuringUnit
  └── Trasforma task_signal in artefatti strutturati nel context_map.
      Popola salience su code, tests, failure_signal.

StandardizationUnit
  └── Analizza bug.py con AST. Estrae simboli, funzioni, classi.
      Aumenta salience su regioni sospette.

DivergenceUnit
  └── Genera ≥3 ipotesi distinte (fix operatore, boundary, None,
      variabile, return). Aggiunge al hypothesis_pool via FieldDelta.

CompetitionUnit
  └── Assegna score alle ipotesi. Penalizza duplicati.
      Effettua pruning prima della validazione.

ValidationUnit (ValidationGateUnit)
  └── Materializza patch in workspace temporaneo.
      Esegue pytest. Aggiorna stato ipotesi nel campo.

ConsolidationUnit
  └── Seleziona l'ipotesi validata migliore. Emette l'outcome finale.
      Registra metriche nel trace. Predispone il payload per il replay.
```

### 2.6 Il protocollo di comunicazione: Field Transformation Protocol (FTP-SCR)

Il **FTP-SCR** è lo standard semantico interno al runtime che regola come le unità interagiscono con il campo. Non è un protocollo di rete.

Le regole sono:

- Una unità **non invia messaggi** a un'altra unità.
- Una unità può solo produrre un `FieldDelta`.
- Il runtime è l'unico intermediario autorizzato.

Il `FieldDelta` trasporta:

```text
FieldDelta
├── source_unit          # unità che ha prodotto il delta
├── salience_updates     # aggiornamenti alle priorità del campo
├── tension_updates      # aggiornamenti alla tensione
├── energy_updates       # aggiornamenti all'energia
├── hypotheses_add       # nuove ipotesi da aggiungere al pool
├── hypotheses_replace   # sostituzione atomica del pool (usato da CompetitionUnit)
├── hypotheses_remove    # ipotesi da rimuovere per id
├── context_updates      # aggiornamenti al context_map
├── stability_shift      # variazione dello stability_score
├── outcome              # esito finale (se determinato da questa unità)
├── selected_hypothesis  # ipotesi consolidata (se determinata da questa unità)
└── trace_events         # eventi semantici da aggiungere al trace
```

### 2.7 Il modello di apprendimento

SCR adotta un learning **incrementale, locale e tracciabile**, non un training neurale end-to-end.

Il motivo è architetturale: il training end-to-end tende a far collassare le competenze in un unico comportamento medio, rendendo opaca la comunicazione e difficile l'attribuzione dei reward.

Il learning è strutturato in quattro livelli:

| Livello | Oggetto appreso | Metodo |
| --- | --- | --- |
| L1 Locale | threshold, sensitivity, weight, decay per unità | adaptive tuning |
| L2 Campo | pattern di stabilità e instabilità | pattern memory |
| L3 Relazionale | sinergie e inibizioni tra unità | influence matrix |
| L4 Episodico | esiti, costi, rami, replay | episode store |

Il **replay** è il meccanismo portante del learning. Ogni run è serializzata in JSON con:

- campo iniziale;
- lista tick;
- unità attivate e delta prodotti;
- ipotesi create e rimosse;
- risultati di validazione;
- outcome finale;
- parametri prima e dopo il learning update.

Il replay non è semplice logging. È la base per l'attribuzione retrospettiva dei reward (**hindsight labeling**): a posteriori è possibile identificare quali unità hanno contribuito al successo o al fallimento e aggiornare i loro parametri locali con clamp.

Il reward model del PoC:

```text
+1.0  ipotesi validata con successo
+0.3  pruning utile (eliminazione di ipotesi non promettenti prima della validazione)
+0.2  riduzione tensione senza perdita di ipotesi valide
-0.5  validazione sprecata (ipotesi inviata a pytest senza sufficiente score)
-0.3  aumento instabilità del campo
-1.0  timeout o campo instabile
```

### 2.8 Anti-collasso

SCR include meccanismi espliciti per impedire le degenerazioni strutturali più comuni:

| Rischio | Meccanismo |
| --- | --- |
| Dominanza di una singola unità | Usage penalty per unità troppo frequenti; limite di attivazioni consecutive |
| Convergenza prematura | Diversity check sulle ipotesi; limit minimo di ipotesi prima della validation |
| Ipotesi duplicate | Similarity check prima dell'aggiunta al pool |
| Instabilità crescente | Clamp dei parametri apprendibili; criteri di stop espliciti |
| Overfitting sui task visti | Replay su task visti e nuovi; episode store separato da training |

---

## 3. Tesi a favore della teoria

### Tesi 1 — La comunicazione via campo è più espressiva e sicura della comunicazione diretta tra unità

Quando le unità comunicano tramite chiamate dirette o DTO, la struttura della comunicazione è implicita nel grafo delle dipendenze. Aggiungere o rimuovere un'unità richiede di modificare tutte le unità che la chiamano o che ne ricevono output.

Con il campo, la struttura della comunicazione è **esplicita e centralizzata nel campo stesso**. Un'unità può leggere il campo arricchito da qualsiasi altra unità senza sapere chi lo ha popolato. Il runtime può aggiungere o rimuovere unità senza modificare quelle esistenti.

La prova operativa in SCR: `InputStructuringUnit` popola `context_map["artifacts"]`. `StandardizationUnit` legge da lì senza sapere che è stata `InputStructuringUnit` a farlo. `DivergenceUnit` legge `context_map["ast_summary"]` prodotto da `StandardizationUnit`. Nessuna unità conosce le altre.

### Tesi 2 — La validazione reale è l'unico criterio di verità computazionalmente onesto

In molti sistemi multi-agente, la "validazione" è interna: un'ipotesi viene promossa perché ha uno score alto rispetto ad altre ipotesi. Questo è tautologico: lo score misura quanto un'ipotesi assomiglia a ciò che il sistema si aspetta di vedere, non se è corretta.

SCR adotta un principio opposto: **nessuna ipotesi è valida solo perché ha score alto**. La validazione richiede l'esecuzione reale di `pytest` su una copia del task con la patch applicata.

Questa scelta ha un costo (la validazione è lenta e costosa) che è accettato consapevolmente perché il PoC deve dimostrare un modello verificabile, non ottimizzare una metrica interna.

### Tesi 3 — La divergenza controllata produce soluzioni migliori della convergenza prematura

Un sistema che genera una sola ipotesi e la valida immediatamente ha probabilità di successo proporzionale alla qualità della sua prima ipotesi. Un sistema che genera almeno 3 ipotesi distinte e le fa competere prima della validazione ha probabilità di successo proporzionale alla qualità del suo meccanismo di generazione e selezione.

Il benchmark previsto di SCR contro la baseline lineare misura esattamente questo: la baseline genera una o poche ipotesi in sequenza fissa; SCR genera almeno 3 ipotesi divergenti, le fa competere e valida solo le top-k. Le metriche attese sono:

- **success rate**: SCR > baseline per task con bug ambigui (multiple cause plausibili);
- **false positives**: SCR < baseline grazie al pruning pre-validation;
- **riaperture utili**: disponibili solo in SCR, assenti nella baseline.

### Tesi 4 — La segregazione delle competenze rende il sistema debuggabile e migliorabile localmente

In un sistema monolitico, un comportamento errato può avere origine in qualsiasi punto del sistema. Non è possibile attribuire il fallimento a una componente specifica senza analizzare l'intero sistema.

In SCR, ogni unità ha responsabilità circoscritte e produce un trace esplicito delle proprie azioni. Se `DivergenceUnit` genera ipotesi troppo simili tra loro, il problema è localizzato e misurabile (similarity check fallisce, il pool è ridondante). Se `CompetitionUnit` effettua pruning eccessivo, il trace mostra quante ipotesi sono state eliminate e con quale score.

Il trace strutturato per ogni evento include:

```json
{
  "seq": 3,
  "tick": 1,
  "unit": "divergence",
  "event_type": "unit_delta_applied",
  "reason": "context_map contains ast_summary and failure_signal",
  "input_summary": { "hypotheses_before": 0, "ast_functions": ["calculate"] },
  "changes": { "hypotheses_added": 3 }
}
```

Questo rende ogni decisione tracciabile, riproducibile e attribuibile.

### Tesi 5 — Il learning locale e incrementale è più stabile e interpretabile del training end-to-end

Il training end-to-end su un sistema multi-agente ottimizza un obiettivo globale distribuendo i gradienti attraverso tutte le unità. Il risultato atteso è che le unità convergono verso comportamenti che massimizzano l'obiettivo globale, ma **collassano le loro differenze** perché il gradiente non distingue quale unità ha contribuito a quale parte dell'esito.

SCR adotta invece adaptive tuning locale: ogni unità aggiorna i propri parametri (`threshold`, `sensitivity`, `weight`, `decay`) in base al reward attribuito specificamente al suo contributo nella run, ricostruito tramite il trace.

L'update rule è deliberatamente semplice:

```python
new_value = old_value + learning_rate * reward * influence
```

Con clamp sui parametri per impedire degenerazioni:

```text
threshold:   [0.05, 0.95]
sensitivity: [0.10, 5.00]
weight:      [0.10, 5.00]
decay:       [0.00, 0.50]
```

La semplicità è una scelta consapevole: il PoC deve prima dimostrare la dinamica computazionale. La complessità del learning può crescere solo dopo che la dinamica è verificata.

### Tesi 6 — Il replay episodico è superiore al logging come meccanismo di apprendimento

Un log registra eventi. Un replay registra lo stato sufficiente per ricostruire e reinterpretare una run completa.

Il `ReplayRecorder` di SCR persiste:

- campo iniziale e campo finale;
- ogni tick con unità attivate e delta prodotti;
- ipotesi create, rimosse e validate;
- outcome finale e ipotesi selezionata;
- timestamp per ordinamento temporale.

Il `ReplayValidator` verifica che ogni replay rispetti le invarianti strutturali: chiavi obbligatorie presenti, trace non vuota, seq strettamente crescente, ipotesi selezionata presente in caso di `SUCCESS`.

Questa struttura permette di applicare **hindsight labeling**: a posteriori, sapendo che la run è terminata con `SUCCESS` e che l'ipotesi `hyp-003` è stata quella corretta, è possibile risalire nel trace e assegnare reward positivi alle unità che hanno prodotto o rinforzato `hyp-003`, e reward negativi alle unità che hanno generato ipotesi poi prunate o fallite.

### Tesi 7 — Un dominio piccolo e verificabile è la strategia corretta per validare un modello computazionale nuovo

La scelta del dominio — micro bug fixing Python con `pytest` — non è una limitazione del PoC. È la strategia corretta per validare un modello computazionale nuovo.

Un dominio grande introduce variabili confondenti: non è chiaro se un fallimento dipende dal modello computazionale o dalla complessità del dominio. Un dominio piccolo con criterio di verità reale (pytest passa o non passa) permette di misurare esattamente la dinamica che SCR intende dimostrare.

Il passaggio a domini più complessi (multi-file refactoring, security analysis, system design) è possibile solo dopo che il modello è validato nel dominio piccolo. SCR è progettato per questo: le unità sono operatori locali, il campo è generico, il runtime è parametrico. Cambiare dominio significa aggiungere o sostituire unità, non riscrivere il runtime.

---

## 4. Roadmap evolutiva

| Versione | Scope | Stato |
| --- | --- | --- |
| V0 | Runtime statico, 6 unità, validazione reale, replay | In corso (PoC) |
| V1 | Adaptive tuning su threshold/weight/decay | Pianificato |
| V2 | Bandit / RL leggero per selezione unità e ipotesi | Pianificato |
| V3 | Moduli neurali mirati (standardization, divergence, competition) | Roadmap |

La progressione è deliberata: ogni livello di complessità è introdotto solo dopo che il livello precedente è verificato empiricamente sui task di benchmark.

---

## 5. Criteri di accettazione della teoria

La teoria alla base di SCR è confermata se il PoC V0 dimostra:

1. Un sistema con 6 unità segregate produce convergenza verificabile su almeno 10 task di micro bug fixing.
2. Il success rate di SCR è misurabilmente superiore o uguale alla baseline lineare su task con bug ambigui.
3. Il pruning pre-validation riduce il numero di chiamate a `pytest` rispetto a una validazione esaustiva.
4. Il trace permette di attribuire il successo o il fallimento a unità specifiche.
5. Il replay è deterministico: riletto con lo stesso campo iniziale, riproduce lo stesso outcome.
6. Il sistema produce fallimenti espliciti e distinti (timeout, instabilità, nessuna ipotesi valida) invece di silenzi o output non classificati.
7. Nessuna unità chiama direttamente un'altra unità: il vincolo è verificabile staticamente sul codice.
