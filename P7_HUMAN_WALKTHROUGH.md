# Human-Arm Walkthrough — Starter Edition (read this first)

> You do **not** need chip-design experience. You need basic Python and the
> willingness to follow steps exactly. If you can write a function, compare
> two lists, and run a script, you can do this.
> Estimated total: one focused afternoon (max 4 hours per task + setup).

## 0. What you are doing, in plain words

Somewhere in this project an AI pipeline checks hardware designs for bugs.
We need to know: **is a human working alone faster, slower, or equal?**
You are the human baseline. You will test two tiny pretend-hardware blocks
by writing small Python checkers, run them against correct and deliberately
broken versions, and write down your times. That's the whole job.

## 1. What you need installed (with checks)

Open **PowerShell** (press Win key, type `PowerShell`, Enter). Run:

```powershell
python --version
```
You should see `Python 3.11` (any 3.10+ is fine). If Python is missing,
install it from python.org (tick "Add python.exe to PATH" during install),
then close and reopen PowerShell.

```powershell
git --version
```
You should see a version number. If missing, install Git for Windows
(git-scm.com, accept all defaults).

## 2. Get the code (copy-paste, one line at a time)

```powershell
cd $HOME
git clone https://github.com/aiquanticinsights-commits/AIQ-VeriClave.git
cd AIQ-VeriClave
git rev-parse HEAD
```
The last command prints a long code like `49aa428…`. **Write it down** —
it goes into your timesheet as `repo_commit` (it proves exactly which code
you worked against).

## 3. The blinding rule (read twice, it matters most)

