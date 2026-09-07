#!/usr/bin/env python
r"""Usage:
  git-fame [--help | options] [<gitdir>...]

Arguments:
  <gitdir>       Git directory [default: ./].
                 May be specified multiple times to aggregate across
                 multiple repositories.

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  --branch=<b>   Branch or tag [default: HEAD] up to which to check.
  --sort=<key>   [default: loc]|commits|files|hours|months.
  --min=<val>    Minimum value (of `--sort` key) to show [default: 0:int].
  --loc=<type>   surv(iving)|ins(ertions)|del(etions)
                 What `loc` represents. Use 'ins,del' to count both.
                 defaults to 'surviving' unless `--cost` is specified.
  --excl=<f>     Excluded files (default: None).
                 In no-regex mode, may be a comma-separated list.
                 Escape (\,) for a literal comma (may require \\, in shell).
  --incl=<f>     Included files [default: .*]. See `--excl` for format.
  --since=<date>  Date from which to check. Can be absolute (eg: 1970-01-31)
                  or relative to now (eg: 3.weeks).
  --until=<date>  Date to which to check. See `--since` for format.
  --cost=<method>  Include time cost in person-months (COCOMO) or
                   person-hours (based on author times).
                   Methods: month(s)|cocomo|hour(s).
                   May be multiple comma-separated values.
                   Alters `--loc` default to imply 'ins' (COCOMO) or
                   'ins,del' (hours).
  -R, --recurse  Recursively find repositories & submodules within <gitdir>.
  -n, --no-regex  Treat `--incl`, `--excl` & `--ignore-author` as
                  comma-separated exact matches rather than regular
                  expressions [default: False].
                  NB: if regex is enabled ',' is equivalent to '|'.
  -s, --silent-progress    Suppress `tqdm` [default: False].
  -j=<n>, --jobs=<n>  Number of concurrent `git blame` threads per <gitfir>
                      [default: 0:int]: automatic.
  --warn-binary  Don't silently skip files which appear to be binary data
                 [default: False].
  --auth=<strat>  Credit commit trailers (`Co-authored-by`, `Assisted-by`):
                  [default: git]|first|share, i.e.: only use 'git' author,
                  only use 'first' trailer, or 'share' equally with git &
                  all trailers.
  --show=<info>  Author information to show [default: name]|email.
                 Use 'name,email' to show both.
  -e, --show-email  Shortcut for `--show=email`.
  --enum         Show row numbers [default: False].
  -t, --bytype             Show stats per file extension [default: False].
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from [default: False].
  -M             Detect intra-file line moves and copies [default: False].
  -C             Detect inter-file line moves and copies [default: False].
  --ignore-rev=<rev>      Ignore changes made by the given revision
                          (requires `--loc=surviving`).
                          May be a comma-separated list.
  --ignore-revs-file=<f>  Ignore revisions listed in the given file
                          (requires `--loc=surviving`).
  --ignore-author=<auth>  Ignore revisions from this author regex
                          (requires `--loc=surviving`).
                          In no-regex mode, may be a comma-separated list.
                          Escape (\,) for a literal comma (may require \\, in shell).
  --format=<format>        Table format
      fame|svg|[default: md]|yaml|json|csv|tsv.
      Any `tabulate.tabulate_formats` is also accepted.
      Most formats can also be prefixex by `svg-`, e.g. `svg-fame`.
  --log=<lvl>    FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.
"""
import logging
import os
import re
import subprocess
from collections import defaultdict
from functools import partial
from importlib.metadata import PackageNotFoundError, version
from itertools import chain
from os import path

import tabulate as tabber

from ._utils import (TERM_WIDTH, Str, TqdmStream, check_output, fext, get_mapper, int_float_len, merge_stats,
                     print_unicode, tqdm)

# version detector. Precedence: installed dist, git, 'UNKNOWN'
try:
    __version__ = version('git-fame')
except PackageNotFoundError:
    __version__ = "UNKNOWN"
__author__ = "Casper da Costa-Luis <casper.dcl@physics.org>"
__date__ = "2016-2026"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__ # weird foreign language
log = logging.getLogger(__name__)

