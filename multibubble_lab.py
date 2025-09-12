#Multiverse / Bubble Cosmology — simulator with CSV, plotting, and ethical protocol (BC-REP style)

#Nodes: bubble universes
#Drift: each bubble has its own inflation rate
#Boosts: tunneling events spawn new universes
#Collapse: false-vacuum decay wipes bubbles
#Metrics: RCI (stable / total), Δℰ (exported invariants)

#Ethical sovereignty (Observer/BC-REP flavored):
#- closed: no cross-boundary export (birth or collapse)
#- consensual: export allowed only with consent ledger OK, scaled (default 0.5)
#- open: export always allowed (scale 1.0)

#New:
#- EthicsEngine with consent ledger, inheritance, and event audits
#- Matplotlib plotting (--plot) and optional PNG export (--plot-path)
#- CSV logging (--csv) of per-step metrics

import argparse, csv, os, sys, math, random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import numpy as np


# ------------------------------
# Sovereignty policy
# ------------------------------
class SovereigntyPolicy:
    def __init__(self, mode: str):
        if mode not in ("closed", "consensual", "open"):
            raise ValueError("policy must be 'closed', 'consensual', or 'open'")
        self.mode = mode

    def scale(self) -> float:
        return 1.0 if self.mode == "open" else (0.5 if self.mode == "consensual" else 0.0)

    @property
    def allows_export(self) -> bool:
        return self.mode in ("consensual", "open")


# ------------------------------
# Ethics Engine (BC-REP mini)
# ------------------------------
@dataclass
class EthicsConfig:
    # Probability a bubble opts-in to exports if consent required
    consent_prob: float = 0.85
    # If True, children inherit parent consent at birth (can mutate later)
    inherit_consent: bool = True
    # Strictness multiplier (0–1): scales allowed exports even when permitted
    strictness: float = 1.0   # 1.0 = no reduction; 0.7 = throttle 30%


@dataclass
class EthicsEngine:
    policy: SovereigntyPolicy
    cfg: EthicsConfig = field(default_factory=EthicsConfig)
    # Ledger of all attempted exports (birth/collapse)
    ledger: List[Dict] = field(default_factory=list)

    def decide_consent(self, current: Optional[bool] = None) -> bool:
        """If consent state unknown, sample one."""
        if current is not None:
            return current
        return random.random() < self.cfg.consent_prob

    def check_and_record(
        self,
        t: int,
        ev_type: str,            # "birth" or "collapse"
        src_id: Optional[int],
        dst_id: Optional[int],
        proposed_amt: float,
        src_consents: bool,
        dst_consents: bool,
    ) -> Tuple[bool, float, str]:
        """
        Returns: (allowed, scaled_amount, reason)
        - Enforcement: by policy + consent + strictness scaling
        """
        reason = "ok"
        allowed = True
        amt = proposed_amt

        if not self.policy.allows_export:
            allowed = False
            reason = "policy_closed"
        elif self.policy.mode == "consensual":
            # Require consent of source; if a dst exists (birth), require dst too
            if not (src_consents and (dst_consents if dst_id is not None else True)):
                allowed = False
                reason = "no_consent"
            else:
                amt *= self.policy.scale() * self.cfg.strictness
        else:  # open
            amt *= self.policy.scale() * self.cfg.strictness

        amt = max(0.0, float(amt))

        self.ledger.append({
            "t": int(t),
            "type": ev_type,
            "src": src_id,
            "dst": dst_id,
            "proposed": float(proposed_amt),
            "allowed": bool(allowed),
            "amount": float(amt if allowed else 0.0),
            "policy": self.policy.mode,
            "src_consents": bool(src_consents),
            "dst_consents": bool(dst_consents),
            "reason": reason,
        })
        return allowed, amt, reason


# ------------------------------
# Bubble universe
# ------------------------------
@dataclass
class Bubble:
    id: int
    inflation_rate: float
    invariants: float = 0.0
    stable: bool = True
    parent_id: Optional[int] = None
    consent: Optional[bool] = None   # sovereignty consent flag (None => undecided)


