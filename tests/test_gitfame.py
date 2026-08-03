import re
import sys
from json import loads
from os import path
from shutil import rmtree
from tempfile import mkdtemp
from textwrap import dedent
from xml.etree import ElementTree

from pytest import mark, skip

from gitfame import _gitfame, main

# test data
auth_stats = {
    'Not Committed Yet': {
        'files': {'gitfame/_gitfame.py', 'gitfame/_utils.py', 'Makefile', 'MANIFEST.in'}, 'loc': 75, 'ctimes': [],
        'commits': 0},
    'Casper da Costa-Luis': {
        'files': {
            'gitfame/_utils.py', 'gitfame/__main__.py', 'setup.cfg', 'gitfame/_gitfame.py', 'gitfame/__init__.py',
            'git-fame_completion.bash', 'Makefile', 'MANIFEST.in', '.gitignore', 'setup.py'}, 'loc': 538,
        'ctimes': [
            1510942009, 1517426360, 1532103452, 1543323944, 1548030670, 1459558286, 1510942009, 1459559144, 1481150373,
            1510942009, 1548030670, 1517178199, 1481150379, 1517426360, 1548030670, 1459625059, 1510942009, 1517426360,
            1481150373, 1517337751, 1517426360, 1510942009, 1548030670, 1459099074, 1459598664, 1517337751, 1517176447,
            1552697404, 1546630326, 1543326881, 1459558286, 1481150373, 1510930168, 1459598664, 1517596988],
        'commits': 35}}
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

    assert "Not Committed Yet" not in _gitfame.tabulate(auth_stats, stats_tot, min_sort_val=76)


