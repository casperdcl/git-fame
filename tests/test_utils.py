import pytest

from gitfame import _utils


def test_tighten():
    """Test (grid) table compression"""

    orig_tab = '''
+------------------------+-----+------+------+----------------------+
|   Author               | loc | coms | fils |     distribution     |
+========================+=====+======+======+======================+
|   Casper da Costa-Luis | 719 |   35 |   11 |    93.5/ 100/84.6    |
+------------------------+-----+------+------+----------------------+
|   Not Committed Yet    |  50 |    0 |    2 |     6.5/ 0.0/15.4    |
+------------------------+-----+------+------+----------------------+
'''

    # compress whitespace
    assert (_utils.tighten(orig_tab, max_width=80) == '''\
+----------------------+-----+------+------+----------------+
| Author               | loc | coms | fils |  distribution  |
+======================+=====+======+======+================+
| Casper da Costa-Luis | 719 |   35 |   11 | 93.5/ 100/84.6 |
| Not Committed Yet    |  50 |    0 |    2 |  6.5/ 0.0/15.4 |
+----------------------+-----+------+------+----------------+''')

    # compress first column
    assert (_utils.tighten(orig_tab, max_width=47) == '''\
+--------+-----+------+------+----------------+
| Author | loc | coms | fils |  distribution  |
+========+=====+======+======+================+
| Casper | 719 |   35 |   11 | 93.5/ 100/84.6 |
| Not Com|  50 |    0 |    2 |  6.5/ 0.0/15.4 |
+--------+-----+------+------+----------------+''')

    # too small width - no first column compression
    assert (_utils.tighten(orig_tab, max_width=35) == _utils.tighten(orig_tab))


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


def test_imap_bounded():
    """Test bounded concurrent map: order preserved, concurrency capped"""
    from threading import Lock
    from time import sleep

    from gitfame._utils import imap_bounded

    live, peak, lock = [0], [0], Lock()

    def work(i):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        sleep(0.005)
        with lock:
            live[0] -= 1
        return i * 2

    assert list(imap_bounded(work, range(20), 4)) == [i * 2 for i in range(20)]
    assert peak[0] > 1, "should have run concurrently"
    assert peak[0] <= 4, "should not exceed the job cap"

    # serial fallback: no executor, same results
    assert list(imap_bounded(lambda i: i * 2, range(5), 1)) == [0, 2, 4, 6, 8]
    assert list(imap_bounded(lambda i: i * 2, [], 4)) == []


def test_imap_bounded_window_edges():
    """Test input lengths either side of the `2 * jobs` window"""
    from gitfame._utils import imap_bounded

    for n in range(2*4 + 2): # fewer than, exactly, and more than the window
        assert list(imap_bounded(lambda i: i * 2, range(n), 4)) == [i * 2 for i in range(n)]


def test_imap_bounded_abandoned():
    """Test abandoning the generator early doesn't consume the whole input"""
    from threading import Lock

    from gitfame._utils import imap_bounded

    started, lock = [0], Lock()

    def work(i):
        with lock:
            started[0] += 1
        return i

    gen = imap_bounded(work, range(200), 2)
    assert next(gen) == 0
    gen.close()
    # window is `2 * jobs`, plus the one submitted after the first result
    assert started[0] <= 5, "should not have consumed the whole input"


def test_imap_bounded_raises():
    """Test exceptions from `func` propagate"""
    from gitfame._utils import imap_bounded

    def work(i):
        if i == 3:
            raise ValueError(i)
        return i

    with pytest.raises(ValueError):
        list(imap_bounded(work, range(200), 4))
    with pytest.raises(ValueError):
        list(imap_bounded(work, range(200), 1))
