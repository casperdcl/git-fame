from __future__ import print_function

import logging
import subprocess
import sys
from functools import partial

from tqdm import tqdm as tqdm_std
from tqdm.utils import _screen_shape_wrapper

try:
  # python2
  _str = unicode
  _range = xrange
  from StringIO import StringIO
  string_types = (basestring,)
except NameError:
  # python3
  _str = str
  _range = range
  from io import StringIO
  string_types = (str,)
try:
  from threading import RLock
except ImportError:
  tqdm = tqdm_std
else:
  tqdm_std.set_lock(RLock())
  tqdm = partial(tqdm_std, lock_args=(False,))

__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016-2020"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["TERM_WIDTH", "int_cast_or_len", "Max", "fext", "_str", "tqdm",
           "tighten", "check_output", "print_unicode", "StringIO", "Str"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__  # weird foreign language

log = logging.getLogger(__name__)
TERM_WIDTH = _screen_shape_wrapper()(sys.stdout)[0]
if not TERM_WIDTH:
  # non interactive pipe
  TERM_WIDTH = 256


class TqdmStream(object):
  @classmethod
  def write(cls, msg):
    tqdm_std.write(msg, end='')


def check_output(*a, **k):
  log.debug(' '.join(a[0][3:]))
  k.setdefault('stdout', subprocess.PIPE)
  return subprocess.Popen(*a, **k).communicate()[0].decode(
      'utf-8', errors='replace')


def blank_col(rows, i, blanks):
  return all(r[i] in blanks for r in rows)


def tighten(t, max_width=256, blanks=' -=', seps='|+'):
  """Tighten (default: grid) table padding"""
  rows = t.strip().split('\n')
  i = 1
  curr_blank = bool()
  prev_blank = blank_col(rows, i - 1, blanks)
  len_r = len(rows[0])
  while (i < len_r):
    curr_blank = blank_col(rows, i, blanks)
    if prev_blank and curr_blank:
      rows = [r[:i - 1] + r[i:] for r in rows]
      len_r -= 1
      i -= 1
    prev_blank = curr_blank
    i += 1

  if len_r > max_width:
    have_first_line = False
    for i in _range(len_r):
      if blank_col(rows, i, seps):
        if have_first_line:
          if i > len_r - max_width:
            return '\n'.join(r[:i - len_r + max_width] + r[i:] for r in
                             rows[:3] + rows[3::2] + [rows[-1]])
          break
        else:
          have_first_line = True

  return '\n'.join(rows[:3] + rows[3::2] + [rows[-1]])


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
  except ValueError:
    return len(i)
  except TypeError:
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
    if 'empty sequence' in str(e):
      return empty_default
    raise  # pragma: no cover


def print_unicode(msg, end='\n', err='?'):
  """print `msg`, replacing unicode characters with `err` upon failure"""
  for c in msg:
    try:
      print(c, end='')
    except UnicodeEncodeError:
      print(err, end='')
  print('', end=end)


def Str(i):
  """return `'%g' % i` if possible, else `_str(i)`"""
  try:
    return '%g' % i
  except TypeError:
    return _str(i)


def merge_stats(left, right):
  """Add `right`'s values to `left` (modifies `left` in-place)"""
  for k, val in getattr(right, 'iteritems', right.items)():
    if isinstance(val, int):
      left[k] = left.get(k, 0) + val
    elif hasattr(val, 'extend'):
      left[k].extend(val)
    elif hasattr(val, 'update'):
      left[k].update(val)
    else:
      raise TypeError(val)
  return left