# processing `blame --line-porcelain`
RE_AUTHS_BLAME = re.compile(r'^(\w+) \d+ \d+ (\d+)\nauthor (.+?)\nauthor-mail <(.*?)>\nauthor-time (\d+)',
                            flags=re.M | re.DOTALL)
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*?)\s+<(.*)>\s*$', flags=re.M)
RE_BLAME_BOUNDS = re.compile(r'^\w+\s+\d+\s+\d+(\s+\d+)?\s*$[^\t]*?^boundary\s*$[^\t]*?^\t.*?$\r?\n',
                             flags=re.M | re.DOTALL)
# processing `log --format="aN%aN aE%aE at%at H%H" --numstat`
RE_AUTHS_LOG = re.compile(r"^aN(.+?) aE(.*?) at(\d+) H(\w+)\n\n", flags=re.M)
RE_STAT_BINARY = re.compile(r"^\s*?-\s*-.*?\n", flags=re.M)
RE_RENAME = re.compile(r"\{.+? => (.+?)\}")
# finds all non-escaped commas
# NB: does not support escaping of escaped character
RE_CSPILT = re.compile(r'(?<!\\),')
# options
COST_MONTHS = {'cocomo', 'month', 'months'}
COST_HOURS = {'author', 'authors', 'commit', 'commits', 'hour', 'hours'}
CHURN_SLOC = {'surv', 'survive', 'surviving'}
CHURN_INS = {'ins', 'insert', 'insertion', 'insertions', 'add', 'addition', 'additions', '+'}
CHURN_DEL = {'del', 'deletion', 'deletions', 'delete', '-'}
SHOW_NAME = {'name', 'n'}
SHOW_EMAIL = {'email', 'e'}
FORMATS = ['yaml', 'yml', 'json', 'csv', 'tsv', 'svg', 'md', 'markdown', 'tabulate']
tabber._table_formats['fame'] = tabber.TableFormat(lineabove=None, linebelowheader=tabber.Line("", "─", "┼", ""),
                                                   linebetweenrows=None, linebelow=tabber.Line("", "─", "┴", ""),
                                                   headerrow=tabber.DataRow("", "│",
                                                                            ""), datarow=tabber.DataRow("", "│", ""),
                                                   padding=1, with_header_hide=None)
FORMATS.extend(tabber._table_formats)
FORMATS.extend(f"svg-{i}" for i in tabber._table_formats
               if not re.search("asciidoc|html|jira|latex|mediawiki|moinmoin|textile|tsv|youtrack", i))


def hours(dates, maxCommitDiffInSec=120 * 60, firstCommitAdditionInMinutes=120):
    """
    Convert list of author times (in seconds) to an estimate of hours spent.

    https://github.com/kimmobrunfeldt/git-hours/blob/\
8aaeee237cb9d9028e7a2592a25ad8468b1f45e4/index.js#L114-L143
    """
    dates = sorted(dates)
    res = sum(diff for i, j in zip(dates[1:], dates) if (diff := i - j) < maxCommitDiffInSec)
    return (res/60.0 + firstCommitAdditionInMinutes) / 60.0


