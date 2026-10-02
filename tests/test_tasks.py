from vals_petri.tasks import default_seeds, load_instructions, petri_subset, stratified_seed_ids


def test_default_seed_ids_are_unique_and_stable():
    ids = [s.id for s in default_seeds()]
    assert len(ids) == len(set(ids)) == 181
    assert ids == [s.id for s in default_seeds()]


def test_stratified_is_deterministic_and_spreads_tags():
    a, b = stratified_seed_ids(30, seed=1), stratified_seed_ids(30, seed=1)
    assert a == b and len(a) == len(set(a)) == 30
    primary = {s.id: (s.metadata["tags"] or ["untagged"])[0] for s in default_seeds() if s.id in a}
    assert len(set(primary.values())) >= 20  # 31 primary tags exist; 30 seeds should hit most


def test_petri_subset_filters():
    assert len(petri_subset(n=12).dataset) == 12
    assert len(petri_subset(ids="1,7").dataset) == 2
    tagged = petri_subset(tags="sycophancy").dataset
    assert all("sycophancy" in s.metadata["tags"] for s in tagged)


def test_load_instructions(tmp_path):
    f = tmp_path / "i.json"
    f.write_text('["plain seed", {"id": "x", "input": "obj seed", "tags": ["t"]}]')
    samples = load_instructions(f)
    assert [s.id for s in samples] == ["1", "x"]
    assert samples[1].metadata["tags"] == ["t"]


def test_defaults_match_petri_and_prefill_ablation_works():
    assert len(petri_subset().dataset) == 181
    ablated = petri_subset(exclude_tags="prefill").dataset
    assert len(ablated) == 159
    assert not any("prefill" in s.metadata["tags"] for s in ablated)
    assert not any("prefill" in s.metadata["tags"] for s in petri_subset(n=40, exclude_tags="prefill").dataset)


def test_auditor_prefill_tool_can_be_disabled():
    from inspect_ai.tool import ToolDef
    from petri.tools import default_auditor_tools

    params = {ToolDef(t).name: ToolDef(t).parameters.properties for t in default_auditor_tools(prefill=False)}
    assert "prefill" not in params["send_message"]
    assert petri_subset(n=2, prefill=False).solver is not None


def test_exclude_ids_holds_out_seeds_from_sample():
    held = "18,30,99,103,idx162,idx163"
    ids = {s.id for s in petri_subset(n=8, exclude_ids=held).dataset}
    assert len(ids) == 8 and not ids & set(held.split(","))
