"""Agreement between two judges scoring the same transcripts.

Compares the original logs against re-judged copies (scripts/rejudge.sh) on
identical (target, sample, epoch, dimension) cells. Reports per-dimension
Spearman correlation and mean offset, and whether the *target gap* changes
with the judge -- the quantity Part A's conclusion actually depends on. A
judge that favors its own model family shows up as a gap that flips or
shrinks under the other judge.

Usage: uv run python -m analysis.judge_agreement [--a logs] [--b logs_rejudged]
"""

import argparse

import pandas as pd
from scipy.stats import spearmanr

from analysis.load import load_logs

KEY = ["target", "sample_id", "epoch", "dimension"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="logs")
    ap.add_argument("--b", default="logs_rejudged")
    ap.add_argument("--task", default=None)
    args = ap.parse_args()

    frames = []
    for d in (args.a, args.b):
        s, _ = load_logs(d, task=args.task)
        frames.append(s[s["valid"]])
    a, b = frames
    if a.empty or b.empty:
        raise SystemExit("No valid (parsed, error-free) scores in one of the log sets")
    ja, jb = a["judge"].iloc[0], b["judge"].iloc[0]
    m = a.merge(b, on=KEY, suffixes=("_a", "_b"))[KEY + ["score_a", "score_b"]]
    if m.empty:
        raise SystemExit("No overlapping transcripts between the two log sets")
    print(f"Judge A = {ja}, judge B = {jb}; {m[['target', 'sample_id', 'epoch']].drop_duplicates().shape[0]} shared transcripts\n")

    rows = []
    for dim, g in m.groupby("dimension"):
        varies = g["score_a"].nunique() > 1 and g["score_b"].nunique() > 1
        gap = g.groupby("target")[["score_a", "score_b"]].mean()
        row = {
            "dimension": dim,
            "n": len(g),
            "spearman": spearmanr(g["score_a"], g["score_b"]).statistic if varies else float("nan"),
            "mean_offset_b_minus_a": (g["score_b"] - g["score_a"]).mean(),
            "exact_agree": (g["score_a"] == g["score_b"]).mean(),
        }
        if len(gap) == 2:
            t1, t2 = gap.index
            row[f"gap_{t1}_minus_{t2}_judgeA"] = gap.loc[t1, "score_a"] - gap.loc[t2, "score_a"]
            row[f"gap_{t1}_minus_{t2}_judgeB"] = gap.loc[t1, "score_b"] - gap.loc[t2, "score_b"]
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("spearman")
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    out.to_csv("figures/judge_agreement.csv", index=False)


if __name__ == "__main__":
    main()