def table2svg(table, backend):
    from xml.sax.saxutils import escape  # nosec B406, yapf: disable
    table_fmt = tabber._table_formats[backend]
    seps = {
        getattr(fmtrow, i, None)
        for attr in ('lineabove', 'linebelowheader', 'linebetweenrows', 'linebelow', 'headerrow', 'datarow')
        if (fmtrow := getattr(table_fmt, attr, None)) for i in ('begin', 'sep', 'end')}
    # drop '', drop None, sort by longest first, escape regex
    row_separator = '|'.join(map(re.escape, sorted(filter(None, seps), key=len, reverse=True)))
    rows = table.split('\n')
    font_size = 15
    # typical monospace advance (`textLength` below makes it exact for any font)
    char_width = 0.6 * font_size
    # `em` in the root `<svg>`'s size refers to the (inherited) font size of the `<svg>`
    # element itself rather than to `font-size` below, so use user units instead
    svg_width = char_width * max(map(len, rows))
    # 0.2em of padding above the first & below the last row
    svg_height = font_size * (len(rows) + 0.7)

    def cells(row):
        """One `<tspan>` per cell, each pinned to & stretched over its own columns."""
        col = 0
        for cell in filter(None, re.split(f'({row_separator})', row)):
            yield (f'<tspan x="{char_width * col:g}" textLength="{char_width * len(cell):g}"'
                   f' lengthAdjust="spacingAndGlyphs">{escape(cell)}</tspan>')
            col += len(cell)

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width:g}" height="{svg_height:g}"'
            f' viewBox="0 0 {svg_width:g} {svg_height:g}">'
            '<rect x="0" y="0" width="100%" height="100%"'
            ' fill="white" fill-opacity="0.5" rx="5"/>'
            f'<text x="0" y="0.2em" font-size="{font_size}"'
            ' font-family="monospace" style="white-space: pre">' +
            ''.join(f'<tspan x="0" dy="1em">{"".join(cells(row))}</tspan>' for row in rows) + '</text></svg>')


def tabulate(auth_stats, stats_tot, sort='loc', bytype=False, backend='md', cost=None, row_nums=False, min_sort_val=0,
             width=TERM_WIDTH):
    """
    backend  : yaml, json, csv, tsv, html, or any `tabulate.tabulate_formats`
      Any tabulate format can prefixed by `svg-`.
      e.g.: md, rst, rounded_outline, svg-rounded_outline, ...
    """
    COL_NAMES = ['Author', 'loc', 'coms', 'fils', ' distribution']
    # get ready
    tab = [[
        auth, s['loc'],
        s.get('commits', 0),
        len(s.get('files', [])), '/'.join(
            map('{:4.1f}'.format,
                (100 * s['loc'] / max(1, stats_tot['loc']), 100 * s.get('commits', 0) / max(1, stats_tot['commits']),
                 100 * len(s.get('files', [])) / max(1, stats_tot['files'])))).replace('/100.0/', '/ 100/')]
           for (auth, s) in auth_stats.items()]
    if cost:
        stats_tot = dict(stats_tot)
        if cost & COST_MONTHS:
            COL_NAMES.insert(1, 'mths')
            tab = [i[:1] + [3.2 * (i[1] / 1e3)**1.05] + i[1:] for i in tab]
            stats_tot.setdefault('months', '%.1f' % sum(i[1] for i in tab))
        if cost & COST_HOURS:
            COL_NAMES.insert(1, 'hrs')
            tab = [i[:1] + [hours(auth_stats[i[0]]['atimes'])] + i[1:] for i in tab]
            stats_tot.setdefault('hours', '%.1f' % sum(i[1] for i in tab))
    # log.debug(auth_stats)

    for i, j in (("commits", "coms"), ("files", "fils"), ("hours", "hrs"), ("months", "mths")):
        sort = sort.replace(i, j)
    if min_sort_val:
        tab = [i for i in tab if i[COL_NAMES.index(sort)] >= min_sort_val]
    tab.sort(key=lambda i: i[COL_NAMES.index(sort)], reverse=True)
    if row_nums:
        tab = [[str(i)] + j for i, j in enumerate(tab, 1)]
        COL_NAMES.insert(0, '#')

    # round fractional loc (from `--auth=share`)
    totals = 'Total ' + '\nTotal '.join(f"{k}: {f'{v:.0f}' if isinstance(v, float) else v}"
                                        for k, v in sorted(stats_tot.items())) + '\n'

    if (backend := backend.lower()) in ("tabulate", "md", "markdown"):
        backend = "pipe"
    if svg := backend.startswith("svg"):
        backend = backend[3:].lstrip('-') or 'fame'

    if backend in ('yaml', 'yml', 'json', 'csv', 'tsv'):
        tab = [i[:-1] + [float(pc.strip()) for pc in i[-1].split('/')] for i in tab]
        tab = {"total": stats_tot, "data": tab, "columns": COL_NAMES[:-1] + ['%' + i for i in COL_NAMES[-4:-1]]}
        if backend in ('yaml', 'yml'):
            log.debug("backend:yaml")
            try:
                import yaml
            except ImportError as exc:
                raise RuntimeError('Try: pip install "git-fame[yaml]"') from exc
            return yaml.safe_dump(tab).rstrip()
        elif backend == 'json':
            log.debug("backend:json")
            import json
            return json.dumps(tab, ensure_ascii=False)
        elif backend in ('csv', 'tsv'):
            log.debug("backend:csv")
            import csv
            from io import StringIO

            res = StringIO()
            csv.writer(res, delimiter=',' if backend == 'csv' else '\t').writerows(
                chain([tab['columns']], tab['data'], ['', tab['total'], tab['total'].values()]))
            return res.getvalue().rstrip()
        else:      # pragma: nocover
            raise RuntimeError("Should be unreachable")

    if backend not in tabber._table_formats:
        raise ValueError(f"Unknown backend:{backend}")
    log.debug("backend:tabulate:%s", backend)
    COL_LENS = [max(map(len, map(Str, col))) for col in zip(COL_NAMES, *tab)]
    COL_LENS[0] = min(width - sum(COL_LENS[1:]) - len(COL_LENS) * 3 - 4, COL_LENS[0])
    tab = [[i[0][:COL_LENS[0]]] + i[1:] for i in tab]
    table = tabber.tabulate(tab, COL_NAMES, tablefmt=backend, floatfmt='.0f')
    if svg:
        return table2svg(table, backend)
    return totals + table


