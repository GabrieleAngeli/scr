# Segregated Competence Runtime — Technical Theory

> Version: 0.1 — Aligned with PoC V0  
> Date: 2026-04-28  
> Normative references: `ADR_0001_FIELD_BASED_COMPETENCE_RUNTIME.md`, `SCR_POC_REQUIREMENTS.md`, `ARCHITECTURE_V0.md`

---

## 1. Objective

The **Segregated Competence Runtime (SCR)** is a computational runtime designed to demonstrate that distinct specialised competences can cooperate and compete to produce verifiable convergence **without becoming a monolithic system**.

The goal is not to build an Artificial General Intelligence (AGI) system. The goal is to demonstrate a **verifiable computational model** with the following properties:

| Property | Description |
| --- | --- |
| Shared field | All units read and deform a single mutable state object |
| Segregated competences | Each unit has a bounded responsibility domain and cannot invoke other units directly |
| Selective activation | Units activate only when the field exceeds their sensitivity threshold |
| Controlled divergence | The system explores at least 3 independent hypotheses before converging |
| Competition and pruning | Hypotheses compete by score before being submitted to real validation |
| Real validation | Truth is not defined by an internal score but by the outcome of `pytest` |
| Explicit consolidation | Every run ends with a declared outcome: `SUCCESS`, `REOPENED`, or a specific failure state |
| Full traceability | Every activation, delta and decision is recorded in a serialisable trace |
| Deterministic replay | Every run can be re-read and compared, forming the basis for learning |

The PoC domain is deliberately narrow: **micro Python bug fixing**. This choice is not a limitation but a strategy: a small, verifiable domain makes it possible to measure computational dynamics without noise.

---

## 2. Theory

### 2.1 The problem SCR aims to solve

Automated reasoning systems tend to degenerate into one of these undesirable patterns:

1. **Linear orchestrator**: competences are executed in a fixed sequence, with no dynamic feedback between stages.
2. **Static rule engine**: rules are hardcoded, the system does not learn and does not adapt.
3. **Set of microservices**: units call each other via API/DTO, shifting the problem to distributed communication.
4. **Disguised monolithic LLM**: a single neural model simulates multiple units but collapses competences into an average behavior.
5. **Unstable system**: the field oscillates without convergence criteria, producing non-deterministic outputs.

SCR adopts a radically different principle: **units do not communicate with each other**. They communicate only by deforming a shared field.

### 2.2 The field model

The field (`FieldState`) is the sole communication medium between units. It is not a passive database: it is a dynamic state object that carries semantic information on every dimension.

```text
FieldState
├── task_signal          # raw input: task_id, task_path
├── context_map          # structured artifacts: code, AST, symbols, expected failures
├── salience_map         # perceived relevance of field regions (float 0–1)
├── hypothesis_pool      # active, pruned and validated hypotheses
├── energy_map           # available energy for units/regions
├── tension_map          # internal tension: indicator of contradiction or uncertainty
├── stability_score      # global convergence score of the field
├── activation_levels    # current activation level of each unit
├── trace                # structured log of every semantic event
├── tick                 # runtime time counter
├── outcome              # final run outcome
└── selected_hypothesis  # hypothesis consolidated as the solution
```

Each dimension has a precise computational meaning:

- **salience_map**: signals which field regions deserve attention. Units read it to decide whether to activate. Units write it to orient subsequent units.
- **tension_map**: represents internal contradiction. High tension on a hypothesis signals that units disagree on its value. The runtime uses tension to decide whether to force pruning or reopening.
- **energy_map**: models the computational cost assigned to units and hypotheses. A unit with low energy tends to decay.
- **stability_score**: global convergence measure. Drops when the field oscillates, rises when hypotheses stabilise.

### 2.3 Units as local operators

A competence unit (`CompetenceUnit`) is an operator that observes a snapshot of the field and produces a localised transformation.

The formal contract is:

```text
FieldState → FieldDelta
```

The minimal implemented interface is:

```python
class CompetenceUnit(ABC):
    name: str
    threshold: float    # minimum activation threshold
    sensitivity: float  # amplification of the incoming signal
    weight: float       # weight of the contribution to the field
    decay: float        # decay rate of the unit's own energy

    def activation(self, field: FieldState) -> float: ...
    def transform(self, field: FieldState) -> FieldDelta: ...
```

The runtime calls `activation(field)` for every unit and activates only those whose value exceeds `threshold`. The activated unit calls `transform(field)` and returns a `FieldDelta`. The runtime is the only component authorized to apply deltas to the field.

A unit **cannot**:

- modify `FieldState` directly;
- call methods of other units;
- read private memory of other units;
- validate or consolidate by bypassing the runtime;
- access undeclared external resources.

### 2.4 The tick cycle

The runtime executes discrete cycles called **ticks**. Each tick follows the sequence:

```text
observe → activate → transform → apply → update → validate → consolidate
```

In detail:

1. **observe**: every unit computes its own activation level by reading the field.
2. **activate**: the runtime selects units with `activation >= threshold`.
3. **transform**: selected units produce their `FieldDelta`.
4. **apply**: the runtime applies all deltas to the field in collection order.
5. **update**: the runtime recomputes `stability_score`, updates `energy_map` and `tension_map`.
6. **validate**: if there are `validating` hypotheses, the runtime submits them to `pytest`.
7. **consolidate**: if a validated hypothesis exists, the runtime promotes it to solution and terminates.

The runtime produces explicit outcomes:

| Outcome | Meaning |
| --- | --- |
| `SUCCESS` | At least one hypothesis passed real validation |
| `REOPENED` | All current hypotheses failed, but the field contains useful signals for reopening |
| `FAILED_NO_VALID_HYPOTHESIS` | No hypothesis remained in the pool after pruning and validation |
| `FAILED_TIMEOUT` | Maximum tick count reached without convergence |
| `FAILED_UNSTABLE_FIELD` | Average tension remained above threshold for too many consecutive ticks |
| `FAILED_VALIDATION` | Hypotheses exist but none passed validation |

### 2.5 The PoC competence units

PoC V0 implements six distinct units, each with bounded responsibility:

```text
InputStructuringUnit
  └── Transforms task_signal into structured artifacts in context_map.
      Populates salience on code, tests, failure_signal.

StandardizationUnit
  └── Analyses bug.py with AST. Extracts symbols, functions, classes.
      Increases salience on suspicious regions.

DivergenceUnit
  └── Generates ≥3 distinct hypotheses (operator fix, boundary, None,
      variable, return). Adds to hypothesis_pool via FieldDelta.

CompetitionUnit
  └── Assigns scores to hypotheses. Penalises duplicates.
      Performs pruning before validation.

ValidationUnit (ValidationGateUnit)
  └── Materialises patch in temporary workspace.
      Runs pytest. Updates hypothesis state in the field.

ConsolidationUnit
  └── Selects the best validated hypothesis. Emits the final outcome.
      Records metrics in the trace. Prepares the replay payload.
```

### 2.6 The communication protocol: Field Transformation Protocol (FTP-SCR)

**FTP-SCR** is the semantic standard internal to the runtime that governs how units interact with the field. It is not a network protocol.

The rules are:

- A unit **does not send messages** to another unit.
- A unit can only produce a `FieldDelta`.
- The runtime is the sole authorized intermediary.

The `FieldDelta` carries:

```text
FieldDelta
├── source_unit          # unit that produced the delta
├── salience_updates     # updates to field priorities
├── tension_updates      # updates to tension
├── energy_updates       # updates to energy
├── hypotheses_add       # new hypotheses to add to the pool
├── hypotheses_replace   # atomic replacement of the pool (used by CompetitionUnit)
├── hypotheses_remove    # hypotheses to remove by id
├── context_updates      # updates to context_map
├── stability_shift      # change in stability_score
├── outcome              # final outcome (if determined by this unit)
├── selected_hypothesis  # consolidated hypothesis (if determined by this unit)
└── trace_events         # semantic events to append to the trace
```

### 2.7 The learning model

SCR adopts **incremental, local and traceable** learning, not end-to-end neural training.

The reason is architectural: end-to-end training tends to collapse competences into a single average behavior, making communication opaque and reward attribution difficult.

