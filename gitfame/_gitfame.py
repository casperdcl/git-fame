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
  --loc=<type>   surv(iving)|ins(ertions)|del(etions)
                 What `loc` represents. Use 'ins,del' to count both.
                 defaults to 'surviving' unless `--cost` is specified.
  --excl=<f>     Excluded files (default: None).
                 In no-regex mode, may be a comma-separated list.
                 Escape (\,) for a literal comma (may require \\, in shell).
  --incl=<f>     Included files [default: .*]. See `--excl` for format.
  --since=<date>  Date from which to check. Can be absoulte (eg: 1970-01-31)
                  or relative to now (eg: 3.weeks).
  --until=<date>  Date to which to check. Can be absoulte (eg: 1970-01-31)
                  or relative to now (eg: 3.weeks).
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
  -e, --show-email  Show author email instead of name [default: False].
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
      [default: pipe]|md|markdown|yaml|yml|json|csv|tsv|tabulate.
      May require `git-fame[<format>]`, e.g. `pip install git-fame[yaml]`.
      Any `tabulate.tabulate_formats` is also accepted.
  --manpath=<path>         Directory in which to install git-fame man pages.
  --log=<lvl>    FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.
  --processes=<num>         int, Number of processes to use for parallelization [default: 1]
  --author-mapping-file-path=<path>   Path to file containing dictionary mapping author name
                                      to normalized author name
  --author-email-mapping-file-path=<path>   Path to file containing dictionary mapping author
                                            email address to normalized author name
"""
from __future__ import division, print_function

import ast
import codecs
import logging
import multiprocessing
import os
import queue
import re
import subprocess
from collections import defaultdict
# from __future__ import absolute_import
from functools import partial
from os import path
from pathlib import Path
from typing import Dict, Optional

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
__date__ = "2016-2023"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__ # weird foreign language
log = logging.getLogger(__name__)

# processing `blame --line-porcelain`
RE_AUTHS_BLAME = re.compile(r'^\w+ \d+ \d+ (\d+)\nauthor (.+?)$.*?\ncommitter-time (\d+)',
                            flags=re.M | re.DOTALL)
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*?)\s+<(.*)>\s*$', flags=re.M)
RE_BLAME_BOUNDS = re.compile(
    r'^\w+\s+\d+\s+\d+(\s+\d+)?\s*$[^\t]*?^boundary\s*$[^\t]*?^\t.*?$\r?\n',
    flags=re.M | re.DOTALL)
# processing `log --format="aN%aN ct%ct" --numstat`
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


def hours(dates, maxCommitDiffInSec=120 * 60, firstCommitAdditionInMinutes=120):
    """
    Convert list of commit times (in seconds) to an estimate of hours spent.

    https://github.com/kimmobrunfeldt/git-hours/blob/\
