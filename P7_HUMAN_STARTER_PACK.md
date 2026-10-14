# Human-Arm Starter Pack — DO NOT read the assisted results first

> Blinding rule: do NOT open `P7_PILOT_ASSISTED.json`, `P5_EXECUTION.json`,
> or `p5_execute.py` oracles until your own runs are recorded. Work from the
> specs below only — same information the assisted arm's intent builder had.

## Task 1 — round-robin-arbiter (mutants to kill: 2)

**Behavioral spec.** 4 requesters (indices 0–3). State: `last` = index last
granted, init 3. On `grant(req[4])`: scan indices `(last+1)%4, (last+2)%4, …`
in order; grant the first with `req[i]==1` and set `last=i`. If none
requesting, return -1 and leave `last` unchanged.

**Your job.** Write a checker (Python or SVA or directed test — your choice)
that, given a request vector sequence, verifies (a) grant validity (granted
index was requesting; -1 iff none requesting), (b) round-robin order on
all-ones vectors (expect rotation 0,1,2,3 from init), (c) run it against the
golden model (expect zero violations) and 2 seeded mutants (expect kills).

## Task 2 — interrupt-controller (mutants to kill: 3)

**Behavioral spec.** 4 sources, priorities `prio=[1,2,3,4]` (higher number =
higher priority), threshold register = 1. `raise_irq(i)` sets pending bit.
`winner()` = highest-priority pending source with `prio > threshold`, else -1.
`claim(i)` clears pending bit `i`.

**Your job.** Same shape: verify winner correctness (multi-source vector
{0,2,3} → expect 3; edge vector {0}-only → expect -1 since prio 1 is not >
threshold 1), claim-clears behavior, then golden (zero violations) + 3
seeded mutants (expect kills).

## Timeboxes (hard caps, runbook rule)
- Read spec + author artifacts: log as **authoring** minutes.
- Each debug cycle (run → inspect → fix): **1 iteration**, log it.
- Self/peer review at end: log **review** minutes + reviewer initials.
- **4 hours max per task.** Stuck time counts — report it, it's data.

## Starter timesheet file
Copy `P7_PILOT_HUMAN_TEMPLATE.json` → `P7_PILOT_HUMAN_<initials>.json`,
fill it as you go (append rows, never edit recorded rows).
