import numpy as np
import pandas as pd

from analysis.part_a import compare, paired_table


def _scores(n=40, shift=2.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        base = rng.integers(1, 6)
        for target, bump in [("a", shift), ("b", 0.0)]:
            rows += [
                {"target": target, "sample_id": str(i), "primary_tag": "t", "dimension": "concerning",
                 "score": base + bump + rng.normal(0, 0.5)},
                {"target": target, "sample_id": str(i), "primary_tag": "t", "dimension": "admirable",
                 "score": float(base)},
            ]
    return pd.DataFrame(rows)


def test_detects_real_difference_and_ignores_null():
    res = compare(paired_table(_scores()), "a", "b").set_index("dimension")
    assert res.loc["concerning", "p_bh"] < 0.001
    assert res.loc["concerning", "ci_low"] > 1.5
    assert res.loc["admirable", "p"] == 1.0


def test_pairs_by_seed_and_averages_epochs():
    df = _scores(n=5)
    df2 = df.assign(score=df["score"] + 1)  # second epoch, +1 for both targets
    wide = paired_table(pd.concat([df, df2]))
    assert len(wide) == 10  # 5 seeds x 2 dims
