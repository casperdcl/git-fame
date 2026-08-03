import logging
import subprocess
import sys
from functools import partial

from tqdm import tqdm as tqdm_std
from tqdm.utils import _screen_shape_wrapper

try:
    from threading import RLock
except ImportError:
    tqdm = tqdm_std
else:
    tqdm_std.set_lock(RLock())
    tqdm = partial(tqdm_std, lock_args=(False,))

__author__ = "Casper da Costa-Luis <casper.dcl@physics.org>"
__date__ = "2016-2025"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["TERM_WIDTH", "int_cast_or_len", "Max", "fext", "tqdm", "check_output", "print_unicode", "Str"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__ # weird foreign language

log = logging.getLogger(__name__)
if not (TERM_WIDTH := _screen_shape_wrapper()(sys.stdout)[0]):
    # non interactive pipe
    TERM_WIDTH = 256


class TqdmStream:
    @classmethod
    def write(cls, msg):
        tqdm_std.write(msg, end='')


def check_output(*a, **k):
    log.debug(' '.join(a[0][3:]))
    k.setdefault('stdout', subprocess.PIPE)
    return subprocess.Popen(*a, **k).communicate()[0].decode('utf-8', errors='replace') # nosec B603


def blank_col(rows, i, blanks):
    return all(r[i] in blanks for r in rows)


def fext(fn):
    """File extension"""
    res = fn.split('.')
    return res[-1] if len(res) > 1 else ''


def int_cast_or_len(i):
    """
    >>> int_cast_or_len(range(10))
    10
    >>> int_cast_or_len('90 foo')
    6
    >>> int_cast_or_len('90')
    90

    """
    try:
        return int(i)
    except (ValueError, TypeError):
        return len(i)


def Max(it, empty_default=0):
    """
    >>> Max(range(10), -1)
    9
    >>> Max(range(0), -1)
    -1

    """
    try:
        return max(it)
    except ValueError as e:
        if 'empty' in str(e):
            return empty_default
        raise      # pragma: no cover


def print_unicode(msg, end='\n', err='?'):
    """print `msg`, replacing unicode characters with `err` upon failure"""
    for c in msg:
        try:
            print(c, end='')
        except UnicodeEncodeError:
            print(err, end='')
    print('', end=end)


def Str(i):
    """return `'%g' % i` if possible, else `str(i)`"""
    try:
        return '%g' % i
    except TypeError:
        return str(i)


def merge_stats(left, right):
    """Add `right`'s values to `left` (modifies `left` in-place)"""
    for k, val in right.items():
        if isinstance(val, int):
            left[k] = left.get(k, 0) + val
        elif hasattr(val, 'extend'):
            left[k].extend(val)
        elif hasattr(val, 'update'):
            left[k].update(val)
        else:
            raise TypeError(val)
    return left


def imap_bounded(func, items, jobs):
    """
    Like `map(func, items)` but runs up to `jobs` calls concurrently,
    yielding results in input order.

    At most `min(2 * jobs, jobs + 4)` calls are outstanding at once, so
    the number of buffered results stays bounded regardless of how many
    items there are (an unbounded map would buffer every result). The
    bound is on the *number* of outstanding calls only: peak memory also
    grows with the size of the largest single result (e.g. `git blame`
    output for one large file can be megabytes).
    """
    if jobs < 2:
        for i in items:
            yield func(i)
        return

    from collections import deque
    from concurrent.futures import ThreadPoolExecutor
    from itertools import islice

    it = iter(items)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        pending = deque()
        try:
            for i in islice(it, min(2 * jobs, jobs + 4)):
                pending.append(pool.submit(func, i))
            while pending:
                res = pending.popleft().result()
                for i in islice(it, 1):
                    pending.append(pool.submit(func, i))
                yield res
        finally:
            # abandoned early, or `func` raised: nobody wants the queued
            # results, so don't let `pool.shutdown()` wait for them
            for future in pending:
                future.cancel()