To keep the experiment fair, you must work **without knowing the expected
answers**. Concretely, do NOT open these until your runs are recorded:
- `P7_PILOT_ASSISTED.json` (the AI's results)
- `P5_EXECUTION.json`
- the oracle/checker functions inside `p5_execute.py` (you MAY look at the
  `FAMILIES` mutant-name list — names only — but not at functions that say
  what correct behavior is)

Allowed: this file, `P7_HUMAN_STARTER_PACK.md` (specs), `PILOT_PROTOCOL.md`,
`HUMAN_ARM_RUNBOOK.md`, Python docs, Google/StackOverflow for *Python
language* questions. **Not allowed**: AI assistants (Copilot, ChatGPT, etc.)
— this arm measures unassisted humans; using AI voids the run.

## 4. Vocabulary (five words, then you're fluent)

- **Block (DUT)**: the pretend-hardware piece under test ("device under test").
- **Checker/oracle**: YOUR Python code that decides pass/fail for a behavior.
- **Mutant**: a deliberately broken copy of the block (e.g. a flag forced to 0).
- **Kill**: your checker reports a failure on a mutant. A mutant your checker
  misses is called **survived** — that's a finding about your checker, not
  a personal failure. Report it.
- **False alarm**: your checker fails on the *correct* version. Must be zero
  at the end — go back and fix your checker if this happens.
- **Iteration**: one full cycle of run → look → fix. Count them with tally marks.

## 5. Warm-up exercise (15 min, toy example — do this first)

This teaches the exact loop on a trivial block, so the real tasks feel familiar.

**5a.** Create a folder OUTSIDE the repo (keeps the repo clean):
```powershell
mkdir $HOME\pilot-work; cd $HOME\pilot-work
```

**5b.** Create `warmup.py` with any editor (Notepad works; VS Code is nicer):
```python
# TOY block: 2-input AND gate with memory of nothing. Spec:
# out is 1 only when a==1 and b==1, otherwise 0.

def golden(a, b):
    return 1 if (a == 1 and b == 1) else 0

def mutant_or_instead_of_and(a, b):
    return 1 if (a == 1 or b == 1) else 0

def my_checker(fn):
    """Return list of failure strings; empty means pass."""
    failures = []
    for a in (0, 1):
        for b in (0, 1):
            if fn(a, b) != golden(a, b):
                failures.append(f"a={a},b={b}: got {fn(a,b)}, want {golden(a,b)}")
    return failures

print("golden violations:", my_checker(golden))          # expect []
print("mutant violations:", my_checker(mutant_or_instead_of_and))  # expect non-empty
```

**5c.** Run it:
```powershell
python warmup.py
```
Expected output: `golden violations: []` (zero false alarms) and one line
listing mutant failures (mutant killed). **You just did the whole workflow**:
write checker → run on correct version → run on broken version → record.

## 6. Task 1 — round-robin-arbiter (cap: 4 hours)

**What it is, in plain words.** Four people (0–3) raise hands (`req` list of
0/1). The arbiter picks one to serve (`grant` returns an index, or -1 if no
hands). Fairness rule: serve them in rotating order — whoever was served
last goes to the back of the queue. It remembers `last` (starts at 3).

Worked trace (all hands up, `last` starts at 3): check index
(3+1)%4=0 → hand up → grant **0**, `last`=0. Next: (0+1)=1 → grant **1**.
Then **2**, **3**, then wraps to **0**. Rotation: 0,1,2,3,0,1,2,3…

**Your two mutants** (implement each as a small variant function, like the
warm-up mutant):
- `fixed-priority`: always serves the lowest-numbered raised hand (ignores rotation).
- `grant-stuck`: keeps serving the same index over and over.

**Do this:**
1. Start a phone/clock timer. Write start time in your JSON (`started`).
2. Write `arbiter.py` in `$HOME\pilot-work`: a golden model (follow the spec
   above), your checker (grant validity: served hand was raised; -1 iff none
   raised; rotation order on all-hands-up), then run golden (want: zero
   violations) and both mutants (want: violations). Log minutes as
   `authoring_min`. Each fix cycle = +1 `iterations`.
3. Self-review your checker once (re-read it top to bottom), log `review_min`.

## 7. Task 2 — interrupt-controller (cap: 4 hours)

**What it is, in plain words.** Four alarm lines with importances
`prio=[1,2,3,4]` (4 = most important). A threshold dial is set to 1: only
alarms *more* important than 1 count (`>` strictly — importance exactly 1
does NOT count). `winner()` returns the most important counting alarm, or -1
if none counts. `claim(i)` switches alarm `i` off.

Worked trace: raise alarms 0, 2, 3 → counting set = {2 (prio 3), 3 (prio 4)}
(alarm 0 has prio 1, not > 1, so excluded) → winner **3**. After `claim(3)`:
pending {0,2} → counting {2} → winner **2**. Edge case: raise ONLY alarm 0
→ nothing counts → winner **-1** (test this — it catches real bugs).

**Your three mutants:** `threshold-ignored` (counts alarm 0 too),
`priority-inverted` (picks least important), `claim-no-clear` (claim does
nothing — verify by checking the alarm is still pending after claiming).

Same loop as Task 1: author → golden (zero violations) → mutants (kills) →
review. Log everything the same way.

## 8. Fill the timesheet (field by field)

```powershell
copy C:\Projects\ChipDesign\AIQ-VeriClave\P7_PILOT_HUMAN_TEMPLATE.json $HOME\pilot-work\P7_PILOT_HUMAN_<your-initials>.json
```
(Replace `<your-initials>`, e.g. `SS` → `P7_PILOT_HUMAN_SS.json`.)
Open it in any editor and fill: `engineer`, `repo_commit` (from step 2),
per task: `authoring_min`, `iterations`, `review_min` + `reviewer`,
`defects` (e.g. `"2/2"`), `false_alarms` (must end at 0), `artifacts`
(filenames you wrote), `notes` (anything odd, including stuck time),
`finished` timestamp, and finally `satisfaction` 1–5 with one honest line.

## 9. Submit (copy-paste git, no experience needed)

```powershell
cd C:\Projects\ChipDesign\AIQ-VeriClave
git checkout -b pilot/human-<initials-lowercase>
copy $HOME\pilot-work\P7_PILOT_HUMAN_<initials>.json .
git add P7_PILOT_HUMAN_<initials>.json
git commit -m "[pilot] human-arm results <initials>"
git push -u origin pilot/human-<initials-lowercase>
```
Then open `github.com/aiquanticinsights-commits/AIQ-VeriClave` in a browser →
you'll see a yellow **Compare & pull request** banner → click it → title
`[pilot] human-arm results <initials>` → Create. Done — a maintainer runs
the blinded comparison (they see only artifacts + evidence, never your
process notes first).

## 10. FAQ for starters
- **Running the interactive runner instead?** If an operator drives `pilot_human.py` for your session, your checker file needs one extra contract: set a global `RESULT` dict with keys `defects_found`, `mutants_total`, `false_alarms`, `iterations`, `artifacts` (list). The runner executes it isolated and records only that dict — it never reads your logic. Timers, questions, and sealing are handled for you; everything in §§6–9 above still applies to *your* work.

- **Stuck?** Stuck time is data — log it in `notes` and keep going; the 4h cap protects you. Ask methodology questions anytime (in the PR or an issue); you just won't be told expected results.
- **My checker disagrees with the spec?** Re-read the spec sheet first; if still conflicted, write down BOTH interpretations in `notes` and pick one. Ambiguity reports are valuable findings.
- **Can I use my own tools (pytest, VS Code debugger)?** Yes — anything except AI assistants and the forbidden files in §3.
- **What if a mutant survives?** Record it exactly as-is (`defects: "1/2"` etc.). A survive is a finding about checker strength, and the program treats findings as first-class results.
- **What happens after?** Blinded grading → E4 verdict (PASS/FAIL with numbers, same as every gate in this program) → ledger entry. You'll be credited in the verdict record.
