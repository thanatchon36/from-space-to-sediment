import pytest

from from_space_to_sediment import cli


def test_verify_passes_options_through(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["verify", "--help"])
    assert e.value.code == 0
    assert "--candidates" in capsys.readouterr().out


def test_network_needs_rivers(tmp_path):
    with pytest.raises(SystemExit, match="make data"):
        cli.main(["network", "--rivers-json", str(tmp_path / "missing.json"), "--out", str(tmp_path)])
