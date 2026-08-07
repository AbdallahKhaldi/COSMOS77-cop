"""Nonce format discipline and the Step-0 declaration (hardware + commit mocked)."""

from unittest.mock import MagicMock, patch

from cosmos77_cop.crypto.nonce import is_valid_nonce, new_nonce
from cosmos77_cop.crypto.step0 import build_step0, current_commit, hardware_spec, is_dirty


def test_new_nonce_is_32_lowercase_hex_and_unique():
    seen = {new_nonce() for _ in range(64)}
    assert len(seen) == 64
    assert all(is_valid_nonce(n) for n in seen)


def test_nonce_validation_rejects_wire_junk():
    assert not is_valid_nonce("ABCDEF00112233445566778899AABBCC")
    assert not is_valid_nonce("abc")
    assert not is_valid_nonce(12345)
    assert not is_valid_nonce("g" * 32)


@patch("cosmos77_cop.crypto.step0.psutil")
@patch("cosmos77_cop.crypto.step0.platform")
def test_hardware_spec_has_the_bonus_gating_fields(mock_platform, mock_psutil):
    mock_platform.system.return_value = "Darwin"
    mock_platform.machine.return_value = "arm64"
    mock_psutil.cpu_count.return_value = 8
    mock_psutil.cpu_freq.return_value = MagicMock(max=3200.0, current=2400.0)
    mock_psutil.virtual_memory.return_value = MagicMock(total=16 * 2**30)
    spec = hardware_spec()
    assert spec["os"] == "Darwin"
    assert spec["cpu_cores"] == 8
    assert spec["cpu_freq_ghz"] == 3.2
    assert spec["ram_gb"] == 16.0
    expected = {"os", "cpu_type", "cpu_cores", "cpu_freq_ghz", "ram_gb", "gpu_type", "vram_gb"}
    assert set(spec) == expected


@patch("cosmos77_cop.crypto.step0.subprocess.run")
def test_current_commit_and_dirty_flag(mock_run):
    mock_run.return_value = MagicMock(stdout="a" * 40 + "\n")
    assert current_commit() == "a" * 40
    mock_run.return_value = MagicMock(stdout=" M src/x.py\n")
    assert is_dirty()
    mock_run.return_value = MagicMock(stdout="")
    assert not is_dirty()


def test_step0_record_shape():
    record = build_step0(
        sub_game_number=3,
        group_name="cosmos77",
        model="gemini-2.5-flash",
        code_version="b" * 40,
        num_games_declared=2,
        spec={"os": "Darwin"},
    )
    assert record["step"] == 0
    assert record["type"] == "system_spec"
    assert record["num_games_declared"] == 2
    assert record["code_version"] == "b" * 40
