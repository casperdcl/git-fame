#!/usr/bin/env python
r"""Usage:
  gitfame [--help | options] [<gitdir>...]

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
                   person-hours (based on commit times).
                   Methods: month(s)|cocomo|hour(s)|commit(s).
                   May be multiple comma-separated values.
                   Alters `--loc` default to imply 'ins' (COCOMO) or
                   'ins,del' (hours).
  -R, --recurse  Recursively find repositories & submodules within <gitdir>.
  -n, --no-regex  Assume <f> are comma-separated exact matches
                  rather than regular expressions [default: False].
                  NB: if regex is enabled ',' is equivalent to '|'.
  -s, --silent-progress    Suppress `tqdm` [default: False].
  --warn-binary  Don't silently skip files which appear to be binary data
                 [default: False].
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
  --ignore-rev=<rev>       Ignore changes made by the given revision
                           (requires `--loc=surviving`).
  --ignore-revs-file=<f>   Ignore revisions listed in the given file
                           (requires `--loc=surviving`).
  --format=<format>        Table format
      svg|[default: pipe]|md|markdown|yaml|yml|json|csv|tsv|tabulate.
      May require `git-fame[<format>]`, e.g. `pip install git-fame[yaml]`.
      Any `tabulate.tabulate_formats` is also accepted.
  --manpath=<path>         Directory in which to install git-fame man pages.
  --log=<lvl>    FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.
"""
import logging
import os
import re
import subprocess
from collections import defaultdict
from functools import partial
from os import path

from ._utils import (TERM_WIDTH, Str, TqdmStream, check_output, fext, int_cast_or_len, merge_stats,
                     print_unicode, tqdm)

# version detector. Precedence: installed dist, git, 'UNKNOWN'
try:
    from ._dist_ver import __version__
except ImportError:
    try:
        from setuptools_scm import get_version
        __version__ = get_version(root='..', relative_to=__file__)
    except (ImportError, LookupError):
        __version__ = "UNKNOWN"
__author__ = "Casper da Costa-Luis <casper.dcl@physics.org>"
__date__ = "2016-2025"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__ # weird foreign language
log = logging.getLogger(__name__)

# processing `blame --line-porcelain`
RE_AUTHS_BLAME = re.compile(
    r'^\w+ \d+ \d+ (\d+)\nauthor (.+?)\nauthor-mail <(.*?)>$.*?\ncommitter-time (\d+)',
    flags=re.M | re.DOTALL)
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*?)\s+<(.*)>\s*$', flags=re.M)
RE_BLAME_BOUNDS = re.compile(
    r'^\w+\s+\d+\s+\d+(\s+\d+)?\s*$[^\t]*?^boundary\s*$[^\t]*?^\t.*?$\r?\n',
    flags=re.M | re.DOTALL)
# processing `log --format="aN%aN aE%aE ct%ct" --numstat`
RE_AUTHS_LOG = re.compile(r"^aN(.+?) aE(.*?) ct(\d+)\n\n", flags=re.M)
RE_STAT_BINARY = re.compile(r"^\s*?-\s*-.*?\n", flags=re.M)
RE_RENAME = re.compile(r"\{.+? => (.+?)\}")
# finds all non-escaped commas
# NB: does not support escaping of escaped character
RE_CSPILT = re.compile(r'(?<!\\),')
# options
COST_MONTHS = {'cocomo', 'month', 'months'}
COST_HOURS = {'commit', 'commits', 'hour', 'hours'}
CHURN_SLOC = {'surv', 'survive', 'surviving'}
CHURN_INS = {'ins', 'insert', 'insertion', 'insertions', 'add', 'addition', 'additions', '+'}
CHURN_DEL = {'del', 'deletion', 'deletions', 'delete', '-'}
SHOW_NAME = {'name', 'n'}
SHOW_EMAIL = {'email', 'e'}


