import pytest


@pytest.fixture(autouse=True)
def fake_cacheing(mocker):
    mocker.patch('ukechords.theory.save_scanned_chords')
    fake_lsc = mocker.patch('ukechords.theory.load_scanned_chords')
    fake_lsc.return_value = False
