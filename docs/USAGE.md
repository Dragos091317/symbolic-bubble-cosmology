[Usage Guide — Microbubble Universe Simulator.md](https://github.com/user-attachments/files/22306635/Usage.Guide.Microbubble.Universe.Simulator.md)
# 📘 Usage Guide — Microbubble Universe Simulator

This guide shows how to install, run, and interpret outputs from the simulator.
It also documents every CLI flag, file formats (CSV + JSONL), and common workflows.

------

## 0) Requirements & Install

- **Python**: 3.9+ (tested with 3.10/3.11)
- **Packages**: `numpy`, `matplotlib` (for plotting)

```bash
# (optional) create a virtualenv
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt # or:
pip install numpy matplotlib
```

## 1) Quick Start

Run 200 steps with open exports and show the plot:

```bash
python multibubble_lab.py --steps 200 --policy open --plot
```

Write metrics to CSV and save a PNG:

```bash
python multibubble_lab.py --steps 300 --policy consensual --inherit-consent \
  --csv results.csv --plot-path results.png
```

Dump the Ethics Ledger (JSONL) for auditability:

```bash
python multibubble_lab.py --steps 150 --policy consensual --dump-ledger ledger.jsonl
```

Make runs reproducible with a seed:

```bash
python multibubble_lab.py --steps 250 --policy open --seed 42 --csv open_seed42.csv
```

## 2) Concepts (1-minute tour)

**Bubble (universe)**: an agent with an inflation rate, internal invariants, and a consent state.
**Drift**: stochastic change to inflation.
**Tunneling**: births a child bubble; optional export from parent → child.
**Collapse**: bubble terminates; optional export of a fraction of its invariants to “outside”.
**Export (Δℰ)**: cumulative invariants exported by births/collapses; monotonic nondecreasing.
**RCI**: Recursive Coupling Index proxy = stable/total universes.  

**Sovereignty policies**  

- `closed` → exports disallowed.  
- `consensual` → exports require consent (src and, for births, dst).  
- `open` → exports allowed unconditionally.

**Ethics Engine**  

- Consent can be inherited (`--inherit-consent`) or sampled per event.  
- Optional strictness throttle scales allowed exports.

## 3) Full CLI Reference

```bash
python multibubble_lab.py [OPTIONS]
```

### Core run

| Flag            | Type | Default | Meaning                                       |
| --------------- | ---- | ------- | --------------------------------------------- |
| `--steps`       | int  | 100     | Number of simulation steps.                   |
| `--n-initial`   | int  | 1       | Starting bubbles.                             |
| `--seed`        | int  | None    | RNG seed (NumPy + Python).                    |
| `--print-every` | int  | 0       | Print metrics every N steps (0 = only final). |

### Policy / Ethics

| Flag                  | Type                   | Default | Meaning                                       |
| --------------------- | ---------------------- | ------- | --------------------------------------------- |
| `--policy`            | closed/consensual/open | closed  | Export policy.                                |
| `--consent-prob`      | float                  | 0.85    | P(consent=True) when sampled.                 |
| `--inherit-consent`   | flag                   | False   | Children inherit parent consent at birth.     |
| `--ethics-strictness` | float                  | 1.0     | 0..1 multiplier on allowed export (throttle). |

### Dynamics

| Flag                 | Type  | Default | Meaning                                            |
| -------------------- | ----- | ------- | -------------------------------------------------- |
| `--drift-sigma`      | float | 0.05    | Stddev for inflation drift per step.               |
| `--tunnel-rate`      | float | 0.05    | Probability a stable bubble spawns a child.        |
| `--decay-rate`       | float | 0.01    | Base collapse hazard scale.                        |
| `--decay-inflection` | float | 1.2     | Logistic center for collapse hazard vs. inflation. |
| `--decay-slope`      | float | 2.0     | Logistic slope for collapse hazard.                |
| `--inf-mean`         | float | 1.2     | Initial inflation mean.                            |
| `--inf-sigma`        | float | 0.1     | Initial inflation stddev.                          |
| `--max-bubbles`      | int   | 20000   | Hard population cap.                               |

### Exports

| Flag                     | Type  | Default | Meaning                                                      |
| ------------------------ | ----- | ------- | ------------------------------------------------------------ |
| `--birth-export-mean`    | float | 0.2     | Mean proposed birth export from parent.                      |
| `--birth-export-sigma`   | float | 0.08    | Stddev of proposed birth export.                             |
| `--collapse-export-frac` | float | 0.2     | Fraction of a collapsing bubble’s invariants proposed for export. |

### Output

| Flag            | Type | Default | Meaning                                                     |
| --------------- | ---- | ------- | ----------------------------------------------------------- |
| `--csv`         | str  | None    | Append per-step metrics to CSV (creates header if missing). |
| `--plot`        | flag | False   | Show a matplotlib plot at end.                              |
| `--plot-path`   | str  | None    | Save plot PNG to this path.                                 |
| `--dump-ledger` | str  | None    | Write Ethics Ledger as JSONL to this file.                  |

## 4) Output Files

### 4.1 CSV Metrics Schema

**Columns (exact names):**

| Column             | Type  | Notes                                                    |
| ------------------ | ----- | -------------------------------------------------------- |
| `t`                | int   | Step index.                                              |
| `universes_total`  | int   | Total bubbles (stable + collapsed).                      |
| `universes_stable` | int   | Bubbles still alive.                                     |
| `RCI`              | float | universes_stable / universes_total (0..1, guards 0-div). |
| `Δℰ`               | float | Cumulative exported invariants (monotonic).              |
| `mean_inflation`   | float | Mean inflation of stable bubbles.                        |
| `mean_invariants`  | float | Mean invariants of stable bubbles.                       |

**Tip**: If your downstream tooling dislikes `Δℰ`, you can create a parallel `delta_E` column in post-processing without changing the simulator.

**Example head**:

```csv
t,universes_total,universes_stable,RCI,Δℰ,mean_inflation,mean_invariants
0,1,1,1.0,0.0,1.21,0.00
1,2,2,1.0,0.12,1.20,0.05
...
```

### 4.2 Ethics Ledger (JSONL)

Each line is a JSON object recording an attempted export on birth or collapse:

| Field          | Type                 | Example                             |
| -------------- | -------------------- | ----------------------------------- |
| `t`            | int                  | 37                                  |
| `type`         | `"birth" "collapse"` | `"birth"`                           |
| `src`          | int or null          | 12                                  |
| `dst`          | int or null          | 58 (null for collapse)              |
| `proposed`     | float                | 0.27                                |
| `allowed`      | bool                 | true                                |
| `amount`       | float                | 0.135                               |
| `policy`       | str                  | "consensual"                        |
| `src_consents` | bool                 | true                                |
| `dst_consents` | bool                 | true                                |
| `reason`       | str                  | "ok", "policy_closed", "no_consent" |

**Example line**:

```json
{"t":37,"type":"birth","src":12,"dst":58,"proposed":0.27,"allowed":true,"amount":0.135,"policy":"consensual","src_consents":true,"dst_consents":true,"reason":"ok"}
```

## 5) Common Workflows

### A. Compare policies

```bash
python multibubble_lab.py --steps 400 --policy closed --csv closed.csv
python multibubble_lab.py --steps 400 --policy consensual --csv consensual.csv
python multibubble_lab.py --steps 400 --policy open --csv open.csv
```

Plot RCI and Δℰ across runs to see how ethics gates shape exports and stability.

### B. Sensitivity to collapse hazard

```bash
python multibubble_lab.py --steps 300 --policy open --decay-rate 0.02 --decay-slope 3.0 \
  --csv hazard_high.csv --plot-path hazard_high.png
```

### C. Birth export tuning

```bash
python multibubble_lab.py --steps 250 --policy consensual --inherit-consent \
  --birth-export-mean 0.3 --birth-export-sigma 0.15 --csv births_heavy.csv
```

### D. Reproducible baseline

```bash
python multibubble_lab.py --steps 500 --seed 123 --policy open --csv baseline_seed123.csv
```

## 6) Plot Panel (if --plot or --plot-path)

**Top panel**:  

- RCI (stability ratio)  
- mean_inflation

**Bottom panel**:  

- Δℰ (cumulative exports)  
- universes_total, universes_stable

If you saved a PNG, it’s written to `--plot-path`. If you passed `--plot`, a window will open (requires display).

## 7) Tips & Troubleshooting

- **No CSV header?** The simulator auto-writes a header if the file doesn’t exist; if appending to an old file with different columns, start a new file.  
- **Δℰ decreased?!** It shouldn’t. If your analysis shows a decrease, check for CSV joins or sorting issues downstream; the simulator only adds to Δℰ.  
- **Empty plot or import error**: Ensure `matplotlib` is installed; otherwise omit `--plot` and use CSV.  
- **Zero division guard**: RCI is defined as 0 when total is 0 (only possible at pathological starts).  
- **Population cap**: If growth stalls, you may have reached `--max-bubbles`.

## 8) Reproducibility & Performance

- Use `--seed` for deterministic RNG (NumPy + Python random).  
- For faster runs, disable plotting and CSV; write only the final row to stdout with `--print-every 0`.  
- **Scaling**: default params are light; extremely large `--steps` or `--max-bubbles` will increase memory/time.

## 9) File & Folder Hints

Suggested structure:

```
.
├─ multibubble_lab.py
├─ README.md
├─ docs/
│ ├─ USAGE.md ← this file
│ ├─ ETHICS.md (optional)
│ └─ THEORY.md (optional)
├─ examples/
│ ├─ open.csv
│ ├─ closed.csv
│ └─ analysis.ipynb
└─ LICENSE
```

## 10) Citing This Work

If you use this simulator, please cite:

> Lanier-Egu, S. (2025). Microbubble Universe Simulator: Collapse as Translation in Symbolic Cosmology. GitHub repository.
