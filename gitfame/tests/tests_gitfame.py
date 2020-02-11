from __future__ import unicode_literals

import sys
from os import path
from shutil import rmtree
from tempfile import mkdtemp
# import re
# from nose import with_setup
from nose.plugins.skip import SkipTest
# from io import IOBase  # to support unicode strings
from gitfame._utils import StringIO
from gitfame import _gitfame
from gitfame import main
from textwrap import dedent

# test data
auth_stats = {
    u'Not Committed Yet': {'files': set([
        'gitfame/_gitfame.py', 'gitfame/_utils.py', 'Makefile', 'MANIFEST.in'
    ]),
        'loc': 75, 'ctimes': [], 'commits': 0},
    u'Casper da Costa-Luis': {'files': set([
        'gitfame/_utils.py', 'gitfame/__main__.py', 'setup.cfg',
        'gitfame/_gitfame.py', 'gitfame/__init__.py',
        'git-fame_completion.bash', 'Makefile', 'MANIFEST.in', '.gitignore',
        'setup.py']), 'loc': 538, 'ctimes': [
        1510942009, 1517426360, 1532103452, 1543323944, 1548030670, 1459558286,
        1510942009, 1459559144, 1481150373, 1510942009, 1548030670, 1517178199,
        1481150379, 1517426360, 1548030670, 1459625059, 1510942009, 1517426360,
        1481150373, 1517337751, 1517426360, 1510942009, 1548030670, 1459099074,
        1459598664, 1517337751, 1517176447, 1552697404, 1546630326, 1543326881,
        1459558286, 1481150373, 1510930168, 1459598664, 1517596988],
        'commits': 35}
}
stats_tot = {'files': 14, 'loc': 613, 'commits': 35}


def test_tabulate():
  """Test builtin tabulate"""
  assert (_gitfame.tabulate(auth_stats, stats_tot) == dedent("""\
    Total commits: 35
    Total files: 14
    Total loc: 613
    | Author               |   loc |   coms |   fils |  distribution   |
    |:---------------------|------:|-------:|-------:|:----------------|
    | Casper da Costa-Luis |   538 |     35 |     10 | 87.8/ 100/71.4  |
    | Not Committed Yet    |    75 |      0 |      4 | 12.2/ 0.0/28.6  |"""))

  sys.stderr.write("\rTest builtin tabulate ... ")  # `tqdm` may clear info


def test_tabulate_cost():
  """Test cost estimates"""
  assert (_gitfame.tabulate(
      auth_stats, stats_tot, cost="hours,COCOMO") == dedent("""\
    Total commits: 35
    Total files: 14
    Total hours: 5.5
    Total loc: 613
    Total months: 1.9
    | Author               |   hrs |   mths |   loc |   coms |   fils \
|  distribution   |
    |:---------------------|------:|-------:|------:|-------:|-------:\
|:----------------|
    | Casper da Costa-Luis |     4 |      2 |   538 |     35 |     10 \
| 87.8/ 100/71.4  |
    | Not Committed Yet    |     2 |      0 |    75 |      0 |      4 \
| 12.2/ 0.0/28.6  |"""))


def test_tabulate_yaml():
  """Test YAML tabulate"""
  res = [
      dedent("""\
      columns:
      - Author
      - loc
      - coms
      - fils
      - '%loc'
      - '%coms'
      - '%fils'
      data:
      - - Casper da Costa-Luis
        - 538
        - 35
        - 10
        - 87.8
        - 100.0
        - 71.4
      - - Not Committed Yet
        - 75
        - 0
        - 4
        - 12.2
        - 0.0
        - 28.6
      total:
        commits: 35
        files: 14
        loc: 613"""),
      # pyyaml<5
      dedent("""\
      columns: [Author, loc, coms, fils, '%loc', '%coms', '%fils']
      data:
      - [Casper da Costa-Luis, 538, 35, 10, 87.8, 100.0, 71.4]
      - [Not Committed Yet, 75, 0, 4, 12.2, 0.0, 28.6]
      total: {commits: 35, files: 14, loc: 613}""")]
  try:
    assert (_gitfame.tabulate(auth_stats, stats_tot, backend='yaml') in res)
  except ImportError:
    raise SkipTest


