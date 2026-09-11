import json
import pathlib

EVAL_SET_PATH = pathlib.Path(__file__).resolve().parent.parent / "evaluation" / "eval_set.json"


def test_eval_set_has_at_least_30_questions():
    with EVAL_SET_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 30


def test_eval_set_covers_multiple_question_types():
    with EVAL_SET_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    types = {item["type"] for item in data}
    assert {"factual", "arithmetic", "out_of_scope"}.issubset(types)
