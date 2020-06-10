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
  --excl=<f>     Excluded files (default: None).
                 In no-regex mode, may be a comma-separated list.
                 Escape (\,) for a literal comma (may require \\, in shell).
  --incl=<f>     Included files [default: .*]. See `--excl` for format.
  --since=<date>  Date from which to check. Can be absoulte (eg: 1970-01-31)
                  or relative to now (eg: 3.weeks).
  --cost=<method>  Include time cost in person-months (COCOMO) or
                   person-hours (based on commit times).
                   Methods: month(s)|cocomo|hour(s)|commit(s).
                   May be multiple comma-separated values.
  -n, --no-regex  Assume <f> are comma-separated exact matches
                  rather than regular expressions [default: False].
                  NB: if regex is enabled `,` is equivalent to `|`.
  -s, --silent-progress    Suppress `tqdm` [default: False].
  --warn-binary   Don't silently skip files which appear to be binary data
                  [default: False].
  -e, --show-email  Show author email instead of name [default: False].
  -t, --bytype             Show stats per file extension [default: False].
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from [default: False].
  -M  Detect intra-file line moves and copies [default: False].
  -C  Detect inter-file line moves and copies [default: False].
  --format=<format>        Table format
      [default: pipe]|md|markdown|yaml|yml|json|csv|tsv|tabulate.
      May require `git-fame[<format>]`, e.g. `pip install git-fame[yaml]`.
      Any `tabulate.tabulate_formats` is also accepted.
  --manpath=<path>         Directory in which to install git-fame man pages.
  --log=<lvl>     FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.
"""
from __future__ import print_function
from __future__ import division
# from __future__ import absolute_import
from functools import partial
import logging
import os
from os import path
import re
import subprocess

from ._utils import TERM_WIDTH, int_cast_or_len, fext, _str, \
    check_output, tqdm, TqdmStream, print_unicode, Str, string_types, \
    merge_stats
from ._version import __version__  # NOQA

__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016-2020"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__  # weird foreign language
log = logging.getLogger(__name__)

RE_AUTHS = re.compile(
    r'^\w+ \d+ \d+ (\d+)\nauthor (.+?)$.*?\ncommitter-time (\d+)',
    flags=re.M | re.DOTALL)
# finds all non-escaped commas
# NB: does not support escaping of escaped character
RE_CSPILT = re.compile(r'(?<!\\),')
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*?)\s+<(.*)>\s*$', flags=re.M)
# finds "boundary" line-porcelain messages
RE_BLAME_BOUNDS = re.compile(
    r'^\w+\s+\d+\s+\d+(\s+\d+)?\s*$[^\t]*?^boundary\s*$[^\t]*?^\t.*?$\r?\n',
    flags=re.M | re.DOTALL)


def hours(dates, maxCommitDiffInSec=120 * 60, firstCommitAdditionInMinutes=120):
  """
  Convert list of commit times (in seconds) to an estimate of hours spent.

  https://github.com/kimmobrunfeldt/git-hours/blob/\
