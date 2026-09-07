import logging
import operator
import re
import subprocess
import sys
from json import loads
from pathlib import Path
from textwrap import dedent
from xml.etree import ElementTree

from pytest import fixture, importorskip, mark, raises, skip

from gitfame import _gitfame, main

ROOT = Path(__file__).parent.parent

# test data
auth_stats = {
    'Not Committed Yet': {
        'files': {'gitfame/_gitfame.py', 'gitfame/_utils.py', 'Makefile', 'MANIFEST.in'}, 'loc': 75, 'atimes': [],
        'commits': 0},
    'Casper da Costa-Luis': {
        'files': {
            'gitfame/_utils.py', 'gitfame/__main__.py', 'setup.cfg', 'gitfame/_gitfame.py', 'gitfame/__init__.py',
            'git-fame_completion.bash', 'Makefile', 'MANIFEST.in', '.gitignore', 'setup.py'}, 'loc': 538,
        'atimes': [
            1510942009, 1517426360, 1532103452, 1543323944, 1548030670, 1459558286, 1510942009, 1459559144, 1481150373,
            1510942009, 1548030670, 1517178199, 1481150379, 1517426360, 1548030670, 1459625059, 1510942009, 1517426360,
            1481150373, 1517337751, 1517426360, 1510942009, 1548030670, 1459099074, 1459598664, 1517337751, 1517176447,
            1552697404, 1546630326, 1543326881, 1459558286, 1481150373, 1510930168, 1459598664, 1517596988],
        'commits': 35}}
stats_tot = {'files': 14, 'loc': 613, 'commits': 35}


@fixture
def git_repo(tmp_path):
    """`git_repo({name: contents, ...}) -> path`: commits files"""
    def init(files, path=tmp_path, message="initial", author="pytest <pytest@local.host>"):
        subprocess.check_call(["git", "init", "-q", path])
        for name, content in files.items():
            dest = path / name
            dest.write_bytes(content) if isinstance(content, bytes) else dest.write_text(content)
        for cmd in (["add", "-A"], [
                "-c", "user.name=pytest", "-c", "user.email=pytest@local.host", "commit", "--no-gpg-sign", "--author",
                author, "-qm", message]):
            subprocess.check_call(["git", "-C", path] + cmd)
        return path

    return init


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

    assert "Total hours" not in _gitfame.tabulate(auth_stats, stats_tot, cost={"months"}, width=256)
    assert "Total months" not in _gitfame.tabulate(auth_stats, stats_tot, cost={"hours"}, width=256)


def test_tabulate_yaml():
    """Test YAML tabulate"""
    importorskip('yaml')
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
    assert (_gitfame.tabulate(auth_stats, stats_tot, backend='yaml') in res)


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
    assert (_gitfame.tabulate(auth_stats, stats_tot, backend='simple') == dedent("""\
      Total commits: 35
      Total files: 14
      Total loc: 613
      Author                  loc    coms    fils   distribution
      --------------------  -----  ------  ------  ---------------
      Casper da Costa-Luis    538      35      10  87.8/ 100/71.4
      Not Committed Yet        75       0       4  12.2/ 0.0/28.6"""))


def test_tabulate_svg_escape():
    """Test SVG tabulate escapes markup in author names"""
    stats = {'<script/> & co': {'files': {'setup.py'}, 'loc': 1, 'atimes': [], 'commits': 1}}
    svg = _gitfame.tabulate(stats, {'files': 1, 'loc': 1, 'commits': 1}, backend='svg')
    ElementTree.fromstring(svg) # must be well-formed XML
    assert '<script' not in svg
    assert '&lt;script/&gt; &amp; co' in svg


SVG_NS = {'': 'http://www.w3.org/2000/svg'}


def svg_grid(svg, cmp=operator.eq):
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
        assert cmp(char_width * col, size['width']), 'row does not span the viewport'
        rows.append(cells)
    assert rows and size['height'] >= font_size * (len(rows) + 0.5)
    return size['width'], font_size, rows


@mark.parametrize('backend', _gitfame.FORMATS)
def test_tabulate_formats(backend):
    if backend in ('yaml', 'yml'):
        importorskip('yaml')
    tab = _gitfame.tabulate(auth_stats, stats_tot, backend=backend)
    if not backend.startswith('svg'):
        skip(backend)
    assert tab.startswith('<svg ') and tab.endswith('</svg>')
    ragged = backend == 'svg' or any(backend == f'svg-{i}' for i in ('fame', 'rst', 'plain', 'simple', 'presto'))
    width, font_size, rows = svg_grid(tab, operator.le if ragged else operator.eq)
    # the viewport must fit the text (rendered at `font-size` in a `0.6em`-advance monospace)
    assert width >= 0.6 * font_size * len(''.join(text for _, text in rows[0]))


