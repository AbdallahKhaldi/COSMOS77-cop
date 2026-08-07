"""Gemini hinter (fully mocked) and the provider chain — the Phase-6 gate sequence."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cosmos77_cop.hints.gemini import GeminiHinter, HintMeter, load_env_key
from cosmos77_cop.hints.lint import is_coordinate_free
from cosmos77_cop.hints.provider import HintProvider
from cosmos77_cop.hints.templates import LIES_COP, TRUTHS


def hinter_with(mock_client, key="k"):
    meter = HintMeter()
    h = GeminiHinter(key, "gemini-2.5-flash", meter)
    h._client = mock_client
    return h, meter


def response(text, tokens=42):
    return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(total_token_count=tokens))


def test_gemini_success_meters_tokens_per_sub_game():
    client = MagicMock()
    client.models.generate_content.return_value = response("Nothing moves without me hearing it")
    h, meter = hinter_with(client)
    assert h.hint(role="police", arena="New York", intent="lie", sub_game=2) is not None
    h.hint(role="police", arena="New York", intent="lie", sub_game=2)
    h.hint(role="police", arena="New York", intent="truth", sub_game=3)
    assert meter.per_sub_game == {2: 84, 3: 42}
    assert meter.total_series == 126


def test_gemini_every_failure_path_returns_none():
    h, _ = hinter_with(None, key=None)
    assert h.hint(role="police", arena="X", intent="lie", sub_game=1) is None
    boom = MagicMock()
    boom.models.generate_content.side_effect = TimeoutError("slow")
    h2, _ = hinter_with(boom)
    assert h2.hint(role="police", arena="X", intent="lie", sub_game=1) is None
    empty = MagicMock()
    empty.models.generate_content.return_value = SimpleNamespace(text=None, usage_metadata=None)
    h3, _ = hinter_with(empty)
    assert h3.hint(role="police", arena="X", intent="lie", sub_game=1) is None


def test_load_env_key_prefers_process_env(tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text('GEMINI_API_KEY="from-file"\n')
    with patch.dict("os.environ", {"GEMINI_API_KEY": "from-env"}):
        assert load_env_key(envfile) == "from-env"
    with patch.dict("os.environ", {}, clear=True):
        assert load_env_key(envfile) == "from-file"
        assert load_env_key(tmp_path / "absent") is None


def test_seeded_sequence_meets_the_phase_gate():
    provider = HintProvider(role="police", arena="New York", max_words=15, seed=11)
    seen_intents = set()
    for step in range(1, 21):
        result = provider.hint_for_step(step, sub_game=1)
        assert len(result.text.split()) <= 15
        assert is_coordinate_free(result.text)
        assert result.intent in {"truth", "lie"}
        pools = TRUTHS if result.intent == "truth" else LIES_COP
        assert any(result.text == line.format(arena="New York") for line in pools)
        seen_intents.add(result.intent)
    assert seen_intents == {"truth", "lie"}


def test_gemini_cadence_and_fallback_on_none():
    client = MagicMock()
    client.models.generate_content.return_value = response("The west side is sealed tight tonight")
    meter = HintMeter()
    hinter = GeminiHinter("k", "gemini-2.5-flash", meter)
    hinter._client = client
    provider = HintProvider(
        role="police", arena="New York", max_words=15, gemini=hinter, every_n_steps=3, seed=5
    )
    for step in range(1, 7):
        provider.hint_for_step(step, sub_game=1)
    assert client.models.generate_content.call_count == 2
    dead = MagicMock()
    dead.models.generate_content.side_effect = RuntimeError("quota")
    hinter2 = GeminiHinter("k", "gemini-2.5-flash", HintMeter())
    hinter2._client = dead
    provider2 = HintProvider(
        role="police", arena="New York", max_words=15, gemini=hinter2, every_n_steps=1, seed=5
    )
    result = provider2.hint_for_step(1, sub_game=1)
    assert result.text and is_coordinate_free(result.text)


def test_generated_digits_get_linted_to_safe_line():
    client = MagicMock()
    client.models.generate_content.return_value = response("Meet at 4,4 sharp")
    hinter = GeminiHinter("k", "m", HintMeter())
    hinter._client = client
    provider = HintProvider(
        role="thief", arena="New York", max_words=15, gemini=hinter, every_n_steps=1, seed=2
    )
    result = provider.hint_for_step(1, sub_game=1)
    assert is_coordinate_free(result.text)
    assert "secrets" in result.text