8aaeee237cb9d9028e7a2592a25ad8468b1f45e4/index.js#L114-L143
  """
  dates = sorted(dates)
  diffInSec = [i - j for (i, j) in zip(dates[1:], dates[:-1])]
  res = sum(filter(lambda i: i < maxCommitDiffInSec, diffInSec))
  return (res / 60.0 + firstCommitAdditionInMinutes) / 60.0


def tabulate(
        auth_stats, stats_tot, sort='loc', bytype=False, backend='md',
        cost=None):
  """
  backends  : [default: md]|yaml|json|csv|tsv|tabulate|
    `in tabulate.tabulate_formats`
  """
  COL_NAMES = ['Author', 'loc', 'coms', 'fils', ' distribution']
  it_as = getattr(auth_stats, 'iteritems', auth_stats.items)
  # get ready
  tab = [[auth,
          s['loc'],
          s.get('commits', 0),
          len(s.get('files', [])),
          '/'.join(map('{0:4.1f}'.format, (
              100 * s['loc'] / max(1, stats_tot['loc']),
              100 * s.get('commits', 0) / max(1, stats_tot['commits']),
              100 * len(s.get('files', [])) / max(1, stats_tot['files'])
          ))).replace('/100.0/', '/ 100/')]
         for (auth, s) in it_as()]
  if cost is None:
    cost = ''
  if cost:
    cost = cost.lower()
    stats_tot = dict(stats_tot)
    if any(i in cost for i in ['cocomo', 'month']):
      COL_NAMES.insert(1, 'mths')
      tab = [i[:1] + [3.2 * (i[1] / 1e3)**1.05] + i[1:] for i in tab]
      stats_tot.setdefault('months', '%.1f' % sum(i[1] for i in tab))
    if any(i in cost for i in ['commit', 'hour']):
      COL_NAMES.insert(1, 'hrs')
      tab = [i[:1] + [hours(auth_stats[i[0]]['ctimes'])] + i[1:] for i in tab]

    stats_tot.setdefault('hours', '%.1f' % sum(i[1] for i in tab))
  # log.debug(auth_stats)

  for i, j in [("commits", "coms"), ("files", "fils"), ("hours", "hrs"),
               ("months", "mths")]:
    sort = sort.replace(i, j)
  tab.sort(key=lambda i: i[COL_NAMES.index(sort)], reverse=True)

  totals = 'Total ' + '\nTotal '.join(
      "%s: %s" % i for i in sorted(stats_tot.items())) + '\n'

  backend = backend.lower()
  if backend in ("tabulate", "md", "markdown"):
    backend = "pipe"

  if backend in ['yaml', 'yml', 'json', 'csv', 'tsv']:
    tab = [i[:-1] + [float(pc.strip()) for pc in i[-1].split('/')] for i in tab]
    tab = dict(
        total=stats_tot, data=tab,
        columns=COL_NAMES[:-1] + ['%' + i for i in COL_NAMES[-4:-1]])
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
    else:  # pragma: nocover
      raise RuntimeError("Should be unreachable")
  else:
    import tabulate as tabber
    if backend not in tabber.tabulate_formats:
      raise ValueError("Unknown backend:%s" % backend)
    log.debug("backend:tabulate:" + backend)
    COL_LENS = [max(len(Str(i[j])) for i in [COL_NAMES] + tab)
                for j in range(len(COL_NAMES))]
    COL_LENS[0] = min(
        TERM_WIDTH - sum(COL_LENS[1:]) - len(COL_LENS) * 3 - 4,
        COL_LENS[0])
    tab = [[i[0][:COL_LENS[0]]] + i[1:] for i in tab]
    return totals + tabber.tabulate(
        tab, COL_NAMES, tablefmt=backend, floatfmt='.0f')
    # from ._utils import tighten
    # return totals + tighten(tabber(...), max_width=TERM_WIDTH)


def _get_auth_stats(
        gitdir, branch="HEAD", since=None, include_files=None,
        exclude_files=None, silent_progress=False, ignore_whitespace=False,
        M=False, C=False, warn_binary=False, bytype=False, show_email=False,
        prefix_gitdir=False):
  """Returns dict: {"<author>": {"loc": int, "files": {}, "commits": int,
                                 "ctimes": [int]}}"""
  since = ["--since", since] if since else []
  git_cmd = ["git", "-C", gitdir]
  log.debug("base command:" + ' '.join(git_cmd))
  file_list = check_output(
      git_cmd + ["ls-files", "--with-tree", branch]).strip().split('\n')
  if not hasattr(include_files, 'search'):
    file_list = [i for i in file_list
                 if (not include_files or (i in include_files))
                 if i not in exclude_files]
  else:
    file_list = [i for i in file_list
                 if include_files.search(i)
                 if not (exclude_files and exclude_files.search(i))]
  log.log(logging.NOTSET, "files:\n" + '\n'.join(file_list))

  auth_stats = {}
  for fname in tqdm(file_list, desc=gitdir if prefix_gitdir else "Blame",
                    disable=silent_progress, unit="file"):
    git_blame_cmd = git_cmd + ["blame", "--line-porcelain", branch, fname] + \
        since
    if prefix_gitdir:
      fname = path.join(gitdir, fname)
    if ignore_whitespace:
      git_blame_cmd.append("-w")
    if M:
      git_blame_cmd.append("-M")
    if C:
      git_blame_cmd.extend(["-C", "-C"])  # twice to include file creation
    try:
      blame_out = check_output(git_blame_cmd, stderr=subprocess.STDOUT)
    except Exception as e:
      getattr(log, "warn" if warn_binary else "debug")(fname + ':' + str(e))
      continue
    log.log(logging.NOTSET, blame_out)

    # Strip boundary messages,
    # preventing user with nearest commit to boundary owning the LOC
    blame_out = RE_BLAME_BOUNDS.sub('', blame_out)
    loc_auth_times = RE_AUTHS.findall(blame_out)

    for loc, auth, tstamp in loc_auth_times:  # for each chunk
      loc = int(loc)
      auth = _str(auth)
      tstamp = int(tstamp)
      try:
        auth_stats[auth]["loc"] += loc
      except KeyError:
        auth_stats[auth] = {"loc": loc, "files": set([fname]), "ctimes": []}
      else:
        auth_stats[auth]["files"].add(fname)
        auth_stats[auth]["ctimes"].append(tstamp)

      if bytype:
        fext_key = ("." + fext(fname)) if fext(fname) else "._None_ext"
        # auth_stats[auth].setdefault(fext_key, 0)
        try:
          auth_stats[auth][fext_key] += loc
        except KeyError:
          auth_stats[auth][fext_key] = loc

  log.log(logging.NOTSET, "authors:" + '; '.join(auth_stats.keys()))
  auth_commits = check_output(
      git_cmd + ["shortlog", "-s", "-e", branch] + since)
  for stats in auth_stats.values():
    stats.setdefault("commits", 0)
  log.debug(RE_NCOM_AUTH_EM.findall(auth_commits.strip()))
  auth2em = {}
  for (ncom, auth, em) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
    auth = _str(auth)
    auth2em[auth] = em  # TODO: count most used email?
    try:
      auth_stats[auth]["commits"] += int(ncom)
    except KeyError:
      auth_stats[auth] = {"loc": 0,
                          "files": set([]),
                          "commits": int(ncom),
                          "ctimes": []}
  if show_email:
    # replace author name with email
    log.debug(auth2em)
    old = auth_stats
    auth_stats = {}
    for auth, stats in getattr(old, 'iteritems', old.items)():
      i = auth_stats.setdefault(auth2em[auth], {"loc": 0,
                                                "files": set([]),
                                                "commits": 0,
                                                "ctimes": []})
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
    log.warn("--sort argument (%s) unrecognised\n%s" % (
        args.sort, __doc__))
    raise KeyError(args.sort)

  if not args.excl:
    args.excl = ""

  if isinstance(args.gitdir, string_types):
    args.gitdir = [args.gitdir]
  gitdirs = [i.rstrip(os.sep) for i in args.gitdir]

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

  auth_stats = {}
  statter = partial(
      _get_auth_stats,
      branch=args.branch, since=args.since,
      include_files=include_files, exclude_files=exclude_files,
      silent_progress=args.silent_progress,
      ignore_whitespace=args.ignore_whitespace, M=args.M, C=args.C,
      warn_binary=args.warn_binary, bytype=args.bytype,
      show_email=args.show_email, prefix_gitdir=len(gitdirs) > 1)

  # concurrent multi-repo processing
  if len(gitdirs) > 1:
    try:
      from concurrent.futures import ThreadPoolExecutor  # NOQA
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

  stats_tot = dict((k, 0) for stats in auth_stats.values() for k in stats)
  log.debug(stats_tot)
  for k in stats_tot:
    stats_tot[k] = sum(int_cast_or_len(stats.get(k, 0))
                       for stats in auth_stats.values())
  log.debug(stats_tot)

  # TODO:
  # extns = set()
  # if args.bytype:
  #   for stats in auth_stats.values():
  #     extns.update([fext(i) for i in stats["files"]])
  # log.debug(extns)

  print_unicode(tabulate(
      auth_stats, stats_tot,
      args.sort, args.bytype, args.format, args.cost))


def main(args=None):
  """args  : list [default: sys.argv[1:]]"""
  from argopt import argopt
  args = argopt(__doc__ + '\n' + __copyright__,
                version=__version__).parse_args(args=args)
  logging.basicConfig(
      level=getattr(logging, args.log, logging.INFO),
      stream=TqdmStream,
      format="%(levelname)s:gitfame.%(funcName)s:%(lineno)d:%(message)s")

  log.debug(args)
  if args.manpath is not None:
    from os import path
    from shutil import copyfile
    from pkg_resources import resource_filename, Requirement
    import sys
    fi = resource_filename(Requirement.parse('git-fame'), 'gitfame/git-fame.1')
    fo = path.join(args.manpath, 'git-fame.1')
    copyfile(fi, fo)
    log.info("written:" + fo)
    sys.exit(0)

  run(args)


if __name__ == "__main__":  # pragma: no cover
  main()
