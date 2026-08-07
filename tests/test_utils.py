from gitfame import _utils


def test_fext():
    """Test detection of file extensions"""
    assert (_utils.fext('foo/bar.baz') == 'baz')
    assert (_utils.fext('foo/.baz') == 'baz')
    assert (_utils.fext('foo/bar') == '')


def test_Max():
    """Test max with defaults"""
    assert (_utils.Max(range(10), -1) == 9)
    assert (_utils.Max(range(0), -1) == -1)


def test_integer_stats():
    """Test integer representations"""
    assert (_utils.int_cast_or_len(range(10)) == 10)
    assert (_utils.int_cast_or_len('90 foo') == 6)
    assert (_utils.int_cast_or_len('90') == 90)


def test_print():
    """Test printing of unicode"""
    _utils.print_unicode("\x81")
