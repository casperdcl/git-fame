from __future__ import unicode_literals
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
