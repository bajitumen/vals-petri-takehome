import numpy as np
import pandas as pd

from analysis.part_a import compare, n_paired_seeds, paired_table, t_interval


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
                 "score": float(base) + bump},
            ]
    return pd.DataFrame(rows)


def test_detects_real_difference():
    res = compare(paired_table(_scores()), "a", "b").set_index("dimension")
    assert res.loc["concerning", "p_bh"] < 0.001
    assert res.loc["concerning", "ci_low"] > 1.5


def test_polarity_flips_higher_is_better():
    res = compare(paired_table(_scores()), "a", "b").set_index("dimension")
    # a scores higher on both; that is worse on `concerning`, better on `admirable`
    assert res.loc["concerning", "harm_diff"] > 0
    assert res.loc["admirable", "harm_diff"] < 0
    assert res.loc["admirable", "seeds_b_worse"] == 40


def test_null_dimension_and_ties():
    df = _scores(n=6, shift=0.0)
    df.loc[df.dimension == "concerning", "score"] = 1.0
    res = compare(paired_table(df), "a", "b").set_index("dimension")
    assert res.loc["concerning", "p"] == 1.0
    assert res.loc["concerning", "seeds_tied"] == 6


def test_t_interval_is_not_degenerate_bootstrap():
    lo, hi = t_interval(np.array([2.0, 2.0, 2.0, 1.0]))
    assert lo < 1.75 < hi
    assert np.isnan(t_interval(np.array([1.0]))[0])


def test_pairs_by_seed_and_averages_epochs():
    df = _scores(n=5)
    wide = paired_table(pd.concat([df, df.assign(score=df["score"] + 1)]))
    assert len(wide) == 10 and n_paired_seeds(wide) == 5


def test_compare_empty_pairing_returns_empty():
    assert compare(paired_table(_scores(n=3)).iloc[0:0], "a", "b").empty
