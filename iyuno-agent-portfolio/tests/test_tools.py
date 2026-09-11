import pytest

from agent.tools import calculator, doc_search, policy_lookup, call_tool, CalculatorError, _safe_eval
import ast


def test_calculator_basic_arithmetic():
    assert calculator("2+2")["result"] == 4
    assert calculator("(10-4)/3")["result"] == 2.0


def test_calculator_rejects_unsafe_expression():
    result = calculator("__import__('os').system('echo hi')")
    assert result["ok"] is False


def test_calculator_rejects_names():
    with pytest.raises(CalculatorError):
        _safe_eval(ast.parse("x + 1", mode="eval").body)


def test_doc_search_returns_results():
    result = doc_search("tool calling agent", k=3)
    assert result["ok"] is True
    assert len(result["results"]) == 3


def test_policy_lookup_known_id():
    result = policy_lookup("owasp-top10-overview")
    assert result["ok"] is True
    assert "OWASP" in result["title"]


def test_policy_lookup_unknown_id():
    result = policy_lookup("not-a-real-doc")
    assert result["ok"] is False
    assert "known_doc_ids" in result


def test_call_tool_dispatches_and_logs():
    from agent import tools

    before = len(tools.CALL_LOG)
    call_tool("calculator", expression="1+1")
    assert len(tools.CALL_LOG) == before + 1


def test_call_tool_unknown_tool_raises():
    with pytest.raises(KeyError):
        call_tool("not_a_tool")