def test_tabulate_cost():
    """Test cost estimates"""
    assert (_gitfame.tabulate(auth_stats, stats_tot, cost={"hours", "months"}, width=256) == dedent("""\
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
        dedent("""\
      columns: [Author, loc, coms, fils, '%loc', '%coms', '%fils']
      data:
      - [Casper da Costa-Luis, 538, 35, 10, 87.8, 100.0, 71.4]
      - [Not Committed Yet, 75, 0, 4, 12.2, 0.0, 28.6]
      total: {commits: 35, files: 14, loc: 613}""")]
    try:
        assert (_gitfame.tabulate(auth_stats, stats_tot, backend='yaml') in res)
    except ImportError as err: # lacking pyyaml<5
        raise skip(str(err))


def test_tabulate_json():
    """Test JSON tabulate"""
    res = loads(_gitfame.tabulate(auth_stats, stats_tot, backend='json'))
    assert (res == loads(
        dedent("""\
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
        assert (_gitfame.tabulate(auth_stats, stats_tot, backend='simple') == dedent("""\
      Total commits: 35
      Total files: 14
      Total loc: 613
      Author                  loc    coms    fils   distribution
      --------------------  -----  ------  ------  ---------------
      Casper da Costa-Luis    538      35      10  87.8/ 100/71.4
      Not Committed Yet        75       0       4  12.2/ 0.0/28.6"""))
    except ImportError as err:
        raise skip(str(err))


def test_tabulate_svg_escape():
    """Test SVG tabulate escapes markup in author names"""
    stats = {'<script/> & co': {'files': {'setup.py'}, 'loc': 1, 'ctimes': [], 'commits': 1}}
    svg = _gitfame.tabulate(stats, {'files': 1, 'loc': 1, 'commits': 1}, backend='svg')
    ElementTree.fromstring(svg) # must be well-formed XML
    assert '<script' not in svg
    assert '&lt;script/&gt; &amp; co' in svg


def test_tabulate_svg():
    """Test SVG tabulate"""
    svg = _gitfame.tabulate(auth_stats, stats_tot, backend='svg')
    assert svg.startswith('<svg ') and svg.endswith('</svg>')
    rows = re.findall('<tspan[^>]*>(.*?)</tspan>', svg)
    assert rows and len(set(map(len, rows))) == 1

    size = {}
    for i in ('width', 'height'):
        value, unit = re.search(f'{i}="([\\d.]+)([^"]*)"', svg).groups()
        # `em` would refer to the `<svg>`'s own font size rather than to `font-size` below
        assert not unit, f'viewport {i}="{value}{unit}" is not in user units'
        size[i] = float(value)
    width, height = size['width'], size['height']

    # the viewport must fit the text (rendered at `font-size` in a `0.6em`-advance monospace)
    font_size = float(re.search('font-size="([\\d.]+)"', svg).group(1))
    assert width >= 0.6 * font_size * len(rows[0])
    assert height >= font_size * (len(rows) + 0.5)
    # ... and the text must be forced to fit, whatever the font's actual metrics
    assert [float(i) for i in re.findall('textLength="([\\d.]+)"', svg)] == [width] * len(rows)


def test_tabulate_enum():
    """Test --enum tabulate"""
    res = loads(_gitfame.tabulate(auth_stats, stats_tot, backend='json', row_nums=True))
    assert res['columns'][0] == '#'
    assert [int(i[0]) for i in res['data']] == [1, 2]


def test_tabulate_unknown():
    """Test unknown tabulate format"""
    try:
        _gitfame.tabulate(auth_stats, stats_tot, backend='1337')
    except ValueError as e:
        if "unknown" not in str(e).lower():
            raise
    else:
        raise ValueError("Should not support unknown tabulate format")


@mark.parametrize('params', [['--sort', 'commits'], ['--no-regex'], ['--no-regex', '--incl', 'setup.py,README.rst'],
                             ['--excl', r'.*\.py'], ['--loc', 'ins,del'], ['--cost', 'hour'], ['--cost', 'month'],
                             ['--cost', 'month', '--excl', r'.*\.py'], ['-e'], ['-w'], ['-j', '1'], ['-j', '4'], ['-M'],
                             ['-C'], ['-t'], ['--show=name,email'], ['--format=csv'], ['--format=svg']])
def test_options(params):
    """Test command line options"""
    main(['-s'] + params)


def test_main():
    """Test command line pipes"""
    import subprocess
    from os.path import dirname as dn

    res = subprocess.Popen((sys.executable, '-c',
                            dedent('''\
      import gitfame
      import sys
      sys.argv = ["", "--silent-progress", r"''' + dn(dn(__file__)) + '''"]
      gitfame.main()
      ''')), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]

    assert ('Total commits' in str(res))


def test_main_errors(capsys):
    """Test bad options"""
    main(['--silent-progress'])

    capsys.readouterr() # clear output
    try:
        main(['--bad', 'arg'])
    except SystemExit:
        out = capsys.readouterr()
        res = ' '.join(out.err.strip().split()[:2])
        if res != "usage: gitfame":
            raise ValueError(out)
    else:
        raise ValueError("Expected --bad arg to fail")

    capsys.readouterr() # clear output
    try:
        main(['-s', '--sort', 'badSortArg'])
    except KeyError as e:
        if "badSortArg" not in str(e):
            raise ValueError("Expected `--sort=badSortArg` to fail")


def test_manpath():
    """Test --manpath"""
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


def test_multiple_gitdirs():
    """test multiple gitdirs"""
    main(['.', '.'])


def test_multiple_gitdirs_loc(capsys):
    """test surviving loc are counted for each of multiple gitdirs"""
    import subprocess
    from os import chdir, getcwd
    tmp = mkdtemp()
    cwd = getcwd()
    try:
        for name in ("repo_a", "repo_b"):
            repo = path.join(tmp, name)
            subprocess.check_call(["git", "init", "-q", repo])
            with open(path.join(repo, name + ".txt"), 'w') as fd:
                fd.write("one\ntwo\nthree\n")
            commit = ["-c", "user.name=tester", "-c", "user.email=tester@example.com", "commit", "-qm", "initial"]
            for cmd in (["add", "-A"], commit):
                subprocess.check_call(["git", "-C", repo] + cmd)

        chdir(tmp)          # relative gitdirs, as reported
        capsys.readouterr() # clear output
        main(['-s', "repo_a", "repo_b"])
        out = capsys.readouterr().out
    finally:
        chdir(cwd)
        rmtree(tmp, True)

    assert "Total loc: 6" in out
    assert "Total files: 2" in out


def test_jobs_determinism(capsys):
    """--jobs must not change output"""
    root = path.dirname(path.dirname(__file__))
    main(['-s', '--format=json', '-j', '1', root])
    serial = capsys.readouterr().out
    main(['-s', '--format=json', '-j', '4', root])
    parallel = capsys.readouterr().out
    assert serial == parallel
    assert loads(serial)['total']['loc'] > 0


def test_blame_failure_determinism(capsys, caplog):
    """Blame failures are reported identically (files, order, log level) at any --jobs"""
    import logging
    import subprocess
    from unittest.mock import patch

    root = path.dirname(path.dirname(__file__))
    failing = ['LICENCE', 'Makefile'] # text files, in `ls-files` order
    real_check_output = _gitfame.check_output

    def fake_check_output(args, *a, **k):
        if args[3:4] == ['blame'] and args[-1] in failing:
            raise subprocess.CalledProcessError(1, args)
        return real_check_output(args, *a, **k)

    caplog.set_level(logging.DEBUG, logger='gitfame._gitfame')
    runs = []
    for jobs in ('1', '4'):
        with patch.object(_gitfame, 'check_output', fake_check_output):
            caplog.clear()
            main(['-s', '--format=json', '-j', jobs, root])
            out = capsys.readouterr().out
        reported = [(r.levelname, r.getMessage()) for r in caplog.records
                    if r.name == 'gitfame._gitfame' and r.getMessage().split(':', 1)[0] in failing]
        runs.append((out, reported))

    (serial_out, serial_log), (parallel_out, parallel_log) = runs
    # both runs report the same files, in `file_list` order, at the same level
    assert serial_log == parallel_log
    assert [level for level, _ in serial_log] == ['DEBUG', 'DEBUG']
    assert [msg.split(':', 1)[0] for _, msg in serial_log] == failing
    # and the report itself is byte-identical (and non-empty)
    assert serial_out == parallel_out
    assert loads(serial_out)['total']['loc'] > 0