def hours(dates, maxCommitDiffInSec=120 * 60, firstCommitAdditionInMinutes=120):
    """
    Convert list of commit times (in seconds) to an estimate of hours spent.

    https://github.com/kimmobrunfeldt/git-hours/blob/\
8aaeee237cb9d9028e7a2592a25ad8468b1f45e4/index.js#L114-L143
    """
    dates = sorted(dates)
    diffInSec = [i - j for (i, j) in zip(dates[1:], dates[:-1])]
    res = sum(i for i in diffInSec if i < maxCommitDiffInSec)
    return (res/60.0 + firstCommitAdditionInMinutes) / 60.0


def tabulate(auth_stats, stats_tot, sort='loc', bytype=False, backend='md', cost=None,
             row_nums=False, min_sort_val=0, width=TERM_WIDTH):
    """
    backends  : [default: md]|yaml|json|csv|tsv|tabulate|
      `in tabulate.tabulate_formats`
    """
    COL_NAMES = ['Author', 'loc', 'coms', 'fils', ' distribution']
    # get ready
    tab = [[
        auth, s['loc'],
        s.get('commits', 0),
        len(s.get('files', [])), '/'.join(
            map('{:4.1f}'.format,
                (100 * s['loc'] / max(1, stats_tot['loc']),
                 100 * s.get('commits', 0) / max(1, stats_tot['commits']),
                 100 * len(s.get('files', [])) / max(1, stats_tot['files'])))).replace(
                     '/100.0/', '/ 100/')] for (auth, s) in auth_stats.items()]
    if cost:
        stats_tot = dict(stats_tot)
        if cost & COST_MONTHS:
            COL_NAMES.insert(1, 'mths')
            tab = [i[:1] + [3.2 * (i[1] / 1e3)**1.05] + i[1:] for i in tab]
            stats_tot.setdefault('months', '%.1f' % sum(i[1] for i in tab))
        if cost & COST_HOURS:
            COL_NAMES.insert(1, 'hrs')
            tab = [i[:1] + [hours(auth_stats[i[0]]['ctimes'])] + i[1:] for i in tab]

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

    totals = 'Total ' + '\nTotal '.join("%s: %s" % i for i in sorted(stats_tot.items())) + '\n'

    if (backend := backend.lower()) in ("tabulate", "md", "markdown"):
        backend = "pipe"
    svg = backend == 'svg'
    if svg:
        backend = 'rounded_outline'

    if backend in ('yaml', 'yml', 'json', 'csv', 'tsv'):
        tab = [i[:-1] + [float(pc.strip()) for pc in i[-1].split('/')] for i in tab]
        tab = {
            "total": stats_tot, "data": tab,
            "columns": COL_NAMES[:-1] + ['%' + i for i in COL_NAMES[-4:-1]]}
        if backend in ('yaml', 'yml'):
            log.debug("backend:yaml")
            from yaml import safe_dump as tabber
            return tabber(tab).rstrip()
        elif backend == 'json':
            log.debug("backend:json")
            from json import dumps as tabber
            return tabber(tab, ensure_ascii=False)
        elif backend in ('csv', 'tsv'):
            log.debug("backend:csv")
            from csv import writer as tabber
            from io import StringIO

            res = StringIO()
            t = tabber(res, delimiter=',' if backend == 'csv' else '\t')
            t.writerow(tab['columns'])
            t.writerows(tab['data'])
            t.writerow('')
            t.writerow(list(tab['total'].keys()))
            t.writerow(list(tab['total'].values()))
            return res.getvalue().rstrip()
        else:      # pragma: nocover
            raise RuntimeError("Should be unreachable")
    else:
        import tabulate as tabber

        if backend not in tabber.tabulate_formats:
            raise ValueError(f"Unknown backend:{backend}")
        log.debug("backend:tabulate:%s", backend)
        COL_LENS = [max(len(Str(i[j])) for i in [COL_NAMES] + tab) for j in range(len(COL_NAMES))]
        COL_LENS[0] = min(width - sum(COL_LENS[1:]) - len(COL_LENS) * 3 - 4, COL_LENS[0])
        tab = [[i[0][:COL_LENS[0]]] + i[1:] for i in tab]
        table = tabber.tabulate(tab, COL_NAMES, tablefmt=backend, floatfmt='.0f')
        if svg:
            rows = table.split('\n')
            return ('<svg xmlns="http://www.w3.org/2000/svg"'
                    f' width="{len(rows[0]) / 2 + 1}em" height="{len(rows)}em">'
                    '<rect x="0" y="0" width="100%" height="100%"'
                    ' fill="white" fill-opacity="0.5" rx="5"/>'
                    '<text x="0" y="-0.5em" font-size="15"'
                    ' font-family="monospace" style="white-space: pre">' +
                    ''.join(f'<tspan x="0" dy="1em">{row}</tspan>'
                            for row in rows) + '</text></svg>')
        return totals + table

        # from ._utils import tighten
        # return totals + tighten(tabber(...), max_width=TERM_WIDTH)