def test_tabulate_svg_grapheme_clusters():
    """Test SVG tabulate aligns rows containing multi-codepoint graphemes"""
    # 5 codepoints drawn as 3 clusters: a whole-row `textLength` would squeeze the entire row
    name = 'सौगात'
    stats = {
        name: {'files': {'setup.py'}, 'loc': 1, 'atimes': [], 'commits': 1},
        'ASCII': {'files': {'setup.py'}, 'loc': 1, 'atimes': [], 'commits': 1}}
    svg = _gitfame.tabulate(stats, {'files': 1, 'loc': 2, 'commits': 2}, backend='svg-grid')
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
    with raises(ValueError, match='(?i)unknown'):
        _gitfame.tabulate(auth_stats, stats_tot, backend='1337')


@mark.parametrize('params', [['--sort', 'commits'], ['--no-regex'], ['--no-regex', '--incl', 'setup.py,README.rst'],
                             ['--excl', r'.*\.py'], ['--loc', 'ins,del'], ['--cost', 'hour'], ['--cost', 'month'],
                             ['--cost', 'month', '--excl', r'.*\.py'], ['-e'], ['-w'], ['-M'], ['-C'], ['-t'],
                             ['--show=name,email'], ['--format=csv'], ['--format=svg'], ['-j', '1'], ['-j', '4'],
                             ['--auth=first'], ['--auth=share', '--loc', 'ins,del']]) # yapf: disable
def test_options(params):
    """Test command line options"""
    main(['-s'] + params)


def test_main():
    """Test command line pipes"""
    res = subprocess.check_output((sys.executable, '-c',
                                   dedent(f'''\
      import gitfame
      import sys
      sys.argv = ["", "--silent-progress", r"{ROOT}"]
      gitfame.main()
      ''')), stderr=subprocess.STDOUT, text=True)

    assert 'Total commits' in res


def test_main_errors(capsys):
    """Test bad options"""
    main(['--silent-progress'])

    capsys.readouterr() # clear output
    with raises(SystemExit):
        main(['--bad', 'arg'])
    assert ' '.join(capsys.readouterr().err.split()[:2]) == "usage: git-fame"

    with raises(SystemExit):
        main(['-s', '--sort', 'badSortArg'])
    assert "badSortArg" in capsys.readouterr().err


def test_multiple_gitdirs():
    """test multiple gitdirs"""
    main(['.', '.'])


def test_multiple_gitdirs_loc(capsys, monkeypatch, tmp_path, git_repo):
    """test surviving loc are counted for each of multiple gitdirs"""
    for name in ("repo_a", "repo_b"):
        git_repo({f"{name}.txt": "one\ntwo\nthree\n"}, tmp_path / name)

    monkeypatch.chdir(tmp_path) # relative gitdirs, as reported
    capsys.readouterr()         # clear output
    main(['-s', "repo_a", "repo_b"])
    out = capsys.readouterr().out

    assert "Total loc: 6" in out
    assert "Total files: 2" in out


def test_jobs_determinism(capsys):
    """--jobs must not change output"""
    main(['-s', '--format=json', '-j', '1', str(ROOT)])
    serial = capsys.readouterr().out
    main(['-s', '--format=json', '-j', '4', str(ROOT)])
    parallel = capsys.readouterr().out
    assert serial == parallel
    assert loads(serial)['total']['loc'] > 0


def test_blame_failure_determinism(capsys, caplog, monkeypatch):
    """Blame failures are reported identically (files, order, log level) at any --jobs"""
    failing = ['LICENCE'] # text files, in `ls-files` order
    real_check_output = _gitfame.check_output

    def fake_check_output(args, *a, **k):
        if args[3:4] == ['blame'] and args[-1] in failing:
            raise subprocess.CalledProcessError(1, args)
        return real_check_output(args, *a, **k)

    monkeypatch.setattr(_gitfame, 'check_output', fake_check_output)
    caplog.set_level(logging.DEBUG, logger='gitfame._gitfame')
    runs = []
    for jobs in ('1', '4'):
        caplog.clear()
        main(['-s', '--format=json', '-j', jobs, str(ROOT)])
        out = capsys.readouterr().out
        reported = [(r.levelname, r.getMessage()) for r in caplog.records
                    if r.name == 'gitfame._gitfame' and r.getMessage().split(':', 1)[0] in failing]
        runs.append((out, reported))

    (serial_out, serial_log), (parallel_out, parallel_log) = runs
    # both runs report the same files, in `file_list` order, at the same level
    assert serial_log == parallel_log
    assert [level for level, _ in serial_log] == ['DEBUG']
    assert [msg.split(':', 1)[0] for _, msg in serial_log] == failing
    # and the report itself is byte-identical (and non-empty)
    assert serial_out == parallel_out
    assert loads(serial_out)['total']['loc'] > 0


