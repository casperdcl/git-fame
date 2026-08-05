import re
import sys
from json import loads
from os import path
from shutil import rmtree
from tempfile import mkdtemp
from textwrap import dedent
from xml.etree import ElementTree

from pytest import mark, raises, skip

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


SVG_NS = {'': 'http://www.w3.org/2000/svg'}


def svg_grid(svg):
    """(viewport width, `font-size`, rows of `(column, text)` cells) of a tabulated SVG"""
    # must be well-formed XML
    root = ElementTree.fromstring(svg)
    size = {}
    for i in ('width', 'height'):
        value, unit = re.fullmatch('([\\d.]+)(.*)', root.get(i)).groups()
        # `em` would refer to the `<svg>`'s own font size rather than to `font-size` below
        assert not unit, f'viewport {i}="{value}{unit}" is not in user units'
        size[i] = float(value)
    text = root.find('text', SVG_NS)
    font_size = float(text.get('font-size'))
    # a monospace advance; `textLength` makes it exact for any font
    char_width = 0.6 * font_size

    rows = []
    for row in text.findall('tspan', SVG_NS):
        cells, col = [], 0
        for cell in row.findall('tspan', SVG_NS):
            # each cell is pinned to & stretched over its own columns, so that a cell whose
            # glyphs don't advance by `char_width` cannot displace the ones after it
            assert float(cell.get('x')) == char_width * col
            assert float(cell.get('textLength')) == char_width * len(cell.text)
            cells.append((col, cell.text))
            col += len(cell.text)
        assert char_width * col == size['width'], 'row does not span the viewport'
        rows.append(cells)
    assert rows and size['height'] >= font_size * (len(rows) + 0.5)
    return size['width'], font_size, rows


def test_tabulate_svg():
    """Test SVG tabulate"""
    svg = _gitfame.tabulate(auth_stats, stats_tot, backend='svg')
    assert svg.startswith('<svg ') and svg.endswith('</svg>')
    width, font_size, rows = svg_grid(svg)
    # the viewport must fit the text (rendered at `font-size` in a `0.6em`-advance monospace)
    assert width >= 0.6 * font_size * len(''.join(text for _, text in rows[0]))


def test_tabulate_svg_grapheme_clusters():
    """Test SVG tabulate aligns rows containing multi-codepoint graphemes"""
    # 5 codepoints drawn as 3 clusters: a whole-row `textLength` would squeeze the entire row
    name = 'सौगात'
    stats = {
        name: {'files': {'setup.py'}, 'loc': 1, 'ctimes': [], 'commits': 1},
        'ASCII': {'files': {'setup.py'}, 'loc': 1, 'ctimes': [], 'commits': 1}}
    svg = _gitfame.tabulate(stats, {'files': 1, 'loc': 2, 'commits': 2}, backend='svg')
    # `svg_grid` asserts that every cell sits on the character grid
    _, _, rows = svg_grid(svg)
    # the name is drawn as one cell, so its clusters stay intact
    assert any(text.strip() == name for row in rows for _, text in row)
    # ... and the separators are at the same columns on every row which has them
    seps = {tuple(col for col, text in row) for row in rows if len(row) > 1}
    assert len(seps) == 1


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


@mark.parametrize(
    'params',
    [['--sort', 'commits'], ['--no-regex'], ['--no-regex', '--incl', 'setup.py,README.rst'], ['--excl', r'.*\.py'],
     ['--loc', 'ins,del'], ['--cost', 'hour'], ['--cost', 'month'], ['--cost', 'month', '--excl', r'.*\.py'], ['-e'],
     ['-w'], ['-M'], ['-C'], ['-t'], ['--show=name,email'], ['--format=csv'], ['--format=svg']])
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
        if res != "usage: git-fame":
            raise ValueError(out)
    else:
        raise ValueError("Expected --bad arg to fail")

    capsys.readouterr() # clear output
    with raises(SystemExit):
        main(['-s', '--sort', 'badSortArg'])
    if "badSortArg" not in capsys.readouterr().err:
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
            commit = [
                "-c", "user.name=tester", "-c", "user.email=tester@example.com", "commit", "--no-gpg-sign", "-qm",
                "initial"]
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
