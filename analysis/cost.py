"""Cost so far, and a projection for a larger run from per-seed averages.

Usage: uv run python -m analysis.cost [--log-dir logs] [--seeds 181] [--epochs 1] [--budget 20]
"""

import argparse

from analysis.load import load_logs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", default="logs")
    ap.add_argument("--seeds", type=int, default=181, help="seeds per target in the planned run")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--budget", type=float, default=20.0)
    args = ap.parse_args()

    _, usage = load_logs(args.log_dir)
    # Re-scored logs (logs_rejudged/) copy the original audit's events, so only their
    # judge usage is new spend. Keep them out of --log-dir to avoid double counting.
    if usage.empty:
        raise SystemExit(f"No usage found in {args.log_dir}")
    if usage["cost"].isna().any():
        missing = sorted(usage.loc[usage["cost"].isna(), "model"].unique())
        print(f"WARNING: no price for {missing}; add them to model_costs.yaml. Their cost counts as $0.\n")

    spent = usage["cost"].sum()
    print(f"Spent so far: ${spent:.2f} of ${args.budget:.2f}\n")
    print("By task x target x role:")
    print(usage.groupby(["task", "target", "role"])["cost"].sum().round(3).to_string(), "\n")

    per_seed = usage.groupby(["target", "sample_id", "epoch"])["cost"].sum().groupby("target").agg(["mean", "max", "count"])
    print("Per-seed cost by target (all roles):")
    print(per_seed.round(4).to_string(), "\n")

    projected = per_seed["mean"].sum() * args.seeds * args.epochs
    print(f"Projected: {args.seeds} seeds x {args.epochs} epoch(s) x {len(per_seed)} targets = ${projected:.2f}")
    remaining = args.budget - spent
    affordable = int(remaining / per_seed["mean"].sum()) if per_seed["mean"].sum() else 0
    print(f"Remaining ${remaining:.2f} affords ~{affordable} more seed-runs per target (at the mean).")


if __name__ == "__main__":
    main()