@mark.parametrize(['strat', 'credit'], [('git', {'pytest': [6, 2, 2]}),
                                        ('first', {'pytest': [2, 1, 1], 'assist': [4, 1, 1]}),
                                        ('share', {'pytest': [4, 1.5, 2], 'assist': [2, 0.5, 1]})])
@mark.parametrize('trailer', ['Co-authored-by', 'Assisted-by', 'Generated-by'])
@mark.parametrize('loc', ['surviving', 'ins'])
def test_coauthors(capsys, git_repo, loc, trailer, strat, credit):
    """`{Co-authored,Assisted}-by` credit strategies (#101)"""
    repo = git_repo({"solo.txt": "one\ntwo\n"})
    git_repo({"shared.txt": "one\ntwo\nthree\nfour\n"}, repo,
             message=f"shared\n\n{trailer}: assist <assist@local.host>")

    main(['-s', '--format=json', '--loc', loc, '--auth', strat, str(repo)])
    assert {i[0]: i[1:4] for i in loads(capsys.readouterr().out)['data']} == credit # {author: [loc, coms, fils]}


def test_coauthors_mailmap(capsys, git_repo):
    """`.mailmap` is applied to `Co-authored-by`"""
    repo = git_repo({"shared.txt": "one\ntwo\n", ".mailmap": "pytest <pytest@local.host> <assist@local.host>\n"},
                    message="shared\n\nCo-authored-by: assist <assist@local.host>")

    main(['-s', '--format=json', '--auth=share', str(repo)])
    assert [i[0] for i in loads(capsys.readouterr().out)['data']] == ['pytest']


def test_ignore_revs(capsys, git_repo):
    """`--ignore-rev` credits the previous commit & accepts a comma-separated list"""
    repo = git_repo({"f.txt": "one\ntwo\nthree\n"})
    for line in ("ONE\ntwo\nthree\n", "ONE\ntwo\nTHREE\n"):
        git_repo({"f.txt": line}, repo, message="format", author="bot <bot@local.host>")
    revs = subprocess.check_output(["git", "-C", repo, "log", "--format=%H"], text=True).split()[:2]

    def loc(*params):
        main(['-s', '--format=json'] + list(params) + [str(repo)])
        return {i[0]: i[1] for i in loads(capsys.readouterr().out)['data']}

    assert loc() == {'bot': 2, 'pytest': 1}
    assert loc(f'--ignore-rev={revs[0]}') == {'bot': 1, 'pytest': 2}
    assert loc('--ignore-rev=' + ','.join(revs) + ',') == {'bot': 0, 'pytest': 3}


@fixture
def bot_repo(git_repo):
    """repo where `bot[x]` reformatted both of `pytest`'s lines"""
    repo = git_repo({"f.txt": "one\ntwo\n"})
    git_repo({"f.txt": "ONE\nTWO\n"}, repo, message="format", author="bot[x] <bot@local.host>")
    return repo


@mark.parametrize(['params', 'ignored'], [([], False), (['-n', '--ignore-author=bot[x]'], True),
                                          ([r'--ignore-author=bot\[x\]'], True),
                                          (['-n', '--ignore-author=nobody,bot[x]'], True),
                                          (['--ignore-author=bot[x]'], False)])
def test_ignore_author(capsys, bot_repo, params, ignored):
    main(['-s', '--format=json'] + params + [str(bot_repo)])
    credit = {i[0]: i[1:3] for i in loads(capsys.readouterr().out)['data']} # {author: [loc, coms]}

    assert credit == ({'pytest': [2, 1], 'bot[x]': [0, 1]} if ignored else {'bot[x]': [2, 1], 'pytest': [0, 1]})


def test_ignore_author_churn(capsys, caplog, bot_repo):
    caplog.set_level(logging.WARNING, logger='gitfame._gitfame')
    main(['-s', '--format=json', '--loc=ins', '-n', '--ignore-author=bot[x]', str(bot_repo)])

    assert {i[0]: i[1] for i in loads(capsys.readouterr().out)['data']} == {'bot[x]': 2, 'pytest': 2}
    assert any('--loc=surviving' in r.getMessage() for r in caplog.records)


def test_warn_binary_order(caplog, git_repo):
    """Binary file warnings are emitted in `ls-files` order (#130)"""
    names = [f"bin_{c}.dat" for c in "abcdefgh"]
    repo = git_repo({**{name: b"\x00\x01" + name.encode() for name in names}, "text.txt": "one\n"})

    caplog.set_level(logging.DEBUG, logger='gitfame._gitfame')
    main(['-s', '--warn-binary', str(repo)])

    warned = [
        r.getMessage().split(':', 1)[1] for r in caplog.records
        if r.name == 'gitfame._gitfame' and r.getMessage().startswith('binary:')]
    assert warned == names
