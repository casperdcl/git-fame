#!/usr/bin/env python
r"""Usage:
  gitfame [--help | options] [<gitdir>]

Arguments:
  <gitdir>       Git directory [default: ./].

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  --branch=<b>   Branch or tag [default: HEAD] up to which to check.
  --sort=<key>   [default: loc]|commits|files.
  --excl=<f>     Excluded files (default: None).
                 In no-regex mode, may be a comma-separated list.
                 Escape (\,) for a literal comma (may require \\, in shell).
  --incl=<f>     Included files [default: .*]. See `--excl` for format.
  --since=<date>  Date from which to check. Can be absoulte (eg: 1970-01-31)
                  or relative to now (eg: 3.weeks).
  -n, --no-regex  Assume <f> are comma-separated exact matches
                  rather than regular expressions [default: False].
                  NB: if regex is enabled `,` is equivalent to `|`.
  -s, --silent-progress    Suppress `tqdm` [default: False].
  -t, --bytype             Show stats per file extension [default: False].
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from [default: False].
  -M  Detect intra-file line moves and copies [default: False].
  -C  Detect inter-file line moves and copies [default: False].
  --format=<format>        Table format
      [default: md]|markdown|yaml|yml|json|csv|tsv|tabulate.
      May require `git-fame[<format>]`, e.g. `pip install git-fame[yaml]`.
  --manpath=<path>         Directory in which to install git-fame man pages.
  --log=<lvl>     FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.
"""
from __future__ import print_function
from __future__ import division
# from __future__ import absolute_import
import subprocess
import re
import logging

from ._utils import TERM_WIDTH, int_cast_or_len, Max, fext, _str, \
    check_output, tqdm, TqdmStream, print_unicode
from ._version import __version__  # NOQA

__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016-2018"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__license__ = __licence__  # weird foreign language


RE_AUTHS = re.compile('^\w+ \d+ \d+ (\d+)\nauthor (.+)$', flags=re.M)
# finds all non-escaped commas
# NB: does not support escaping of escaped character
RE_CSPILT = re.compile(r'(?<!\\),')
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*?)\s+<(.*)>\s*$', flags=re.M)


def tr_hline(col_widths, hl='-', x='+'):
  return x + x.join(hl * i for i in col_widths) + x


def tabulate(
        auth_stats, stats_tot, sort='loc', bytype=False, backend='md'):
  """
  backends  : [default: md]|yaml|json|csv|tsv|tabulate
  """
  log = logging.getLogger(__name__)
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
         for (auth, s) in sorted(it_as(),
         key=lambda k: int_cast_or_len(k[1].get(sort, 0)),
         reverse=True)]

  totals = 'Total ' + '\nTotal '.join(
      "%s: %d" % i for i in sorted(stats_tot.items())) + '\n'

  backend = backend.lower()
  if backend == 'tabulate':
    from tabulate import tabulate as tabber
    log.debug("backend:tabulate")
    return totals + tabber(tab, COL_NAMES, tablefmt='grid', floatfmt='.0f')
    # from ._utils import tighten
    # return totals + tighten(tabber(...), max_width=TERM_WIDTH)
  elif backend in ['yaml', 'yml', 'json', 'csv', 'tsv']:
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
      t.writerow(tab['total'].keys())
      t.writerow(tab['total'].values())
      return res.getvalue().rstrip()
    else:  # pragma: nocover
      raise RuntimeError("Should be unreachable")
  elif backend not in ['md', 'markdown']:
    raise ValueError("Unknown backend:%s" % backend)

  log.debug("backend:md")
  # TODO: convert below to separate function for testing

  res = ''
  stats = list(auth_stats.values())
  # Columns: Author | loc | coms | fils | distribution
  COL_LENS = [
      max(6, Max(len(a) for a in auth_stats)),
      max(3, Max(len(str(i["loc"])) for i in stats)),
      max(4, Max(len(str(i.get("commits", 0))) for i in stats)),
      max(4, Max(len(str(len(i.get("files", [])))) for i in stats)),
      12
  ]

  COL_LENS[0] = min(TERM_WIDTH - sum(COL_LENS[1:]) - len(COL_LENS) * 3 - 3,
                    COL_LENS[0])

  COL_NAMES = [
      "Author" + ' ' * (COL_LENS[0] - 6),
      ' ' * (COL_LENS[1] - 3) + "loc",
      ' ' * (COL_LENS[2] - 4) + "coms",
      ' ' * (COL_LENS[3] - 4) + "fils",
      " distribution "
  ]

  tbl_row_fmt = u"| {0:<%ds}| {1:>%dd} | {2:>%dd} | {3:>%dd} |" \
                u" {4:4.1f}/{5:4.1f}/{6:4.1f} |" % (COL_LENS[0] + 1,
                                                    COL_LENS[1],
                                                    COL_LENS[2],
                                                    COL_LENS[3])

  TR_HLINE = tr_hline([len(i) + 2 for i in COL_NAMES])
  res += TR_HLINE + '\n'
  res += ("| {0:s} | {1:s} | {2:s} | {3:s} | {4} |").format(*COL_NAMES) + '\n'
  res += tr_hline([len(i) + 2 for i in COL_NAMES], '=') + '\n'

  for (auth, stats) in tqdm(
      sorted(
          auth_stats.items(),
          key=lambda k: int_cast_or_len(k[1].get(sort, 0)),
          reverse=True), leave=False):
    # print (stats)
    loc = stats["loc"]
    commits = stats.get("commits", 0)
    files = len(stats.get("files", []))
    if bytype:
      log.debug("TODO:NotImplemented:--bytype")
      # TODO: print ([stats.get("files", []) ])
    res += (tbl_row_fmt.format(
        auth[:len(COL_NAMES[0]) + 1], loc, commits, files,
        100 * loc / max(1, stats_tot["loc"]),
        100 * commits / max(1, stats_tot["commits"]),
        100 * files / max(1, stats_tot["files"])).replace('100.0', ' 100')) \
        + '\n'
  return totals + res + TR_HLINE


