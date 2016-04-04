from __future__ import unicode_literals

import sys
# import re
# from nose import with_setup
# from nose.plugins.skip import SkipTest
# from io import IOBase  # to support unicode strings
# try:
#   from StringIO import StringIO
# except:
#   from io import StringIO
from gitfame import _gitfame
from gitfame import main


def test_table_line():
  """ Test table line drawing """
  assert (_gitfame.tr_hline([3, 4, 2], hl='/', x='#') == '#///#////#//#')


def test_tabulate():
  """ Test tabulate """

  auth_stats = {
      u'Not Committed Yet': {'files': set([
          'gitfame/_gitfame.py', 'gitfame/_utils.py', 'Makefile', 'MANIFEST.in'
      ]),
          'loc': 75, 'commits': 0},
      u'Casper da Costa-Luis': {'files': set([
          'gitfame/_utils.py', 'gitfame/__main__.py', 'setup.cfg',
          'gitfame/_gitfame.py', 'gitfame/__init__.py',
          'git-fame_completion.bash', 'Makefile', 'MANIFEST.in', '.gitignore',
          'setup.py']), 'loc': 538, 'commits': 35}
  }

  stats_tot = {'files': 14, 'loc': 613, 'commits': 35}

  assert (_gitfame.tabulate(auth_stats, stats_tot) ==
          """+----------------------+-----+------+------+----------------+
| Author               | loc | coms | fils |  distribution  |
+======================+=====+======+======+================+
| Casper da Costa-Luis | 538 |   35 |   10 | 87.8/ 100/71.4 |
| Not Committed Yet    |  75 |    0 |    4 | 12.2/ 0.0/28.6 |
+----------------------+-----+------+------+----------------+""")


# WARNING: this should be the last test as it messes with sys.argv
def test_main():
  """ Test command line pipes """
  import subprocess
  from docopt import DocoptExit
  from copy import deepcopy

  res = subprocess.Popen(('python', '-m', 'gitfame', '--silent-progress'),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT).communicate()[0]

  # actual test:

  assert ('Total commits' in res)

  # semi-fake test which gets coverage:

  _SYS = deepcopy(sys.argv)

  sys.argv = ['', '--silent-progress']
  main()

  sys.argv = ['', '--bad', 'arg']
  try:
    main()
  except DocoptExit as e:
    if """Usage:
  gitfame [--help | options] [<gitdir>]""" not in str(e):
      raise

  sys.argv = ['', '-s', '--sort', 'badSortArg']
  try:
    main()
  except Warning as e:
    if "--sort argument (badSortArg) unrecognised" not in str(e):
      raise

  for params in [
      ['--sort', 'commits'],
      ['--no-regex'],
      ['--no-regex', '--incl', '.*py'],
      ['-w'],
      ['-M'],
      ['-C'],
      ['-t']
  ]:
    sys.argv = ['', '-s'] + params
    main()

  sys.argv = _SYS
