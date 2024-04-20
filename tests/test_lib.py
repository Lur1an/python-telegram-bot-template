import rustlib

def test_rustlib():
    assert rustlib.sum_as_string(20, 30) == "50"