def run(args):
  """args  : Namespace (`argopt.DictAttrWrap` or from `argparse`)"""
  log = logging.getLogger(__name__)

  log.debug("parsing args")

  if args.sort not in ["loc", "commits", "files"]:
    log.warn("--sort argument (" + args.sort +
             ") unrecognised\n" + __doc__)

  if not args.excl:
    args.excl = ""

  gitdir = args.gitdir.rstrip(r'\/').rstrip('\\')

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
    exclude_files = re.compile(args.excl)
    include_files = re.compile(args.incl)
    # include_files = re.compile(args.incl, flags=re.M)

  # ! iterating over files

  branch = args.branch
  since = ["--since", args.since] if args.since else []
  git_cmd = ["git", "-C", gitdir]
  log.debug("base command:" + ' '.join(git_cmd))
  file_list = check_output(
      git_cmd + ["ls-files", "--with-tree", branch]).strip().split('\n')
  if args.no_regex:
    file_list = [i for i in file_list
                 if (not include_files or (i in include_files))
                 if not (i in exclude_files)]
  else:
    file_list = [i for i in file_list
                 if include_files.search(i)
                 if not (args.excl and exclude_files.search(i))]
  log.log(logging.NOTSET, "files:\n" + '\n'.join(file_list))

  auth_stats = {}
  for fname in tqdm(file_list, desc="Blame", disable=args.silent_progress,
                    unit="file"):
    git_blame_cmd = git_cmd + ["blame", "--porcelain", branch, fname] + \
        since
    if args.ignore_whitespace:
      git_blame_cmd.append("-w")
    if args.M:
      git_blame_cmd.append("-M")
    if args.C:
      git_blame_cmd.extend(["-C", "-C"])  # twice to include file creation
    try:
      blame_out = check_output(git_blame_cmd, stderr=subprocess.STDOUT)
    except Exception as e:
      log.warn(fname + ':' + str(e))
      continue
    log.log(logging.NOTSET, blame_out)
    loc_auths = RE_AUTHS.findall(blame_out)

    for loc, auth in loc_auths:  # for each chunk
      loc = int(loc)
      auth = _str(auth)
      try:
        auth_stats[auth]["loc"] += loc
      except KeyError:
        auth_stats[auth] = {"loc": loc, "files": set([fname])}
      else:
        auth_stats[auth]["files"].add(fname)

      if args.bytype:
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
  for (ncom, auth, _) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
    try:
      auth_stats[_str(auth)]["commits"] += int(ncom)
    except KeyError:
      auth_stats[_str(auth)] = {"loc": 0,
                                "files": set([]),
                                "commits": int(ncom)}

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
      auth_stats, stats_tot, args.sort, args.bytype, args.format))


def main(args=None):
  """args  : list [default: sys.argv[1:]]"""
  from argopt import argopt
  args = argopt(__doc__ + '\n' + __copyright__,
                version=__version__).parse_args(args=args)
  logging.basicConfig(
      level=getattr(logging, args.log, logging.INFO),
      stream=TqdmStream)
  log = logging.getLogger(__name__)

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