def _get_auth_stats(gitdir, branch="HEAD", since=None, include_files=None, exclude_files=None,
                    silent_progress=False, ignore_whitespace=False, M=False, C=False,
                    warn_binary=False, bytype=False, show=None, prefix_gitdir=False, churn=None,
                    ignore_rev="", ignore_revs_file=None, until=None):
    """Returns dict: {"<author>": {"loc": int, "files": {}, "commits": int, "ctimes": [int]}}"""
    until = ["--until", until] if until else []
    since = ["--since", since] if since else []
    show = show or SHOW_NAME
    git_cmd = ["git", "-C", gitdir]
    log.debug("base command:%s", git_cmd)
    file_list = check_output(git_cmd + ["ls-files", "--with-tree", branch]).strip().split('\n')
    text_file_list = check_output(git_cmd + ["grep", "-I", "--name-only", ".", branch]).strip()
    text_file_list = set(
        re.sub(f"^{re.escape(branch)}:", "", text_file_list, flags=re.M).split('\n'))
    if not hasattr(include_files, 'search'):
        file_list = [
            i for i in file_list if (not include_files or (i in include_files))
            if i not in exclude_files]
    else:
        file_list = [
            i for i in file_list if include_files.search(i)
            if not (exclude_files and exclude_files.search(i))]
    for fname in set(file_list) - text_file_list:
        getattr(log, "warn" if warn_binary else "debug")("binary:%s", fname.strip())
    file_list = [f for f in file_list if f in text_file_list] # preserve order
    log.log(logging.NOTSET, "files:%s", file_list)
    churn = churn or set()

    if churn & CHURN_SLOC:
        base_cmd = git_cmd + ["blame", "--line-porcelain"] + since + until
        if ignore_rev:
            base_cmd.extend(["--ignore-rev", ignore_rev])
        if ignore_revs_file:
            base_cmd.extend(["--ignore-revs-file", ignore_revs_file])
    else:
        base_cmd = git_cmd + ["log", "--format=aN%aN aE%aE ct%ct", "--numstat"] + since + until

    if ignore_whitespace:
        base_cmd.append("-w")
    if M:
        base_cmd.append("-M")
    if C:
        base_cmd.extend(["-C", "-C"]) # twice to include file creation

    auth_stats = {}

    def stats_append(fname, auth, loc, tstamp):
        tstamp = int(tstamp)
        if (auth := str(auth)) not in auth_stats:
            auth_stats[auth] = defaultdict(int, files=set(), ctimes=[])
        auth_stats[auth]["loc"] += loc
        auth_stats[auth]["files"].add(fname)
        auth_stats[auth]["ctimes"].append(tstamp)

        if bytype:
            fext_key = f".{fext(fname) or '_None_ext'}"
            auth_stats[auth][fext_key] += loc

    if churn & CHURN_SLOC:
        for fname in tqdm(file_list, desc=gitdir if prefix_gitdir else "Processing",
                          disable=silent_progress, unit="file"):
            if prefix_gitdir:
                fname = path.join(gitdir, fname)
            try:
                blame_out = check_output(base_cmd + [branch, fname], stderr=subprocess.STDOUT)
            except Exception as err:
                getattr(log, "warn" if warn_binary else "debug")(fname + ':' + str(err))
                continue
            log.log(logging.NOTSET, blame_out)

            if since:
                # Strip boundary messages,
                # preventing user with nearest commit to boundary owning the LOC
                blame_out = RE_BLAME_BOUNDS.sub('', blame_out)

            if until:
                # Strip boundary messages,
                # preventing user with nearest commit to boundary owning the LOC
                blame_out = RE_BLAME_BOUNDS.sub('', blame_out)

            for loc, name, email, tstamp in RE_AUTHS_BLAME.findall(blame_out): # for each chunk
                loc = int(loc)
                auth = f'{name} <{email}>'
                stats_append(fname, auth, loc, tstamp)

    else:
        with tqdm(total=1, desc=gitdir if prefix_gitdir else "Processing", disable=silent_progress,
                  unit="repo") as t:
            blame_out = check_output(base_cmd + [branch], stderr=subprocess.STDOUT)
            t.update()
        log.log(logging.NOTSET, blame_out)

        # Strip binary files
        for fname in set(RE_STAT_BINARY.findall(blame_out)):
            getattr(log, "warn" if warn_binary else "debug")("binary:%s", fname.strip())
        blame_out = RE_STAT_BINARY.sub('', blame_out)

        blame_out = RE_AUTHS_LOG.split(blame_out)
        blame_out = zip(blame_out[1::4], blame_out[2::4], blame_out[3::4], blame_out[4::4])
        for name, email, tstamp, fnames in blame_out:
            auth = f'{name} <{email}>'
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
                        stats_append(fname, auth, loc, tstamp)

    # quickly count commits (even if no surviving loc)
    log.log(logging.NOTSET, "authors:%s", list(auth_stats.keys()))
    auth_commits = check_output(git_cmd + ["shortlog", "-s", "-e", branch] + since + until)
    log.debug(RE_NCOM_AUTH_EM.findall(auth_commits.strip()))
    auth2em = {}
    auth2name = {}
    for (ncom, name, em) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
        auth = f'{name} <{em}>'
        auth2em[auth] = em
        auth2name[auth] = name
        if auth not in auth_stats:
            auth_stats[auth] = defaultdict(int, files=set(), ctimes=[])
        auth_stats[auth]["commits"] += int(ncom)
    if not (show & SHOW_NAME and show & SHOW_EMAIL): # replace author with either email or name
        auth2new = auth2em if (show & SHOW_EMAIL) else auth2name
        log.debug(auth2new)
        old = auth_stats
        auth_stats = {}

        for auth, stats in old.items():
            i = auth_stats.setdefault(auth2new[auth], defaultdict(int, files=set(), ctimes=[]))
            i["files"].update(stats["files"])
            for k, v in stats.items():
                if k != 'files':
                    i[k] += v
        del old

    return auth_stats


