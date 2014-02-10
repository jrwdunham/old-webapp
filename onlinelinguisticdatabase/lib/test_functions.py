from functions import *

def test_pretty_date_no_arg():
    out = pretty_date()
    assert type(out) == type('')


def test_pretty_date_ISO_8601_date():
    out = pretty_date('2012-08-15')
    assert type(out) == type('')