Learning is structured across four levels:

| Level | Object learned | Method |
| --- | --- | --- |
| L1 Local | threshold, sensitivity, weight, decay per unit | adaptive tuning |
| L2 Field | stability and instability patterns | pattern memory |
| L3 Relational | synergies and inhibitions between units | influence matrix |
| L4 Episodic | outcomes, costs, branches, replay | episode store |

**Replay** is the core learning mechanism. Every run is serialised to JSON with:

- initial field;
- tick list;
- activated units and produced deltas;
- hypotheses created and removed;
- validation results;
- final outcome;
- parameters before and after the learning update.

Replay is not simple logging. It is the basis for retrospective reward attribution (**hindsight labeling**): after the fact, it is possible to identify which units contributed to success or failure and update their local parameters with clamping.

The PoC reward model:

```text
+1.0  hypothesis validated successfully
+0.3  useful pruning (elimination of unpromising hypotheses before validation)
+0.2  tension reduction without loss of valid hypotheses
-0.5  wasted validation (hypothesis sent to pytest without sufficient score)
-0.3  increase in field instability
-1.0  timeout or unstable field
```

### 2.8 Anti-collapse

SCR includes explicit mechanisms to prevent the most common structural degenerations:

| Risk | Mechanism |
| --- | --- |
| Single-unit dominance | Usage penalty for overly frequent units; limit on consecutive activations |
| Premature convergence | Diversity check on hypotheses; minimum hypothesis count before validation |
| Duplicate hypotheses | Similarity check before addition to the pool |
| Growing instability | Clamp on learnable parameters; explicit stop criteria |
| Overfitting on seen tasks | Replay on seen and new tasks; episode store separate from training |

---

## 3. Theses in favor of the theory

### Thesis 1 — Field-based communication is more expressive and safer than direct unit-to-unit communication

When units communicate via direct calls or DTOs, the communication structure is implicit in the dependency graph. Adding or removing a unit requires modifying all units that call it or receive its output.

With the field, the communication structure is **explicit and centralised in the field itself**. A unit can read the field enriched by any other unit without knowing who populated it. The runtime can add or remove units without modifying existing ones.

The operational proof in SCR: `InputStructuringUnit` populates `context_map["artifacts"]`. `StandardizationUnit` reads from there without knowing that `InputStructuringUnit` did it. `DivergenceUnit` reads `context_map["ast_summary"]` produced by `StandardizationUnit`. No unit knows the others.

### Thesis 2 — Real validation is the only computationally honest truth criterion

In many multi-agent systems, "validation" is internal: a hypothesis is promoted because it has a high score relative to other hypotheses. This is tautological: the score measures how much a hypothesis resembles what the system expects to see, not whether it is correct.

SCR adopts the opposite principle: **no hypothesis is valid simply because it has a high score**. Validation requires the real execution of `pytest` on a copy of the task with the patch applied.

This choice has a cost (validation is slow and expensive) that is consciously accepted because the PoC must demonstrate a verifiable model, not optimise an internal metric.

### Thesis 3 — Controlled divergence produces better solutions than premature convergence

A system that generates a single hypothesis and validates it immediately has a probability of success proportional to the quality of its first hypothesis. A system that generates at least 3 distinct hypotheses and makes them compete before validation has a probability of success proportional to the quality of its generation and selection mechanism.

The planned SCR benchmark against the linear baseline measures exactly this: the baseline generates one or a few hypotheses in a fixed sequence; SCR generates at least 3 divergent hypotheses, makes them compete and validates only the top-k. The expected metrics are:

- **success rate**: SCR > baseline for tasks with ambiguous bugs (multiple plausible causes);
- **false positives**: SCR < baseline thanks to pre-validation pruning;
- **useful reopenings**: available only in SCR, absent from the baseline.

### Thesis 4 — Competence segregation makes the system locally debuggable and improvable

In a monolithic system, incorrect behavior can originate anywhere in the system. It is not possible to attribute failure to a specific component without analysing the entire system.

