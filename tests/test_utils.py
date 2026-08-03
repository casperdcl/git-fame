import pytest

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


def test_imap_bounded():
    """Test bounded concurrent map: order preserved, concurrency capped"""
    from threading import Lock
    from time import sleep

    live, peak, lock = [0], [0], Lock()

    def work(i):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        # descending durations: item 0 is slowest, so an implementation
        # yielding as-completed (instead of in input order) fails below
        sleep(0.002 * (20-i))
        with lock:
            live[0] -= 1
        return i * 2

    assert list(_utils.imap_bounded(work, range(20), 4)) == [i * 2 for i in range(20)]
    assert peak[0] > 1, "should have run concurrently"
    assert peak[0] <= 4, "should not exceed the job cap"

    # serial fallback: no executor, same results
    assert list(_utils.imap_bounded(lambda i: i * 2, range(5), 1)) == [0, 2, 4, 6, 8]
    assert list(_utils.imap_bounded(lambda i: i * 2, [], 4)) == []


@pytest.mark.parametrize('jobs', [2, 4, 8])
def test_imap_bounded_window_edges(jobs):
    """Test input lengths around the `min(2 * jobs, jobs + 4)` window"""
    window = min(2 * jobs, jobs + 4)
    # fewer than, exactly, and more than the window
    for n in [window - 1, window, window + 1]:
        assert list(_utils.imap_bounded(lambda i: i * 2, range(n), jobs)) == [i * 2 for i in range(n)]

    # The clamp matters for jobs > 4; verify the initial lookahead size.
    consumed = [0]

    def counted_items():
        for i in range(2*jobs + 2):
            consumed[0] += 1
            yield i

    gen = _utils.imap_bounded(lambda i: i * 2, counted_items(), jobs)
    assert next(gen) == 0
    # one extra item is pulled after the first result completes but before yielding
    assert consumed[0] == window + 1
    gen.close()


def test_imap_bounded_abandoned():
    """Test abandoning the generator early doesn't consume the whole input"""
    from threading import Event, Lock

    started, lock, release = [0], Lock(), Event()

    def work(i):
        with lock:
            started[0] += 1
        # only item 0 finishes promptly; the rest block briefly so that
        # queued items can only start if the finally:/cancel is missing
        if i:
            release.wait(0.2)
        return i

    gen = _utils.imap_bounded(work, range(200), 2)
    assert next(gen) == 0
    gen.close()
    release.set()
    # two workers, so at most tasks 0-2 are in flight when the generator is
    # closed; without the cancel, the rest of the submitted window (5 items
    # total) runs too
    assert started[0] <= 3, "should not have run the whole submitted window"


def test_imap_bounded_raises():
    """Test exceptions from `func` propagate"""
    def work(i):
        if i == 3:
            raise ValueError(i)
        return i

    with pytest.raises(ValueError):
        list(_utils.imap_bounded(work, range(200), 4))
    with pytest.raises(ValueError):
        list(_utils.imap_bounded(work, range(200), 1))