8aaeee237cb9d9028e7a2592a25ad8468b1f45e4/index.js#L114-L143
    """
    dates = sorted(dates)
    diffInSec = [i - j for (i, j) in zip(dates[1:], dates[:-1])]
    res = sum(filter(lambda i: i < maxCommitDiffInSec, diffInSec))
    return (res/60.0 + firstCommitAdditionInMinutes) / 60.0


def tabulate(auth_stats, stats_tot, sort='loc', bytype=False, backend='md', cost=None,
             row_nums=False):
    """
    backends  : [default: md]|yaml|json|csv|tsv|tabulate|
      `in tabulate.tabulate_formats`
    """
    COL_NAMES = ['Author', 'loc', 'coms', 'fils', ' distribution']
    it_as = getattr(auth_stats, 'iteritems', auth_stats.items)
    # get ready
    tab = [[
        auth, s['loc'],
        s.get('commits', 0),
        len(s.get('files', [])), '/'.join(
            map('{0:4.1f}'.format,
                (100 * s['loc'] / max(1, stats_tot['loc']),
                 100 * s.get('commits', 0) / max(1, stats_tot['commits']),
                 100 * len(s.get('files', [])) / max(1, stats_tot['files'])))).replace(
                     '/100.0/', '/ 100/')] for (auth, s) in it_as()]
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

    for i, j in [("commits", "coms"), ("files", "fils"), ("hours", "hrs"), ("months", "mths")]:
        sort = sort.replace(i, j)
    tab.sort(key=lambda i: i[COL_NAMES.index(sort)], reverse=True)
    if row_nums:
        tab = [[str(i)] + j for i, j in enumerate(tab, 1)]
        COL_NAMES.insert(0, '#')

    totals = 'Total ' + '\nTotal '.join("%s: %s" % i for i in sorted(stats_tot.items())) + '\n'

    backend = backend.lower()
    if backend in ("tabulate", "md", "markdown"):
        backend = "pipe"

    if backend in ['yaml', 'yml', 'json', 'csv', 'tsv']:
        tab = [i[:-1] + [float(pc.strip()) for pc in i[-1].split('/')] for i in tab]
        tab = {
            "total": stats_tot, "data": tab,
            "columns": COL_NAMES[:-1] + ['%' + i for i in COL_NAMES[-4:-1]]}
        if backend in ['yaml', 'yml']:
            log.debug("backend:yaml")
            from yaml import safe_dump as tabber
            return tabber(tab).rstrip()
        elif backend == 'json':
            log.debug("backend:json")
            from json import dumps as tabber
            return tabber(tab, ensure_ascii=False)
        elif backend in ['csv', 'tsv']:
            log.debug("backend:csv")
            from csv import writer as tabber

            from ._utils import StringIO
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
        COL_LENS[0] = min(TERM_WIDTH - sum(COL_LENS[1:]) - len(COL_LENS) * 3 - 4, COL_LENS[0])
        tab = [[i[0][:COL_LENS[0]]] + i[1:] for i in tab]
        return totals + tabber.tabulate(tab, COL_NAMES, tablefmt=backend, floatfmt='.0f')

        # from ._utils import tighten
        # return totals + tighten(tabber(...), max_width=TERM_WIDTH)


_RE_BLAME_START_LINE = re.compile(r'^(?P<commit_hash>[a-f0-9]+) (?P<original_file_line>\d+) '
                                  r'(?P<final_file_line>\d+) ?(?P<lines_of_code>\d+)?$')


class _CommitInfo:
    def __init__(self):
        self.file_locs = defaultdict(int) # {file_name: loc}
        self.info = {}


def _get_blame_out(base_cmd: list[str], branch: str, fname: str, since,
                   until) -> Dict[str, _CommitInfo]:
    blame_out = check_output(base_cmd + [branch, fname], stderr=subprocess.STDOUT)

    # Coalesces info by commit
    commit_infos = defaultdict(_CommitInfo)
    commit_info = loc = None

    for line in blame_out.splitlines():
        if match := _RE_BLAME_START_LINE.match(line):
            commit = match['commit_hash']
            loc = int(match['lines_of_code'])
            commit_info = commit_infos[commit]
        elif line == 'boundary':
            continue # TODO: is this ok?
        else:
            key, value = line.split(' ', 1)
            if key in ('previous', 'summary'):
                continue

            if key == 'filename':
                commit_info.file_locs[value] += loc
                continue

            assert not line.startswith('\t')
            if key == 'filename':
                commit_info.file_locs[value] += loc

            assert key not in commit_info.info
            commit_info.info[key] = value

    # TODO
    assert not since and not until

    # if since:
    #     # Strip boundary messages,
    #     # preventing user with nearest commit to boundary owning the LOC
    #     blame_out = RE_BLAME_BOUNDS.sub('', blame_out)
    #
    # if until:
    #     # Strip boundary messages,
    #     # preventing user with nearest commit to boundary owning the LOC
    #     blame_out = RE_BLAME_BOUNDS.sub('', blame_out)

    for cinfo in commit_infos.values():
        cinfo.file_locs = dict(cinfo.file_locs)

    return dict(commit_infos)


# TODO: probably should be swapped to mailmap
def _get_user_canonicalization_function(author_mapping_file_path: str = None,
                                        author_email_mapping_file_path: str = None):
    user_mappings = {}
    if author_mapping_file_path:
        with Path(author_mapping_file_path).expanduser().open('rt') as f:
            user_mappings = ast.literal_eval(f.read())

    email_mappings = {}
    if author_email_mapping_file_path:
        with Path(author_email_mapping_file_path).expanduser().open('rt') as f:
            email_mappings = ast.literal_eval(f.read())

    def canonicalize(author: str, author_email: str):
        author = user_mappings.get(author, author)
        author = email_mappings.get(author_email, author)
        return author

    return canonicalize


_RE_EOL_LINE = re.compile(
    r'^(?P<eol_index>[^ \t]+)+\s+(?P<eol_worktree>[^ \t]+)\s+(?P<attr>[^ \t]+)\s+(?P<fpath>.*)$')


def detect_bom(path: str, default=None):
    with open(path, 'rb') as f:
        raw = f.read(4) # will read less if the file is smaller

    # BOM_UTF32_LE's start is equal to BOM_UTF16_LE so need to try the former first
    for enc, boms in (('utf-8-sig', (codecs.BOM_UTF8,)), ('utf-32', (codecs.BOM_UTF32_LE,
                                                                     codecs.BOM_UTF32_BE)),
                      ('utf-16', (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))):
        if any(raw.startswith(bom) for bom in boms):
            return enc

    return default


GIT_BLAME_FORMAT = "ct%ct H%H aE%aE aN%aN"
RE_AUTHS_LOG_COMMIT = re.compile(
    r"^ct(?P<timestamp>\d*) H(?P<commit>[a-f0-9]*) aE(?P<auth_email>[^ ]*) aN(?P<author>.+?)$")
RE_AUTHS_LOG_FILE = re.compile(r"^(?P<inserts>\d+)\s+(?P<deletes>\d+)\s+(?P<fname>.+?)$")


def _get_auth_stats(
    gitdir: str,
    branch: str = "HEAD",
    since=None,
    include_files=None,
    exclude_files=None,
    silent_progress=False,
    ignore_whitespace=False,
    M: bool = False,
    C: bool = False,
    warn_binary: bool = False,
    bytype: bool = False,
    show_email: bool = False,
    prefix_gitdir: bool = False,
    churn=None,
    ignore_rev="",
    ignore_revs_file=None,
    until=None,
    processes: int = 1,
    author_mapping_file_path: str = None,
    author_email_mapping_file_path: str = None,
):
    """Returns dict: {"<author>": {"loc": int, "files": {}, "commits": int, "ctimes": [int]}}"""
    until = ["--until", until] if until else []
    since = ["--since", since] if since else []
    git_cmd = ["git", "-C", gitdir]
    log.debug("base command:%s", git_cmd)

    file_list = check_output(git_cmd +
                             ["ls-files", "--eol", "--with-tree", branch]).strip().splitlines()
    binary_file_list = []
    text_file_list = []
    for f in file_list:
        m = _RE_EOL_LINE.match(f)
        fpath = m['fpath']

        if not hasattr(include_files, 'search'):
            if (include_files and fpath not in include_files) or fpath in exclude_files:
                continue
        elif (not include_files.search(fpath)) or (exclude_files and exclude_files.search(fpath)):
            continue

        if m['eol_worktree'] == 'w/-text':
            binary_file_list.append(fpath)
        else:
            text_file_list.append(fpath)

    # we need to inspect if the binary_files are unicode
    for f in list(binary_file_list):
        if detect_bom(path.join(gitdir, f)):
            binary_file_list.remove(f)
            text_file_list.append(f)

    for fname in binary_file_list:
        getattr(log, "warn" if warn_binary else "debug")("binary:%s", fname.strip())

    file_list = text_file_list # preserve order
    log.log(logging.NOTSET, "files:%s", file_list)
    churn = churn or set()

    if churn & CHURN_SLOC:
        base_cmd = git_cmd + ["blame", "--line-porcelain", "--incremental"] + since + until
        if ignore_rev:
            base_cmd.extend(["--ignore-rev", ignore_rev])
        if ignore_revs_file:
            base_cmd.extend(["--ignore-revs-file", ignore_revs_file])
    else:
        base_cmd = git_cmd + ["log", f"--format={GIT_BLAME_FORMAT}", "--numstat"] + since + until

    if ignore_whitespace:
        base_cmd.append("-w")
    if M:
        base_cmd.append("-M")
    if C:
        base_cmd.extend(["-C", "-C"]) # twice to include file creation

    auth_stats = defaultdict(lambda: {'loc': 0, 'files': set(), 'ctimes': [], 'commits': 0})
    auth2em = defaultdict(set)

    author_canonicalizer = _get_user_canonicalization_function(author_mapping_file_path,
                                                               author_email_mapping_file_path)

    def stats_append(fname: str, auth: str, loc: int, tstamp: str, author_email: str):
        auth = author_canonicalizer(auth, author_email)
        tstamp = int(tstamp)

        auth2em[auth].add(author_email)

        i = auth_stats[auth]
        i["loc"] += loc
        i["files"].add(fname)
        i["ctimes"].append(tstamp)
        # NOTE: we could add all the commits here, that would equate to how many commits
        #   the author has that contain code still visible in the working branch

        if bytype:
            fext_key = f".{fext(fname) or '_None_ext'}"
            try:
                i[fext_key] += loc
            except KeyError:
                i[fext_key] = loc

    if churn & CHURN_SLOC:
        completed = queue.Queue()

        def process_blame_out(commit_infos: Dict[str, _CommitInfo]):
            for cinfo in commit_infos.values():
                for fname, loc in cinfo.file_locs.items():
                    stats_append(fname, cinfo.info['author'], loc, cinfo.info['committer-time'],
                                 cinfo.info['author-mail'])

            completed.put(None)

        def process_blame_out_error(fname, err):
            getattr(log, "warn" if warn_binary else "debug")(fname + ':' + str(err))
            completed.put(None)

        with multiprocessing.Pool(processes) as mp_pool:
            for fname in file_list:
                if prefix_gitdir:
                    fname = path.join(gitdir, fname)

                mp_pool.apply_async(_get_blame_out, args=(base_cmd, branch, fname, since, until),
                                    callback=process_blame_out,
                                    error_callback=partial(process_blame_out_error, fname))

            for _ in tqdm(file_list, desc=gitdir if prefix_gitdir else "Processing",
                          disable=silent_progress, unit="file"):
                completed.get()

            mp_pool.close()
            mp_pool.join()
    else:
        with tqdm(total=1, desc=gitdir if prefix_gitdir else "Processing", disable=silent_progress,
                  unit="repo") as t:
            blame_out = check_output(base_cmd + [branch], stderr=subprocess.STDOUT)
            t.update()
        log.log(logging.NOTSET, blame_out)

        # Strip binary files
        for fname in set(RE_STAT_BINARY.findall(blame_out)):
            getattr(log, "warn" if warn_binary else "debug")("binary:%s", fname.strip())
        lines = RE_STAT_BINARY.sub('', blame_out).splitlines()

        commit_infos = defaultdict(_CommitInfo)
        commit_info: Optional[_CommitInfo] = None
        for line_num, line in enumerate(lines):
            if not line:
                continue

            if m := RE_AUTHS_LOG_COMMIT.match(line):
                commit = m['commit']
                commit_info = commit_infos[commit]
                commit_info.info.update({
                    'author': m['author'],
                    'author-mail': m['auth_email'],
                    'committer-time': m['timestamp'],})
            elif m := RE_AUTHS_LOG_FILE.match(line):
                fname = RE_RENAME.sub(r'\\2', m['fname'])
                inss, dels = m['inserts'], m['deletes']
                loc = (int(inss) if churn & CHURN_INS and inss else
                       0) + (int(dels) if churn & CHURN_DEL and dels else 0)

                commit_info.file_locs[fname] += loc
            else:
                assert False, f'error parsing blame line ({line_num}): {line}'

        for cinfo in commit_infos.values():
            for fname, loc in cinfo.file_locs.items():
                stats_append(fname, cinfo.info['author'], loc, cinfo.info['committer-time'],
                             cinfo.info['author-mail'])

    # quickly count commits (even if no surviving loc)
    log.log(logging.NOTSET, "authors:%s", list(auth_stats.keys()))
    auth_commits = check_output(git_cmd + ["shortlog", "-s", "-e", branch] + since + until)
    for (ncom, auth, em) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
        auth = author_canonicalizer(auth, em)
        auth_stats[auth]['commits'] += int(ncom)
        auth2em[auth].add(em)

    if show_email: # replace author name with email
        log.debug(auth2em)
        old = auth_stats
        auth_stats = defaultdict(lambda: {'loc': 0, 'files': set(), 'ctimes': [], 'commits': 0})

        for auth, stats in getattr(old, 'iteritems', old.items)():
            auth_email = list(auth2em[auth])[0] # TODO: count most used email?
            i = auth_stats[auth_email]
            i["loc"] += stats["loc"]
            i["files"].update(stats["files"])
            i["commits"] += stats["commits"]
            i["ctimes"] += stats["ctimes"]
        del old

    return auth_stats


def run(args):
    """args  : Namespace (`argopt.DictAttrWrap` or from `argparse`)"""
    log.debug("parsing args")

    if args.sort not in "loc commits files hours months".split():
        log.warning("--sort argument (%s) unrecognised\n%s", args.sort, __doc__)
        raise KeyError(args.sort)

    if not args.excl:
        args.excl = ""

    if isinstance(args.gitdir, str):
        args.gitdir = [args.gitdir]
    # strip `/`, `.git`
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
                      warn_binary=args.warn_binary, bytype=args.bytype, show_email=args.show_email,
                      prefix_gitdir=len(gitdirs) > 1, churn=churn, ignore_rev=args.ignore_rev,
                      ignore_revs_file=args.ignore_revs_file, processes=int(args.processes),
                      author_mapping_file_path=args.author_mapping_file_path,
                      author_email_mapping_file_path=args.author_email_mapping_file_path)

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
        for auth, stats in getattr(res, 'iteritems', res.items)():
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
        tabulate(auth_stats, stats_tot, args.sort, args.bytype, args.format, cost, args.enum))


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