def test_tabulate_json():
  """Test JSON tabulate"""
  from json import loads
  res = loads(_gitfame.tabulate(auth_stats, stats_tot, backend='json'))
  assert (res == loads(dedent("""\
    {"total": {"files": 14, "loc": 613, "commits": 35},
    "data": [["Casper da Costa-Luis", 538, 35, 10, 87.8, 100.0, 71.4],
    ["Not Committed Yet", 75, 0, 4, 12.2, 0.0, 28.6]],
    "columns": ["Author", "loc", "coms", "fils",
    "%loc", "%coms", "%fils"]}""").replace('\n', ' ')))


def test_tabulate_csv():
  """Test CSV tabulate"""
  csv = _gitfame.tabulate(auth_stats, stats_tot, backend='csv')
  tsv = _gitfame.tabulate(auth_stats, stats_tot, backend='tsv')
  assert (csv.replace(',', '\t') == tsv)


def test_tabulate_tabulate():
  """Test external tabulate"""
  try:
    assert (_gitfame.tabulate(
        auth_stats, stats_tot, backend='simple') == dedent("""\
      Total commits: 35
      Total files: 14
      Total loc: 613
      Author                  loc    coms    fils   distribution
      --------------------  -----  ------  ------  ---------------
      Casper da Costa-Luis    538      35      10  87.8/ 100/71.4
      Not Committed Yet        75       0       4  12.2/ 0.0/28.6"""))
  except ImportError:
    raise SkipTest


def test_tabulate_unknown():
  """Test unknown tabulate format"""
  try:
    _gitfame.tabulate(auth_stats, stats_tot, backend='1337')
  except ValueError as e:
    if "unknown" not in str(e).lower():
      raise
  else:
    raise ValueError("Should not support unknown tabulate format")


# WARNING: this should be the last test as it messes with sys.argv
def test_main():
  """Test command line pipes"""
  import subprocess
  from os.path import dirname as dn

  res = subprocess.Popen(
      (sys.executable, '-c', 'import gitfame; import sys;\
       sys.argv = ["", "--silent-progress", "%s"];\
       gitfame.main()' % dn(dn(dn(__file__)))),
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT).communicate()[0]

  # actual test:

  assert ('Total commits' in str(res))

  # semi-fake test which gets coverage:

  _SYS_AOE = sys.argv, sys.stdout, sys.stderr
  sys.stdout = StringIO()
  sys.stderr = sys.stdout

  # sys.argv = ['', '--silent-progress']
  # import gitfame.__main__  # NOQA
  main(['--silent-progress'])

  sys.stdout.seek(0)
  try:
    main(['--bad', 'arg'])
  except SystemExit:
    res = ' '.join(sys.stdout.getvalue().strip().split()[:2])
    if res != "usage: gitfame":
      raise ValueError(sys.stdout.getvalue())
  else:
    raise ValueError("Expected --bad arg to fail")

  sys.stdout.seek(0)
  try:
    main(['-s', '--sort', 'badSortArg'])
  except KeyError as e:
    if "badSortArg" not in str(e):
      raise ValueError("Expected `--sort=badSortArg` to fail")

  for params in [
      ['--sort', 'commits'],
      ['--no-regex'],
      ['--no-regex', '--incl', 'setup.py,README.rst'],
      ['--excl', r'.*\.py'],
      ['-w'],
      ['-M'],
      ['-C'],
      ['-t']
  ]:
    main(['-s'] + params)

  # test --manpath
  tmp = mkdtemp()
  man = path.join(tmp, "git-fame.1")
  assert not path.exists(man)
  try:
    main(['--manpath', tmp])
  except SystemExit:
    pass
  else:
    raise SystemExit("Expected system exit")
  assert path.exists(man)
  rmtree(tmp, True)

  # test multiple gitdirs
  main(['.', '.'])

  sys.argv, sys.stdout, sys.stderr = _SYS_AOE
