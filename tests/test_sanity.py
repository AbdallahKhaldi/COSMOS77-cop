"""Phase 0 seed tests: the package imports and its entry points answer.

pytest exits 5 on zero collected tests, so this file is itself part of the gate.
"""

import cosmos77_cop
from cosmos77_cop.cli import main
from cosmos77_cop.sdk import SDK


def test_package_imports_with_version():
    assert cosmos77_cop.__version__


def test_cli_reports_version(capsys):
    assert main(["--version"]) == 0
    assert f"cosmos-cop {cosmos77_cop.__version__}" in capsys.readouterr().out


def test_cli_default_lists_live_subcommands(capsys):
    assert main([]) == 0
    assert "selfplay" in capsys.readouterr().out


def test_cli_unknown_subcommand_fails_loudly(capsys):
    assert main(["nonsense"]) == 2
    assert "unknown subcommand" in capsys.readouterr().out


def test_sdk_facade_is_documented():
    assert SDK.__doc__
