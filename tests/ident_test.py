import pytest

from ukechords.ident import error


def test_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        error(5, "error!")
    assert excinfo.value.code == 5
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "error!\n"
