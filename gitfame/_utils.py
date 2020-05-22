from __future__ import print_function
from functools import partial
import sys
import subprocess
import logging
log = logging.getLogger(__name__)  # NOQA

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
  from tqdm import tqdm
  try:
    from threading import RLock
  except ImportError:
    pass
  else:
    tqdm.set_lock(RLock())
    tqdm = partial(tqdm, lock_args=(False,))
except ImportError:
  class tqdm(object):
    def __init__(self, iterable=None, **kwargs):
      log.info('install `tqdm` (https://github.com/tqdm/tqdm)'
               ' for a realtime progressbar')
      self.iterable = iterable
      self.n = 0

    def __iter__(self):
      for i in self.iterable:
        self.n += 1
        sys.stderr.write("%d/%d\r" % (self.n, len(self.iterable)))
        sys.stderr.flush()
        yield i

    @classmethod
    def write(cls, msg, end='\n'):
      sys.stderr.write(msg + end)

__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016-2020"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["TERM_WIDTH", "int_cast_or_len", "Max", "fext", "_str", "tqdm",
           "tighten", "check_output", "print_unicode", "StringIO", "Str"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__  # weird foreign language


class TqdmStream(object):
  @classmethod
  def write(cls, msg):
    tqdm.write(msg, end='')

  # is this required?
  # @classmethod
  # def flush(_):
  #   pass


def check_output(*a, **k):
  log.debug(' '.join(a[0][3:]))
  k.setdefault('stdout', subprocess.PIPE)
  return subprocess.Popen(*a, **k).communicate()[0].decode('utf-8')


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


def _environ_cols_windows(fp):  # pragma: no cover
  try:
    from ctypes import windll, create_string_buffer
    import struct
    from sys import stdin, stdout

    io_handle = -12  # assume stderr
    if fp == stdin:
      io_handle = -10
    elif fp == stdout:
      io_handle = -11

    h = windll.kernel32.GetStdHandle(io_handle)
    csbi = create_string_buffer(22)
    res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    if res:
      (_bufx, _bufy, _curx, _cury, _wattr, left, _top, right, _bottom,
       _maxx, _maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
      # nlines = bottom - top + 1
      return right - left  # +1
  except:
    pass
  return None


def _environ_cols_tput(*args):  # pragma: no cover
  """cygwin xterm (windows)"""
  try:
    import shlex
    cols = int(subprocess.check_call(shlex.split('tput cols')))
    # rows = int(subprocess.check_call(shlex.split('tput lines')))
    return cols
  except:
    pass
  return None


def _environ_cols_linux(fp):  # pragma: no cover

  # import os
  # if fp is None:
  #   try:
  #     fp = os.open(os.ctermid(), os.O_RDONLY)
  #   except:
  #     pass
  try:
    from termios import TIOCGWINSZ
    from fcntl import ioctl
    from array import array
  except ImportError:
    return None
  else:
    try:
      return array('h', ioctl(fp, TIOCGWINSZ, '\0' * 8))[1]
    except:
      try:
        from os.environ import get
      except ImportError:
        return None
      else:
        return int(get('COLUMNS', 1)) - 1


def _environ_cols_wrapper():  # pragma: no cover
  """
  Return a function which gets width and height of console
  (linux,osx,windows,cygwin).

  Based on https://raw.githubusercontent.com/tqdm/tqdm/master/tqdm/_utils.py
  """
  import platform
  current_os = platform.system()
  _environ_cols = None
  if current_os in ['Windows', 'cli']:
    _environ_cols = _environ_cols_windows
    if _environ_cols is None:
      _environ_cols = _environ_cols_tput
  if any(current_os.startswith(i) for i in
         ['CYGWIN', 'MSYS', 'Linux', 'Darwin', 'SunOS', 'FreeBSD']):
    _environ_cols = _environ_cols_linux
  return _environ_cols


TERM_WIDTH = _environ_cols_wrapper()(sys.stdout)
if not TERM_WIDTH:
  # non interactive pipe
  TERM_WIDTH = 256


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
      left[k] += val
    elif hasattr(val, 'extend'):
      left[k].extend(val)
    elif hasattr(val, 'update'):
      left[k].update(val)
    else:
      raise TypeError(val)
  return left