def new_stats():
    return defaultdict(int, files=set(), atimes=[])


def _get_coauthors(git_cmd, branch, strat, since=(), until=()):
    """Returns dict: {"<sha>": ("<author>", ["<credited>", ...])} of trailered commits"""
    fmt = ("--format=%x02%H%x00%aN <%aE>%x00"
           "%(trailers:key=Co-authored-by,key=Assisted-by,key=Generated-by,valueonly,separator=%x00)")
    res = {}
    for commit in check_output(git_cmd + ["log", fmt, branch] + list(since) + list(until)).split('\x02')[1:]:
        sha, auth, *coauths = commit.strip().split('\x00')
        if coauths := list(dict.fromkeys(filter(None, map(str.strip, coauths)))):
            res[sha] = (auth, coauths)
    if res:   # mailmap trailers
        coauths = sorted({i for _, cos in res.values() for i in cos})
        mailmap = dict(zip(coauths, check_output(git_cmd + ["check-mailmap", "--"] + coauths).strip().split('\n')))
        res = {sha: (auth, [mailmap.get(i, i) for i in cos]) for sha, (auth, cos) in res.items()}
    log.debug("co-authored:%d", len(res))
    return {sha: (auth, cos[:1] if strat == 'first' else [auth] + cos) for sha, (auth, cos) in res.items()}


def _author_revs(git_cmd, branch, filters):
    """Returns SHAs using `git log --format=%H <branch> <filters...>`"""
    if not filters:
        return []
    revs = check_output(git_cmd + ["log", "--format=%H", branch] + list(filters)).split()
    getattr(log, "debug" if revs else "warning")("ignore-author:%d revs", len(revs))
    return revs


