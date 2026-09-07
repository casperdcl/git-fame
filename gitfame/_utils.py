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

try:
    from concurrent.futures import ThreadPoolExecutor  # noqa: F401, yapf: disable

    from tqdm.contrib.concurrent import thread_map
    mapper = partial(thread_map, tqdm_class=tqdm_std)
except ImportError:
    mapper = map

__author__ = "Casper da Costa-Luis <casper.dcl@physics.org>"
__date__ = "2016-2025"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["TERM_WIDTH", "int_float_len", "fext", "tqdm", "check_output", "print_unicode", "Str", "get_mapper"]
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


def get_mapper(max_workers=None, **tqdm_kwargs):
    """`map` with progress; concurrent iff `max_workers != 1`"""
    if max_workers != 1 and mapper is not map:
        return partial(mapper, max_workers=max_workers, **tqdm_kwargs)
    return lambda func, iterable: map(func, tqdm(iterable, **tqdm_kwargs))


def fext(fn):
    """File extension"""
    res = fn.rsplit('.', 1)
    return res[-1] if len(res) > 1 else ''


def int_float_len(i):
    """
    >>> int_float_len(range(10))
    10
    >>> int_float_len('90 foo')
    6
    >>> int_float_len('90')
    90
    >>> int_float_len(1.5)
    1.5
    """
    try:
        return i if isinstance(i, float) else int(i)
    except (ValueError, TypeError):
        return len(i)


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
        if isinstance(val, (int, float)):
            left[k] = left.get(k, 0) + val
        elif hasattr(val, 'extend'):
            left[k].extend(val)
        elif hasattr(val, 'update'):
            left[k].update(val)
        else:
            raise TypeError(val)
    return left
