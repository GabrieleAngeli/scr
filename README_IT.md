# Segregated Competence Runtime (SCR)

PoC di un runtime computazionale a campo condiviso in cui competenze specializzate cooperano e competono per produrre convergenza verificabile, senza diventare un sistema monolitico.

Il dominio del PoC è micro bug fixing Python. Il criterio di verità è l'esito reale di `pytest`, non uno score interno.

---

## Indice documentazione

| Documento | Contenuto |
| --- | --- |
| [README.md](README.md) | Versione inglese di questo file |
| [README_IT.md](README_IT.md) | Questo file: guida rapida, struttura, comandi |
| [THEORY.md](THEORY.md) | Versione inglese: obiettivo, teoria e tesi a favore del modello SCR |
| [THEORY_IT.md](THEORY_IT.md) | Obiettivo, teoria e tesi a favore del modello SCR |
| [ARCHITECTURE_V0.md](ARCHITECTURE_V0.md) | Architettura V0: field, unit, runtime, strategie |
| [SCR_POC_REQUIREMENTS.md](SCR_POC_REQUIREMENTS.md) | Requisiti completi del PoC, learning layer, criteri V0 |
| [.context/ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md](.context/ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md) | ADR: Field Transformation Protocol, reward model, anti-collasso |
| [.context/SCR_CODEX_IMPLEMENTATION_PACK.md](.context/SCR_CODEX_IMPLEMENTATION_PACK.md) | Specifiche implementative dettagliate per ogni unità e modulo |
| [.context/analysis_snapshot.md](.context/analysis_snapshot.md) | Snapshot analitico corrente: progressi, rischi, domande aperte |

---

## Principio fondamentale

Le unità non comunicano tra loro direttamente. Comunicano solo deformando un campo condiviso.

```text
FieldState → FieldDelta
```

Il runtime è l'unico componente autorizzato ad applicare i delta al campo.

---

## Struttura del progetto

```text
SCR/
  src/scr/
    field.py          # FieldState: oggetto di stato condiviso
    delta.py          # FieldDelta: trasformazione prodotta da un'unità
    runtime.py        # SCRRuntime: ciclo a tick, apply_delta
    replay.py         # ReplayRecorder, ReplayLoader, ReplayValidator
    units/
      base.py               # CompetenceUnit: contratto astratto
      input_structuring.py  # Legge task_signal, popola context_map
      standardization.py    # Analisi AST, estrazione simboli
      divergence.py         # Genera ≥3 ipotesi distinte
      competition.py        # Scoring, pruning pre-validation
      validation.py         # pytest su workspace temporaneo
      consolidation.py      # Outcome finale, selezione ipotesi
  tasks/
    task_001/
      bug.py        # Codice da correggere
      test_bug.py   # Test di riferimento
      meta.txt      # Metadati: failure atteso, hint
  tests/            # Test pytest per ogni modulo
```

---

## Unità di competenza

| Unità | Responsabilità |
| --- | --- |
| `InputStructuringUnit` | Trasforma `task_signal` in artefatti leggibili: codice, test, failure atteso |
| `StandardizationUnit` | Analizza `bug.py` con AST, estrae simboli e regioni sospette |
| `DivergenceUnit` | Genera ≥3 ipotesi con patch o strategie distinte |
| `CompetitionUnit` | Assegna score, penalizza duplicati, effettua pruning pre-validazione |
| `ValidationUnit` | Materializza patch in workspace temporaneo, esegue `pytest`, aggiorna stato ipotesi |
| `ConsolidationUnit` | Seleziona l'ipotesi valida migliore, emette l'outcome finale, predispone il replay |

---

## Ciclo a tick

```text
observe → activate → transform → apply → update → validate → consolidate
```

Ogni tick il runtime calcola il livello di attivazione di ogni unità. Solo le unità con `activation >= threshold` producono un `FieldDelta`. Il runtime applica i delta nell'ordine di raccolta e aggiorna il campo.

---

## Outcome possibili

| Outcome | Significato |
| --- | --- |
| `SUCCESS` | Un'ipotesi ha superato `pytest` |
| `REOPENED` | Tutte le ipotesi attuali hanno fallito, ma il campo ha segnali utili |
| `FAILED_NO_VALID_HYPOTHESIS` | Nessuna ipotesi rimasta dopo pruning e validazione |
| `FAILED_TIMEOUT` | Numero massimo di tick raggiunto senza convergenza |
| `FAILED_UNSTABLE_FIELD` | Tensione sopra soglia per troppi tick consecutivi |
| `FAILED_VALIDATION` | Ipotesi esistenti ma nessuna supera `pytest` |

---

## Sintesi di THEORY_IT.md

[THEORY_IT.md](THEORY_IT.md) documenta tre livelli di comprensione del progetto.

**Obiettivo**: SCR non è un sistema AGI. È un modello computazionale verificabile che dimostra come competenze segregate possano produrre convergenza attraverso un campo condiviso. Le nove proprietà richieste — dal campo condiviso al replay deterministico — definiscono il confine tra SCR e i pattern degenerati che intende evitare (orchestratore lineare, rule engine statico, microservizi con DTO, LLM monolitico).

**Teoria**: Il campo (`FieldState`) non è un database passivo ma un oggetto di stato semantico con dimensioni distinte: `salience_map` per la rilevanza percepita delle regioni, `tension_map` per la contraddizione interna, `energy_map` per il costo computazionale, `stability_score` per la convergenza globale. Le unità sono operatori locali che leggono una snapshot del campo e producono un `FieldDelta` senza modificare il campo direttamente. Il runtime è l'unico intermediario. Il Field Transformation Protocol (FTP-SCR) formalizza questa separazione. Il learning è incrementale a quattro livelli (locale, campo, relazionale, episodico) con replay come meccanismo portante per l'attribuzione retrospettiva dei reward.

**7 tesi a favore**:

1. La comunicazione via campo è più espressiva e sicura della comunicazione diretta perché la struttura delle dipendenze è esplicita nel campo, non implicita nel grafo delle chiamate.
2. La validazione reale tramite `pytest` è l'unico criterio di verità computazionalmente onesto: uno score interno è tautologico.
3. La divergenza controllata (≥3 ipotesi) produce soluzioni migliori della convergenza prematura su task con bug ambigui.
4. La segregazione delle competenze rende il sistema debuggabile e migliorabile localmente grazie al trace strutturato per unità.
5. Il learning locale incrementale è più stabile e interpretabile del training end-to-end perché non collassa le competenze in un comportamento medio.
6. Il replay episodico è superiore al logging perché permette hindsight labeling: l'attribuzione retrospettiva dei reward alle unità specifiche.
7. Il dominio piccolo e verificabile è la strategia corretta per validare un modello computazionale nuovo: le variabili confondenti sono minimizzate.

---

## Comandi

```bash
# Eseguire tutti i test
python -m pytest

# Eseguire solo i test di input structuring
python -m pytest tests/test_input_structuring.py

# Eseguire con output verboso
python -m pytest -v
```

---

## Tecnologie

- Python 3.9+ (compatibile con il workspace corrente)
- `pytest` per validazione reale delle ipotesi e test del runtime
- `ast` per analisi statica del codice Python
- `subprocess` e `tempfile` per esecuzione isolata delle patch
- `dataclasses` e `json` per serializzazione di field, delta e replay