def _get_auth_stats(gitdir, branch="HEAD", since=None, include_files=None, exclude_files=None, silent_progress=False,
                    ignore_whitespace=False, M=False, C=False, warn_binary=False, bytype=False, show=None,
                    prefix_gitdir=False, churn=None, ignore_revs=(), ignore_revs_file=None, ignore_authors=(),
                    until=None, jobs=None, auth='git'):
    """Returns dict: {"<author>": {"loc": int, "files": {}, "commits": int, "atimes": [int]}}"""
    until = ["--until", until] if until else []
    since = ["--since", since] if since else []
    show = show or SHOW_NAME
    log_binary = getattr(log, "warning" if warn_binary else "debug")
    git_cmd = ["git", "-C", gitdir]
    log.debug("base command:%s", git_cmd)
    file_list = check_output(git_cmd + ["ls-files", "--with-tree", branch]).strip().split('\n')
    text_file_list = check_output(git_cmd + ["grep", "-I", "--name-only", ".", branch]).strip()
    text_file_list = set(re.sub(f"^{re.escape(branch)}:", "", text_file_list, flags=re.M).split('\n'))
    if not hasattr(include_files, 'search'):
        file_list = [i for i in file_list if (not include_files or (i in include_files)) if i not in exclude_files]
    else:
        file_list = [i for i in file_list if include_files.search(i) if not (exclude_files and exclude_files.search(i))]
    for fname in file_list:
        if fname not in text_file_list:
            log_binary("binary:%s", fname.strip())
    file_list = [f for f in file_list if f in text_file_list] # preserve order
    log.log(logging.NOTSET, "files:%s", file_list)
    churn = churn or set()

    if churn & CHURN_SLOC:
        base_cmd = git_cmd + ["blame", "--line-porcelain"] + since + until
        for rev in chain(ignore_revs, _author_revs(git_cmd, branch, ignore_authors)):
            base_cmd.extend(["--ignore-rev", rev])
        if ignore_revs_file:
            base_cmd.extend(["--ignore-revs-file", ignore_revs_file])
    else:
        base_cmd = git_cmd + ["log", "--format=aN%aN aE%aE at%at H%H", "--numstat"] + since + until
    sha2auths = _get_coauthors(git_cmd, branch, auth, since, until) if auth != 'git' else {}

    if ignore_whitespace:
        base_cmd.append("-w")
    if M:
        base_cmd.append("-M")
    if C:
        base_cmd.extend(["-C", "-C"]) # twice to include file creation

    auth_stats = {}

    def stats_append(fname, auths, loc, tstamp):
        tstamp = int(tstamp)
        loc = loc / len(auths) if len(auths) > 1 else loc
        for auth in auths:
            stats = auth_stats.setdefault(str(auth), new_stats())
            stats["loc"] += loc
            stats["files"].add(fname)
            stats["atimes"].append(tstamp)

            if bytype:
                stats[f".{fext(fname) or '_None_ext'}"] += loc

    if churn & CHURN_SLOC:

        def blame_file(fname):
            """Blame one file. Returns `(fname, output_or_exception)` so that
            failures stay in input order and are reported by the caller."""
            try:
                return fname, check_output(base_cmd + [branch, fname], stderr=subprocess.STDOUT)
            except Exception as err:
                return fname, err

        # concurrent multi-file processing
        _mapper = get_mapper(max_workers=jobs, desc=gitdir if prefix_gitdir else "Processing", disable=silent_progress,
                             unit="file")

        for fname, blame_out in _mapper(blame_file, file_list):
            # `fname` is relative to `gitdir`, so only prefix the reported name
            display_fname = path.join(gitdir, fname) if prefix_gitdir else fname
            if isinstance(blame_out, Exception):
                log_binary(display_fname + ':' + str(blame_out))
                continue
            log.log(logging.NOTSET, blame_out)

            if since or until:
                # Strip boundary messages,
                # preventing user with nearest commit to boundary owning the LOC
                blame_out = RE_BLAME_BOUNDS.sub('', blame_out)

            for sha, loc, name, email, tstamp in RE_AUTHS_BLAME.findall(blame_out): # for each chunk
                auths = sha2auths[sha][1] if sha in sha2auths else [f'{name} <{email}>']
                stats_append(display_fname, auths, int(loc), tstamp)

    else:
        with tqdm(total=1, desc=gitdir if prefix_gitdir else "Processing", disable=silent_progress, unit="repo") as t:
            blame_out = check_output(base_cmd + [branch], stderr=subprocess.STDOUT)
            t.update()
        log.log(logging.NOTSET, blame_out)

        # Strip binary files
        for fname in dict.fromkeys(RE_STAT_BINARY.findall(blame_out)):
            log_binary("binary:%s", fname.strip())
        blame_out = RE_STAT_BINARY.sub('', blame_out)

        blame_out = RE_AUTHS_LOG.split(blame_out)
        blame_out = zip(*(blame_out[i::5] for i in range(1, 6)))
        for name, email, tstamp, sha, fnames in blame_out:
            auths = sha2auths[sha][1] if sha in sha2auths else [f'{name} <{email}>']
            fnames = fnames.split('\naN', 1)[0]
            for i in fnames.strip().split('\n'):
                try:
                    inss, dels, fname = i.split('\t')
                except ValueError:
                    log.warning(i)
                else:
                    if (fname := RE_RENAME.sub(r'\\2', fname)) in file_list:
                        loc = int(inss) if churn & CHURN_INS and inss else 0
                        loc += int(dels) if churn & CHURN_DEL and dels else 0
                        stats_append(fname, auths, loc, tstamp)

    # quickly count commits (even if no surviving loc)
    log.log(logging.NOTSET, "authors:%s", list(auth_stats.keys()))
    auth_commits = check_output(git_cmd + ["shortlog", "-s", "-e", branch] + since + until)
    log.debug(RE_NCOM_AUTH_EM.findall(auth_commits.strip()))
    auth2new = {}
    for (ncom, name, em) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
        auth2new[(auth := f'{name} <{em}>')] = em if show & SHOW_EMAIL else name
        auth_stats.setdefault(auth, new_stats())["commits"] += int(ncom)
    # transform shortlog according to --auth
    for auth, auths in sha2auths.values():
        auth_stats.setdefault(auth, new_stats())["commits"] -= 1
        for who in auths:
            auth_stats.setdefault(who, new_stats())["commits"] += 1 / len(auths)

    if not (show & SHOW_NAME and show & SHOW_EMAIL): # replace author with either email or name
        log.debug(auth2new)
        old, auth_stats = auth_stats, {}
        for auth, stats in old.items():
            if auth not in auth2new:                 # --since/--until (#122)
                auth2new[auth] = re.match('(.*) <(.*)>$', auth).group(2 if (show & SHOW_EMAIL) else 1) or auth
            merge_stats(auth_stats.setdefault(auth2new[auth], new_stats()), stats)

    return auth_stats