def run(args):
    """args  : Namespace (`argopt.DictAttrWrap` or from `argparse`)"""
    log.debug("parsing args")

    if args.sort not in "loc commits files hours months".split():
        log.warning("--sort argument (%s) unrecognised\n%s", args.sort, __doc__)
        raise KeyError(args.sort)

    args.show = set(args.show.lower().split(','))
    if args.show_email:
        args.show = SHOW_EMAIL

    if not args.excl:
        args.excl = ""

    if isinstance(args.gitdir, str):
        args.gitdir = [args.gitdir]
    # strip `/`, `.git`
    gitdirs = [i.rstrip(os.sep) for i in args.gitdir]
    gitdirs = [
        path.join(*path.split(i)[:-1]) if path.split(i)[-1] == '.git' else i for i in args.gitdir]
    # remove duplicates
    for i, d in reversed(list(enumerate(gitdirs))):
        if d in gitdirs[:i]:
            gitdirs.pop(i)
    # recurse
    if args.recurse:
        nDirs = len(gitdirs)
        i = 0
        while i < nDirs:
            if path.isdir(gitdirs[i]):
                for root, dirs, fns in tqdm(os.walk(gitdirs[i]), desc="Recursing", unit="dir",
                                            disable=args.silent_progress, leave=False):
                    if '.git' in fns + dirs:
                        if root not in gitdirs:
                            gitdirs.append(root)
                        if '.git' in dirs:
                            dirs.remove('.git')
            i += 1

    exclude_files = None
    include_files = None
    if args.no_regex:
        exclude_files = set(RE_CSPILT.split(args.excl))
        include_files = set()
        if args.incl == ".*":
            args.incl = ""
        else:
            include_files.update(RE_CSPILT.split(args.incl))
    else:
        # cannot use findall in case of grouping:
        # for i in include_files:
        # for i in [include_files]:
        #   for j in range(1, len(i)):
        #     if i[j] == '(' and i[j - 1] != '\\':
        #       raise ValueError('Parenthesis must be escaped'
        #                        ' in include-files:\n\t' + i)
        exclude_files = re.compile(args.excl) if args.excl else None
        include_files = re.compile(args.incl)
        # include_files = re.compile(args.incl, flags=re.M)

    cost = set(args.cost.lower().split(',')) if args.cost else set()
    churn = set(args.loc.lower().split(',')) if args.loc else set()
    if not churn:
        if cost & COST_HOURS:
            churn = CHURN_INS | CHURN_DEL
        elif cost & COST_MONTHS:
            churn = CHURN_INS
        else:
            churn = CHURN_SLOC

    if churn & (CHURN_INS | CHURN_DEL) and args.excl:
        log.warning("--loc=ins,del includes historical files"
                    " which may need to be added to --excl")

    auth_stats = {}
    statter = partial(_get_auth_stats, branch=args.branch, since=args.since, until=args.until,
                      include_files=include_files, exclude_files=exclude_files,
                      silent_progress=args.silent_progress,
                      ignore_whitespace=args.ignore_whitespace, M=args.M, C=args.C,
                      warn_binary=args.warn_binary, bytype=args.bytype, show=args.show,
                      prefix_gitdir=len(gitdirs) > 1, churn=churn, ignore_rev=args.ignore_rev,
                      ignore_revs_file=args.ignore_revs_file)

    # concurrent multi-repo processing
    if len(gitdirs) > 1:
        try:
            from concurrent.futures import ThreadPoolExecutor  # NOQA, yapf: disable

            from tqdm.contrib.concurrent import thread_map
            mapper = partial(thread_map, desc="Repos", unit="repo", miniters=1,
                             disable=args.silent_progress or len(gitdirs) <= 1)
        except ImportError:
            mapper = map
    else:
        mapper = map

    for res in mapper(statter, gitdirs):
        for auth, stats in res.items():
            if auth in auth_stats:
                merge_stats(auth_stats[auth], stats)
            else:
                auth_stats[auth] = stats

    stats_tot = {k: 0 for stats in auth_stats.values() for k in stats}
    log.debug(stats_tot)
    for k in stats_tot:
        stats_tot[k] = sum(int_cast_or_len(stats.get(k, 0)) for stats in auth_stats.values())
    log.debug(stats_tot)

    # TODO:
    # extns = set()
    # if args.bytype:
    #   for stats in auth_stats.values():
    #     extns.update([fext(i) for i in stats["files"]])
    # log.debug(extns)

    print_unicode(
        tabulate(auth_stats, stats_tot, args.sort, args.bytype, args.format, cost, args.enum,
                 args.min))


def get_main_parser():
    from argopt import argopt
    return argopt(__doc__ + '\n' + __copyright__, version=__version__)


def main(args=None):
    """args  : list [default: sys.argv[1:]]"""
    parser = get_main_parser()
    args = parser.parse_args(args=args)
    logging.basicConfig(level=getattr(logging, args.log, logging.INFO), stream=TqdmStream,
                        format="%(levelname)s:gitfame.%(funcName)s:%(lineno)d:%(message)s")

    log.debug(args)
    if args.manpath is not None:
        import sys
        from pathlib import Path

        try:  # py<3.9
            import importlib_resources as resources
        except ImportError:
            from importlib import resources
        fi = resources.files('gitfame') / 'git-fame.1'
        fo = Path(args.manpath) / 'git-fame.1'
        fo.write_bytes(fi.read_bytes())
        log.info("written:%s", fo)
        sys.exit(0)

    run(args)


if __name__ == "__main__": # pragma: no cover
    main()
