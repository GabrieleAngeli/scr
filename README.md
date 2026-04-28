# Segregated Competence Runtime (SCR)

PoC of a shared-field computational runtime in which specialized competences cooperate and compete to produce verifiable convergence, without becoming a monolithic system.

The PoC domain is micro Python bug fixing. The truth criterion is the real outcome of `pytest`, not an internal score.

---

## Documentation Index

| Document | Contents |
| --- | --- |
| [README.md](README.md) | This file: quick reference, structure, commands |
| [README_IT.md](README_IT.md) | Italian version of this file |
| [THEORY.md](THEORY.md) | Objective, theory and theses in favor of the SCR model |
| [THEORY_IT.md](THEORY_IT.md) | Italian version of THEORY.md |
| [ARCHITECTURE_V0.md](ARCHITECTURE_V0.md) | V0 architecture: field, units, runtime, strategies |
| [SCR_POC_REQUIREMENTS.md](SCR_POC_REQUIREMENTS.md) | Full PoC requirements, learning layer, V0 acceptance criteria |
| [.context/ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md](.context/ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md) | ADR: Field Transformation Protocol, reward model, anti-collapse |
| [.context/SCR_CODEX_IMPLEMENTATION_PACK.md](.context/SCR_CODEX_IMPLEMENTATION_PACK.md) | Detailed implementation specifications for each unit and module |
| [.context/analysis_snapshot.md](.context/analysis_snapshot.md) | Current analytical snapshot: progress, risks, open questions |

---

## Core Principle

Units do not communicate with each other directly. They communicate only by deforming a shared field.

```text
FieldState → FieldDelta
```

The runtime is the only component authorized to apply deltas to the field.

---

## Project Structure

```text
SCR/
  src/scr/
    field.py          # FieldState: shared state object
    delta.py          # FieldDelta: transformation produced by a unit
    runtime.py        # SCRRuntime: tick cycle, apply_delta
    replay.py         # ReplayRecorder, ReplayLoader, ReplayValidator
    units/
      base.py               # CompetenceUnit: abstract contract
      input_structuring.py  # Reads task_signal, populates context_map
      standardization.py    # AST analysis, symbol extraction
      divergence.py         # Generates ≥3 distinct hypotheses
      competition.py        # Scoring, pre-validation pruning
      validation.py         # pytest on temporary workspace
      consolidation.py      # Final outcome, hypothesis selection
  tasks/
    task_001/
      bug.py        # Code to fix
      test_bug.py   # Reference tests
      meta.txt      # Metadata: expected failure, hints
  tests/            # pytest tests for each module
```

---

## Competence Units

| Unit | Responsibility |
| --- | --- |
| `InputStructuringUnit` | Transforms `task_signal` into structured artifacts: code, tests, expected failure |
| `StandardizationUnit` | Analyses `bug.py` with AST, extracts symbols and suspicious regions |
| `DivergenceUnit` | Generates ≥3 hypotheses with distinct patches or strategies |
| `CompetitionUnit` | Assigns scores, penalises duplicates, performs pre-validation pruning |
| `ValidationUnit` | Materialises patch in temporary workspace, runs `pytest`, updates hypothesis state |
| `ConsolidationUnit` | Selects the best valid hypothesis, emits the final outcome, prepares the replay payload |

---

## Tick Cycle

```text
observe → activate → transform → apply → update → validate → consolidate
```

Each tick, the runtime computes the activation level of every unit. Only units with `activation >= threshold` produce a `FieldDelta`. The runtime applies deltas in collection order and updates the field.

---

## Possible Outcomes

| Outcome | Meaning |
| --- | --- |
| `SUCCESS` | A hypothesis passed `pytest` |
| `REOPENED` | All current hypotheses failed, but the field contains useful signals |
| `FAILED_NO_VALID_HYPOTHESIS` | No hypothesis remained after pruning and validation |
| `FAILED_TIMEOUT` | Maximum tick count reached without convergence |
| `FAILED_UNSTABLE_FIELD` | Tension above threshold for too many consecutive ticks |
| `FAILED_VALIDATION` | Hypotheses exist but none passed `pytest` |

---

## Summary of THEORY.md

[THEORY.md](THEORY.md) documents three levels of understanding of the project.

**Objective**: SCR is not an AGI system. It is a verifiable computational model demonstrating how segregated competences can produce convergence through a shared field. The nine required properties — from the shared field to deterministic replay — define the boundary between SCR and the degenerate patterns it aims to avoid (linear orchestrator, static rule engine, microservices with DTOs, monolithic LLM).

**Theory**: The field (`FieldState`) is not a passive database but a semantic state object with distinct dimensions: `salience_map` for the perceived relevance of regions, `tension_map` for internal contradiction, `energy_map` for computational cost, `stability_score` for global convergence. Units are local operators that read a snapshot of the field and produce a `FieldDelta` without modifying the field directly. The runtime is the sole intermediary. The Field Transformation Protocol (FTP-SCR) formalises this separation. Learning is incremental across four levels (local, field, relational, episodic) with replay as the primary mechanism for retrospective reward attribution.

**7 theses in favor**:

1. Field-based communication is more expressive and safer than direct unit-to-unit communication because the dependency structure is explicit in the field, not implicit in the call graph.
2. Real validation via `pytest` is the only computationally honest truth criterion: an internal score is tautological.
3. Controlled divergence (≥3 hypotheses) produces better solutions than premature convergence on tasks with ambiguous bugs.
4. Competence segregation makes the system locally debuggable and improvable thanks to the per-unit structured trace.
5. Local incremental learning is more stable and interpretable than end-to-end training because it does not collapse competences into an average behavior.
6. Episodic replay is superior to logging because it enables hindsight labeling: retrospective reward attribution to specific units.
7. A small, verifiable domain is the correct strategy for validating a new computational model: confounding variables are minimised.

---

## Commands

```bash
# Run all tests
python -m pytest

# Run only input structuring tests
python -m pytest tests/test_input_structuring.py

# Run with verbose output
python -m pytest -v
```

---

## Technologies

- Python 3.9+ (compatible with the current workspace)
- `pytest` for real hypothesis validation and runtime testing
- `ast` for static analysis of Python code
- `subprocess` and `tempfile` for isolated patch execution
- `dataclasses` and `json` for serialisation of field, delta and replay