# ------------------------------
# Multiverse
# ------------------------------
class Multiverse:
    def __init__(
        self,
        # init
        n_initial:int=1,
        seed:Optional[int]=None,
        # policy/ethics
        policy:str="closed",
        ethics_cfg: EthicsConfig = EthicsConfig(),
        # dynamics
        drift_sigma:float=0.05,
        tunnel_rate:float=0.05,
        decay_rate:float=0.01,
        decay_inflection:float=1.2,
        decay_slope:float=2.0,
        # exports
        birth_export_mean:float=0.2,
        birth_export_sigma:float=0.08,
        collapse_export_frac:float=0.2,
        max_bubbles:int=20000,
        inf_mean:float=1.2,
        inf_sigma:float=0.1,
    ):
        # RNG
        self.rng = np.random.default_rng(seed)
        random.seed(seed)
        self.policy = SovereigntyPolicy(policy)
        self.ethics = EthicsEngine(self.policy, ethics_cfg)

        self.drift_sigma = float(drift_sigma)
        self.tunnel_rate = float(tunnel_rate)
        self.decay_rate = float(decay_rate)
        self.decay_inflection = float(decay_inflection)
        self.decay_slope = float(decay_slope)
        self.birth_export_mean = float(birth_export_mean)
        self.birth_export_sigma = float(birth_export_sigma)
        self.collapse_export_frac = float(collapse_export_frac)
        self.max_bubbles = int(max_bubbles)

        self.universes: List[Bubble] = []
        for _ in range(n_initial):
            inf = max(0.0, float(self.rng.normal(inf_mean, inf_sigma)))
            consent = self.ethics.decide_consent(None)
            self.universes.append(Bubble(inflation_rate=inf, invariants=0.0, id=len(self.universes), consent=consent))
        self.t = 0
        self.exported_total = 0.0

    # ------------------ dynamics ------------------
    def _collapse_prob(self, u: Bubble) -> float:
        # logistic around decay_inflection; base scaled hazard
        x = u.inflation_rate - self.decay_inflection
        logistic = 1.0 / (1.0 + math.exp(-self.decay_slope * x))
        p = self.decay_rate * (0.5 + logistic)   # range ~ [0.5*base, 1.5*base]
        return min(0.95, max(0.0, p))

    def step(self):
        self.t += 1
        new_universes: List[Bubble] = []

        # drift + production + tunneling + collapse
        for u in self.universes:
            if not u.stable:
                continue

            # drift
            u.inflation_rate = max(0.0, u.inflation_rate + float(self.rng.normal(0.0, self.drift_sigma)))

            # internal production (simple: grows with inflation)
            u.invariants += 0.05 + 0.15 * u.inflation_rate

            # tunneling (spawn child)
            if len(self.universes) + len(new_universes) < self.max_bubbles:
                if self.rng.random() < self.tunnel_rate:
                    child_inf = max(0.0, float(self.rng.normal(u.inflation_rate, 0.05)))
                    # child consent: inherit or fresh draw
                    child_consent = u.consent if self.ethics.cfg.inherit_consent else self.ethics.decide_consent(None)
                    child = Bubble(
                        id=len(self.universes) + len(new_universes),
                        inflation_rate=child_inf,
                        invariants=0.0,
                        parent_id=u.id,
                        consent=child_consent,
                    )

                    # birth export proposal
                    proposed = max(0.0, float(self.rng.normal(self.birth_export_mean, self.birth_export_sigma)))
                    proposed = min(proposed, u.invariants)
                    allowed, amt, _ = self.ethics.check_and_record(
                        t=self.t, ev_type="birth",
                        src_id=u.id, dst_id=child.id,
                        proposed_amt=proposed,
                        src_consents=self.ethics.decide_consent(u.consent),
                        dst_consents=self.ethics.decide_consent(child.consent),
                    )
                    if allowed and amt > 0:
                        u.invariants -= amt
                        child.invariants += amt
                        self.exported_total += amt

                    new_universes.append(child)

            # collapse
            if self.rng.random() < self._collapse_prob(u):
                # on collapse, optionally export a fraction of invariants
                proposed = self.collapse_export_frac * u.invariants
                allowed, amt, _ = self.ethics.check_and_record(
                    t=self.t, ev_type="collapse",
                    src_id=u.id, dst_id=None,
                    proposed_amt=proposed,
                    src_consents=self.ethics.decide_consent(u.consent),
                    dst_consents=True,   # no specific recipient modeled
                )
                if allowed and amt > 0.0:
                    self.exported_total += amt
                u.invariants = 0.0
                u.stable = False

        if new_universes:
            self.universes.extend(new_universes)

    # ------------------ metrics ------------------
    def metrics(self) -> Dict[str, float]:
        total = len(self.universes)
        stable = sum(1 for u in self.universes if u.stable)
        mean_inf = float(np.mean([u.inflation_rate for u in self.universes if u.stable])) if stable else 0.0
        mean_inv = float(np.mean([u.invariants for u in self.universes if u.stable])) if stable else 0.0
        return {
            "t": int(self.t),
            "universes_total": int(total),
            "universes_stable": int(stable),
            "RCI": float(stable / total) if total else 0.0,
            "Δℰ": float(self.exported_total),
            "mean_inflation": mean_inf,
            "mean_invariants": mean_inv,
        }


