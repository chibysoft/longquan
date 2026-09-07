"""Stage 3: induce lowest-complexity Program from frozen synth gold."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from longquan.induce import induce
from longquan.program import Program
from longquan.synth_gold import case_examples, load_gold


def test_gold_fixture_matches_specs():
    from longquan.synth_gold import _normalize, build_gold

    assert _normalize(build_gold()) == load_gold()


def test_induce_recovers_every_gold_program():
    gold = load_gold()
    assert len(gold["cases"]) >= 6
    for case in gold["cases"]:
        examples = case_examples(case)
        want = Program.from_json(case["program"])
        got = induce(examples, max_ops=2)
        assert got is not None, case["id"]
        assert got.to_json() == want.to_json(), (
            f"{case['id']}: got {got.to_json()} want {want.to_json()}"
        )
        assert got.complexity() == case["complexity"]