def run(args):
    """args  : Namespace (`argopt.DictAttrWrap` or from `argparse`)"""
    log.debug("parsing args")
    args.show = set(args.show.lower().split(','))
    if args.show_email:
        args.show = SHOW_EMAIL

    args.excl = args.excl or ""

    # strip `/` suffix
    gitdirs = [i.rstrip(os.sep) or os.sep for i in ([args.gitdir] if isinstance(args.gitdir, str) else args.gitdir)]
    # strip `.git`, remove duplicates
    gitdirs = list(dict.fromkeys(path.dirname(i) if path.basename(i) == '.git' else i for i in gitdirs))
    # recurse
    if args.recurse:
        for gitdir in [i for i in gitdirs if path.isdir(i)]:
            for root, dirs, fns in tqdm(os.walk(gitdir), desc="Recursing", unit="dir", disable=args.silent_progress,
                                        leave=False):
                if '.git' in fns + dirs:
                    if root not in gitdirs:
                        gitdirs.append(root)
                    if '.git' in dirs:
                        dirs.remove('.git')

    if args.no_regex:
        exclude_files = set(RE_CSPILT.split(args.excl))
        include_files = set() if args.incl == ".*" else set(RE_CSPILT.split(args.incl))
    else:
        exclude_files = re.compile(args.excl) if args.excl else None
        include_files = re.compile(args.incl)

    ignore_revs = list(filter(None, args.ignore_rev.split(','))) if args.ignore_rev else []
    # `git log` filters, OR-ed by `git`, so ',' is equivalent to '|' even in regex mode
    ignore_authors = [i.replace('\\,', ',') for i in RE_CSPILT.split(args.ignore_author)] if args.ignore_author else []
    if ignore_authors:
        ignore_authors = (["-F"] if args.no_regex else []) + ["--author=" + i for i in ignore_authors]

    cost = set(args.cost.lower().split(',')) if args.cost else set()
    churn = set(args.loc.lower().split(',')) if args.loc else set()
    if not churn:
        churn = CHURN_INS | CHURN_DEL if cost & COST_HOURS else CHURN_INS if cost & COST_MONTHS else CHURN_SLOC

    if churn & (CHURN_INS | CHURN_DEL) and args.excl:
        log.warning("--loc=ins,del includes historical files"
                    " which may need to be added to --excl")
    if not churn & CHURN_SLOC and (ignore_revs or args.ignore_revs_file or ignore_authors):
        log.warning("--ignore-* requires --loc=surviving")

    auth_stats = {}
    statter = partial(_get_auth_stats, branch=args.branch, since=args.since, until=args.until,
                      include_files=include_files, exclude_files=exclude_files, silent_progress=args.silent_progress,
                      ignore_whitespace=args.ignore_whitespace, M=args.M, C=args.C, warn_binary=args.warn_binary,
                      bytype=args.bytype, show=args.show, prefix_gitdir=len(gitdirs) > 1, churn=churn,
                      ignore_revs=ignore_revs, ignore_revs_file=args.ignore_revs_file, ignore_authors=ignore_authors,
                      jobs=args.jobs or None, auth=args.auth)

    # concurrent multi-repo processing
    _mapper = get_mapper(max_workers=1 if len(gitdirs) <= 1 else None, desc="Repos", unit="repo", miniters=1,
                         disable=args.silent_progress or len(gitdirs) <= 1)
    for auth, stats in chain.from_iterable(res.items() for res in _mapper(statter, gitdirs)):
        if auth in auth_stats:
            merge_stats(auth_stats[auth], stats)
        else:
            auth_stats[auth] = stats

    stats_tot = {
        k: sum(int_float_len(stats.get(k, 0)) for stats in auth_stats.values())
        for k in dict.fromkeys(chain.from_iterable(auth_stats.values()))}
    log.debug(stats_tot)
    # NOTE: future idea: show stats per file extension (or other grouping) in addition to per-author
    print_unicode(tabulate(auth_stats, stats_tot, args.sort, args.bytype, args.format, cost, args.enum, args.min))