# ------------------------------ CLI / run ------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Multiverse bubble cosmology with CSV, plotting, and BC-REP-style ethics")
    # run
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--n-initial", type=int, default=1)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--print-every", type=int, default=0)

    # policy
    p.add_argument("--policy", choices=["closed", "consensual", "open"], default="closed")

    # ethics
    p.add_argument("--consent-prob", type=float, default=0.85, help="probability a bubble opts-in to exports")
    p.add_argument("--inherit-consent", action="store_true", help="children inherit parent consent at birth")
    p.add_argument("--ethics-strictness", type=float, default=1.0, help="0..1 additional throttle on allowed exports")

    # dynamics
    p.add_argument("--drift-sigma", type=float, default=0.05)
    p.add_argument("--tunnel-rate", type=float, default=0.05)
    p.add_argument("--decay-rate", type=float, default=0.01)
    p.add_argument("--decay-inflection", type=float, default=1.2)
    p.add_argument("--decay-slope", type=float, default=2.0)
    p.add_argument("--inf-mean", type=float, default=1.2)
    p.add_argument("--inf-sigma", type=float, default=0.1)
    p.add_argument("--max-bubbles", type=int, default=20000)

    # exports
    p.add_argument("--birth-export-mean", type=float, default=0.2)
    p.add_argument("--birth-export-sigma", type=float, default=0.08)
    p.add_argument("--collapse-export-frac", type=float, default=0.2)

    # output
    p.add_argument("--csv", type=str, default=None, help="write per-step metrics to CSV file")
    p.add_argument("--plot", action="store_true", help="plot RCI, Δℰ, mean inflation, population at the end")
    p.add_argument("--plot-path", type=str, default=None, help="if set, save plot PNG to this path")
    p.add_argument("--dump-ledger", type=str, default=None, help="write ethics ledger (JSONL)")

    return p.parse_args(argv)


def run(args):
    ethics_cfg = EthicsConfig(
        consent_prob=args.consent_prob,
        inherit_consent=args.inherit_consent,
        strictness=args.ethics_strictness,
    )
    sim = Multiverse(
        n_initial=args.n_initial,
        seed=args.seed,
        policy=args.policy,
        ethics_cfg=ethics_cfg,
        drift_sigma=args.drift_sigma,
        tunnel_rate=args.tunnel_rate,
        decay_rate=args.decay_rate,
        decay_inflection=args.decay_inflection,
        decay_slope=args.decay_slope,
        birth_export_mean=args.birth_export_mean,
        birth_export_sigma=args.birth_export_sigma,
        collapse_export_frac=args.collapse_export_frac,
        max_bubbles=args.max_bubbles,
        inf_mean=args.inf_mean,
        inf_sigma=args.inf_sigma,
    )

    # prepare CSV if requested
    writer = None
    csvfile = None
    if args.csv:
        need_header = not os.path.exists(args.csv)
        csvfile = open(args.csv, "a", newline="", encoding="utf-8")
        writer = csv.DictWriter(csvfile, fieldnames=[
            "t","universes_total","universes_stable","RCI","Δℰ","mean_inflation","mean_invariants"
        ])
        if need_header:
            writer.writeheader()
        # write t=0
        if writer:
            writer.writerow(sim.metrics())

    # in-memory track for plotting
    history: List[Dict[str, float]] = [sim.metrics()]

    # single pass with optional periodic prints
    if args.print_every > 0:
        print(history[-1])

    for step in range(1, args.steps + 1):
        sim.step()
        m = sim.metrics()
        history.append(m)
        if writer:
            writer.writerow(m)
        if args.print_every > 0 and (step % args.print_every == 0 or step == args.steps):
            print(m)

    if writer:
        csvfile.close()

    # optional ethics ledger dump (JSONL)
    # argparse stores "--dump-ledger" as "dump_ledger"
    if getattr(args, "dump_ledger", None):
        import json
        with open(args.dump_ledger, "w", encoding="utf-8") as jf:
            for rec in sim.ethics.ledger:
                jf.write(json.dumps(rec) + "\n")

    # final print if not periodic
    if args.print_every == 0:
        print(history[-1])

    # optional plot (+ optional save)
    if args.plot or args.plot_path:
        try:
            import matplotlib.pyplot as plt
            ts = [row["t"] for row in history]
            rci = [row["RCI"] for row in history]
            de  = [row["Δℰ"] for row in history]
            mi  = [row["mean_inflation"] for row in history]
            pop = [row["universes_total"] for row in history]
            stb = [row["universes_stable"] for row in history]

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

            # Top: stability + inflation
            ax1.plot(ts, rci, label="RCI", color="#1f77b4", linewidth=2)
            ax1.plot(ts, mi,  label="mean_inflation", color="#2ca02c", linewidth=2, linestyle="--")
            ax1.set_ylim(0, max(1.05, max(rci) if rci else 1.0))
            ax1.set_ylabel("RCI / mean(I)")
            ax1.legend(loc="best")
            ax1.grid(alpha=0.25)

            # Bottom: exports + population
            ax2.plot(ts, de, label="Δℰ", color="#d62728", linewidth=2, alpha=0.9)
            ax2.plot(ts, pop, label="universes_total", color="#7f7f7f", linewidth=1.5)
            ax2.plot(ts, stb, label="universes_stable", color="#9467bd", linewidth=1.5)
            ax2.set_xlabel("t (steps)")
            ax2.set_ylabel("Δℰ / population")
            ax2.legend(loc="best")
            ax2.grid(alpha=0.25)

            plt.suptitle(f"Multiverse dynamics (policy={args.policy}, consent_prob={args.consent_prob}, strictness={args.ethics_strictness})")
            plt.tight_layout(rect=[0, 0.02, 1, 0.98])

            if args.plot_path:
                plt.savefig(args.plot_path, dpi=150)
            if args.plot:
                plt.show()
            plt.close(fig)
        except Exception as e:
            print(f"[plot] skipped: {e}")


def main(argv=None) -> int:
    args = parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