In SCR, each unit has bounded responsibilities and produces an explicit trace of its own actions. If `DivergenceUnit` generates hypotheses that are too similar to each other, the problem is localised and measurable (similarity check fails, the pool is redundant). If `CompetitionUnit` performs excessive pruning, the trace shows how many hypotheses were eliminated and with what score.

The structured trace for every event includes:

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

This makes every decision traceable, reproducible and attributable.

### Thesis 5 — Local incremental learning is more stable and interpretable than end-to-end training

End-to-end training on a multi-agent system optimises a global objective by distributing gradients across all units. The expected result is that units converge towards behaviors that maximise the global objective, but **collapse their differences** because the gradient does not distinguish which unit contributed to which part of the outcome.

SCR instead adopts local adaptive tuning: each unit updates its own parameters (`threshold`, `sensitivity`, `weight`, `decay`) based on the reward attributed specifically to its contribution in the run, reconstructed via the trace.

The update rule is deliberately simple:

```python
new_value = old_value + learning_rate * reward * influence
```

With parameter clamping to prevent degenerations:

```text
threshold:   [0.05, 0.95]
sensitivity: [0.10, 5.00]
weight:      [0.10, 5.00]
decay:       [0.00, 0.50]
```

The simplicity is a deliberate choice: the PoC must first demonstrate the computational dynamics. Learning complexity can grow only after the dynamics have been verified.

### Thesis 6 — Episodic replay is superior to logging as a learning mechanism

A log records events. A replay records the state sufficient to reconstruct and reinterpret a complete run.

SCR's `ReplayRecorder` persists:

- initial and final field;
- each tick with activated units and produced deltas;
- hypotheses created, removed and validated;
- final outcome and selected hypothesis;
- timestamp for temporal ordering.

The `ReplayValidator` verifies that every replay respects structural invariants: required keys present, non-empty trace, strictly increasing seq values, selected hypothesis present in case of `SUCCESS`.

This structure makes it possible to apply **hindsight labeling**: after the fact, knowing that the run ended with `SUCCESS` and that hypothesis `hyp-003` was the correct one, it is possible to trace back through the trace and assign positive rewards to units that produced or reinforced `hyp-003`, and negative rewards to units that generated hypotheses later pruned or failed.

### Thesis 7 — A small, verifiable domain is the correct strategy for validating a new computational model

The domain choice — micro Python bug fixing with `pytest` — is not a limitation of the PoC. It is the correct strategy for validating a new computational model.

A large domain introduces confounding variables: it is not clear whether a failure depends on the computational model or on the complexity of the domain. A small domain with a real truth criterion (pytest passes or it does not) makes it possible to measure exactly the dynamics that SCR aims to demonstrate.

The transition to more complex domains (multi-file refactoring, security analysis, system design) is possible only after the model is validated in the small domain. SCR is designed for this: units are local operators, the field is generic, the runtime is parametric. Changing domain means adding or replacing units, not rewriting the runtime.

---

## 4. Evolutionary roadmap

| Version | Scope | Status |
| --- | --- | --- |
| V0 | Static runtime, 6 units, real validation, replay | In progress (PoC) |
| V1 | Adaptive tuning on threshold/weight/decay | Planned |
| V2 | Bandit / lightweight RL for unit and hypothesis selection | Planned |
| V3 | Targeted neural modules (standardization, divergence, competition) | Roadmap |

The progression is deliberate: each level of complexity is introduced only after the previous level has been empirically verified on benchmark tasks.

---

## 5. Theory acceptance criteria

The theory underlying SCR is confirmed if PoC V0 demonstrates:

1. A system with 6 segregated units produces verifiable convergence on at least 10 micro bug fixing tasks.
2. SCR's success rate is measurably greater than or equal to the linear baseline on tasks with ambiguous bugs.
3. Pre-validation pruning reduces the number of `pytest` calls compared to exhaustive validation.
4. The trace makes it possible to attribute success or failure to specific units.
5. Replay is deterministic: re-read with the same initial field, it reproduces the same outcome.
6. The system produces explicit and distinct failures (timeout, instability, no valid hypothesis) instead of silences or unclassified outputs.
7. No unit directly calls another unit: the constraint is statically verifiable in the code.
