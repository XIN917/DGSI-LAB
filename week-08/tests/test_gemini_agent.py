"""Tests for the Gemini agent integration in turn_engine."""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Ensure the repo root is on the path so turn_engine imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from turn_engine import _run_agent_gemini, _GEMINI_AVAILABLE


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_text_response(text):
    """Build a minimal mock Gemini response with only a text part (no tool calls)."""
    part = MagicMock()
    part.function_call = None
    part.text = text
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


def _make_tool_response(cmd):
    """Build a mock Gemini response that requests one bash tool call."""
    fc = MagicMock()
    fc.name = "bash"
    fc.args = {"command": cmd}
    part = MagicMock()
    part.function_call = fc
    part.text = None
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_gemini_available():
    """google-genai SDK must be importable (installed as a dependency)."""
    assert _GEMINI_AVAILABLE, (
        "google-genai is not installed. Run: pip install google-genai"
    )


def test_run_agent_gemini_raises_without_api_key(tmp_path, monkeypatch):
    """_run_agent_gemini raises RuntimeError when GEMINI_API_KEY is absent."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        _run_agent_gemini("provider", "do something", str(tmp_path), 4, "gemini-2.5-flash")


def test_run_agent_gemini_text_only_response(tmp_path, monkeypatch):
    """Agent returns model text when the model produces no tool calls."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_text_response("All done.")

    with patch("turn_engine.google_genai.Client", return_value=mock_client):
        result = _run_agent_gemini("provider", "assess stock", str(tmp_path), 4, "gemini-2.5-flash")

    assert "All done." in result
    mock_client.models.generate_content.assert_called_once()


def test_run_agent_gemini_executes_bash_tool(tmp_path, monkeypatch):
    """Agent executes a bash command and feeds the output back to the model."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    # Turn 1: model asks for a bash command; Turn 2: model returns text
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        _make_tool_response("echo hello"),
        _make_text_response("Command executed."),
    ]

    with patch("turn_engine.google_genai.Client", return_value=mock_client):
        result = _run_agent_gemini("retailer", "check prices", str(tmp_path), 4, "gemini-2.5-flash")

    assert "echo hello" in result
    assert "hello" in result          # stdout captured
    assert "Command executed." in result
    assert mock_client.models.generate_content.call_count == 2


def test_run_agent_gemini_respects_max_turns(tmp_path, monkeypatch):
    """Agent loop stops after max_turns even if the model keeps calling tools."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_client = MagicMock()
    # Always return a tool call — loop should stop at max_turns
    mock_client.models.generate_content.return_value = _make_tool_response("echo loop")

    with patch("turn_engine.google_genai.Client", return_value=mock_client):
        _run_agent_gemini("manufacturer", "release orders", str(tmp_path), 3, "gemini-2.5-flash")

    assert mock_client.models.generate_content.call_count == 3


def test_run_agent_gemini_retries_on_429(tmp_path, monkeypatch):
    """Agent retries up to 3 times when the API returns a 429 rate-limit error."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_client = MagicMock()
    rate_limit_error = Exception("429 RESOURCE_EXHAUSTED quota exceeded")
    mock_client.models.generate_content.side_effect = [
        rate_limit_error,
        rate_limit_error,
        _make_text_response("Recovered after retries."),
    ]

    with patch("turn_engine.google_genai.Client", return_value=mock_client):
        with patch("turn_engine.time.sleep") as mock_sleep:
            result = _run_agent_gemini("provider", "restock", str(tmp_path), 4, "gemini-2.5-flash")

    assert "Recovered after retries." in result
    assert mock_client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2          # slept between each retry
    assert mock_sleep.call_args_list[0] == call(15)
    assert mock_sleep.call_args_list[1] == call(30)


def test_run_agent_gemini_raises_after_max_retries(tmp_path, monkeypatch):
    """Agent re-raises the exception after exhausting all 4 retry attempts."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

    with patch("turn_engine.google_genai.Client", return_value=mock_client):
        with patch("turn_engine.time.sleep"):
            with pytest.raises(Exception, match="429"):
                _run_agent_gemini("provider", "restock", str(tmp_path), 4, "gemini-2.5-flash")

    assert mock_client.models.generate_content.call_count == 4


def test_run_agent_gemini_non_429_error_not_retried(tmp_path, monkeypatch):
    """Non-rate-limit errors are raised immediately without retrying."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("500 Internal Server Error")

    with patch("turn_engine.google_genai.Client", return_value=mock_client):
        with patch("turn_engine.time.sleep") as mock_sleep:
            with pytest.raises(Exception, match="500"):
                _run_agent_gemini("retailer", "check stock", str(tmp_path), 4, "gemini-2.5-flash")

    mock_client.models.generate_content.assert_called_once()
    mock_sleep.assert_not_called()


def test_run_agent_gemini_model_name_detection(monkeypatch):
    """run_agent routes gemini-prefixed model names to the Gemini path."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    from turn_engine import run_agent

    gemini_called = []

    def fake_gemini(role, prompt, cwd, max_turns, model):
        gemini_called.append(model)
        return "gemini output"

    with patch("turn_engine._run_agent_gemini", side_effect=fake_gemini):
        with patch("turn_engine.prefetch_state", return_value="state"):
            with patch("turn_engine.role_contract", return_value="rules"):
                with patch("turn_engine.console"):
                    run_agent(
                        "provider", None, '{"day": 1}', "/tmp",
                        spinner=False, model="gemini-2.5-flash"
                    )

    assert gemini_called == ["gemini-2.5-flash"]


def test_run_agent_claude_does_not_use_gemini_path(monkeypatch, tmp_path):
    """run_agent does NOT call _run_agent_gemini for Claude model names."""
    from turn_engine import run_agent

    gemini_called = []

    def fake_gemini(*a, **kw):
        gemini_called.append(True)
        return ""

    with patch("turn_engine._run_agent_gemini", side_effect=fake_gemini):
        with patch("turn_engine.prefetch_state", return_value="state"):
            with patch("turn_engine.role_contract", return_value="rules"):
                with patch("turn_engine.console"):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_proc = MagicMock()
                        mock_proc.stdout.readline.side_effect = ["output\n", ""]
                        mock_proc.poll.return_value = 0
                        mock_proc.wait.return_value = 0
                        mock_popen.return_value = mock_proc
                        run_agent(
                            "provider", None, '{"day": 1}', str(tmp_path),
                            spinner=False, model="claude-haiku-4-5-20251001"
                        )

    assert gemini_called == [], "Gemini path should not be called for Claude models"