def get_main_parser():
    import shtab
    from argopt import argopt
    parser = argopt(__doc__ + '\n' + __copyright__, version=__version__)

    def csv_permute(a, b):
        return a | b | {k for i in a for j in b for k in (f"{i},{j}", f"{j},{i}")}

    for o in parser._get_optional_actions():
        if o.dest == 'branch':
            try:
                o.complete = shtab.cmd("git branch")
            except AttributeError:
                log.debug("shtab>1.9.3 required")
        elif o.dest == 'sort':
            o.choices = 'loc', 'commits', 'files', 'hours', 'months'
            o.metavar = None
            o.help = "[default: loc]."
        elif o.dest == 'loc':
            o.choices = CHURN_SLOC | csv_permute(CHURN_INS, CHURN_DEL)
        elif o.dest == 'auth':
            o.choices = 'git', 'first', 'share'
        elif o.dest == 'cost':
            o.choices = csv_permute(COST_HOURS, COST_MONTHS)
        elif o.dest == 'show':
            o.choices = csv_permute(SHOW_NAME, SHOW_EMAIL)
        elif o.dest == 'ignore_revs_file':
            try:
                o.complete = shtab.glob("*git*rev*")
            except AttributeError:
                log.debug("shtab>1.9.3 required")
        elif o.dest == 'format':
            o.choices = FORMATS
            o.metavar = None
            o.help = "[default: md]."
        elif o.dest == 'log':
            o.choices = 'FATAL', 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
            o.metavar = None
            o.help = "[default: INFO]."
    shtab.add_argument_to(parser)
    return parser


def main(args=None):
    """args  : list [default: sys.argv[1:]]"""
    parser = get_main_parser()
    args = parser.parse_args(args=args)
    logging.basicConfig(level=getattr(logging, args.log, logging.INFO), stream=TqdmStream,
                        format="%(levelname)s:gitfame.%(funcName)s:%(lineno)d:%(message)s")
    log.debug(args)
    run(args)


if __name__ == "__main__": # pragma: no cover
    main()
