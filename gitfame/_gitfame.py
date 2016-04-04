#!/usr/bin/env python
r"""
Usage:
  gitfame [--help | options] [<gitdir>]

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  --sort=<key>    Options: [default: loc], files, commits.
  --excl=<f>      Excluded files [default: None].
                  In no-regex mode, may be a comma-separated list.
                  Escape (\,) for a literal comma (may require \\, in shell).
  --incl=<f>      Included files [default: .*]. See `--excl` for format.
  -n, --no-regex  Assume <f> are comma-separated exact matches
                  rather than regular expressions [default: False].
                  NB: if regex is enabled `,` is equivalent to `|`.
  -s, --silent-progress    Suppress `tqdm` [default: False].
  -t, --bytype             Show stats per file extension [default: False].
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from [default: False].
  -M              Detect intra-file line moves and copies [default: False].
  -C              Detect inter-file line moves and copies [default: False].
Arguments:
  <gitdir>       Git directory [default: ./].
"""
from __future__ import print_function
from __future__ import division
# from __future__ import absolute_import
import subprocess
import re
from ._utils import TERM_WIDTH, int_cast_or_len, Max, fext, _str, tqdm

__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join(("Copyright (c)", __date__, __author__, __licence__))
__version__ = "1.1.0"
__license__ = __licence__  # weird foreign language


RE_AUTHS = re.compile('^author (.+)$', flags=re.M)
# finds all non-escaped commas
# NB: does not support escaping of escaped character
RE_CSPILT = re.compile(r'(?<!\\),')
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*)\s+<(.*)>\s*$', flags=re.M)


def tr_hline(col_widths, hl='-', x='+'):
  return x + x.join(hl * i for i in col_widths) + x


def blank_col(rows, i, blanks=' +=-'):
  lenR = len(rows[0])
  return all(r[i] in blanks for r in rows)


def tighten(t):
  """ Tighten grid table padding """
  rows = t.strip().split('\n')
  i = 1
  curr_blank = bool()
  prev_blank = blank_col(rows, i - 1)
  while (i < len(rows[0])):
    curr_blank = blank_col(rows, i)
    if prev_blank and curr_blank:
      rows = [r[:i - 1] + r[i:] for r in rows]
      i -= 1
    prev_blank = curr_blank
    i += 1
  return '\n'.join(rows)


def tabulate(auth_stats, stats_tot, args_sort="loc", args_bytype=False):
  it_as = getattr(auth_stats, 'iteritems', auth_stats.items)
  tab = [[auth, s['loc'], s.get('commits', 0), len(s.get('files', [])),
          '/'.join(map('{0:4.1f}'.format, (
              100 * s['loc'] / max(1, stats_tot["loc"]),
              100 * s.get('commits', 0) / max(1, stats_tot["commits"]),
              100 * len(s.get('files', [])) / max(1, stats_tot["files"])))
              ).replace('/100.0/', '/ 100/')
]
         for (auth, s) in sorted(it_as(),
             key=lambda k: int_cast_or_len(k[1].get(args_sort, 0)),
             reverse=True)]
  try:
    from tabulate import tabulate as tabber
    return tighten(tabber(tab,
                          ['Author', 'loc', 'coms', 'fils', '  distribution'],
                          tablefmt='grid', floatfmt='.0f'))
  except ImportError:
    pass

  res = ''
  it_val_as = getattr(auth_stats, 'itervalues', auth_stats.values)
  # Columns: Author | loc | coms | fils | distribution
  COL_LENS = [
      max(6, Max(len(a) for a in auth_stats)),
      max(3, Max(len(str(stats["loc"]))
                 for stats in it_val_as())),
      max(4, Max(len(str(stats.get("commits", 0)))
                 for stats in it_val_as())),
      max(4, Max(len(str(len(stats.get("files", []))))
                 for stats in it_val_as())),
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

  for (auth, stats) in tqdm(sorted(getattr(auth_stats, 'iteritems',
                                           auth_stats.items)(),
                                   key=lambda k: int_cast_or_len(
                                       k[1].get(args_sort, 0)),
                                   reverse=True), leave=False):
    # print (stats)
    loc = stats["loc"]
    commits = stats.get("commits", 0)
    files = len(stats.get("files", []))
    # TODO:
    # if args_bytype:
    #   print ([stats.get("files", []) ])
    res += (tbl_row_fmt.format(
        auth[:len(COL_NAMES[0]) + 1], loc, commits, files,
        100 * loc / max(1, stats_tot["loc"]),
        100 * commits / max(1, stats_tot["commits"]),
        100 * files / max(1, stats_tot["files"])).replace('100.0', ' 100')) \
        + '\n'
    # TODO: --bytype
  return res + TR_HLINE


def run(args):
  """ args: dict (docopt format) """

  # ! parsing args

  if args["<gitdir>"] is None:
    args["<gitdir>"] = './'
    # sys.argv[0][:sys.argv[0].replace('\\','/').rfind('/')]

  if args["--sort"] not in ["loc", "commits", "files"]:
    raise(Warning("--sort argument unrecognised\n" + __doc__))

  if not args["--excl"]:
    args["--excl"] = ""

  gitdir = args["<gitdir>"].rstrip(r'\/').rstrip('\\')

  exclude_files = None
  include_files = None
  if args["--no-regex"]:
    exclude_files = set(RE_CSPILT.split(args["--excl"]))
    include_files = set()
    if args["--incl"] == ".*":
      args["--incl"] = ""
    else:
      include_files.update(RE_CSPILT.split(args["--incl"]))
  else:
    # cannot use findall in case of grouping:
    # for i in include_files:
    # for i in [include_files]:
    #   for j in range(1, len(i)):
    #     if i[j] == '(' and i[j - 1] != '\\':
    #       raise ValueError('Parenthesis must be escaped'
    #                        ' in include-files:\n\t' + i)
    exclude_files = re.compile(args["--excl"])
    include_files = re.compile(args["--incl"])
    # include_files = re.compile(args["--incl"], flags=re.M)

  # ! iterating over files

  git_cmd = ["git", "-C", gitdir]
  file_list = _str(subprocess.check_output(
      git_cmd + ["ls-files"])).strip().split('\n')
  if args['--no-regex']:
    file_list = [i for i in file_list
                 if (not include_files or (i in include_files))
                 if not (i in exclude_files)]
  else:
    file_list = [i for i in file_list
                 if include_files.search(i)
                 if not exclude_files.search(i)]
  # print(file_list)

  auth_stats = {}
  for fname in tqdm(file_list, desc="Blame", disable=args["--silent-progress"]):
    git_blame_cmd = git_cmd + ["blame", fname, "--line-porcelain"]
    if args["--ignore-whitespace"]:
      git_blame_cmd.append("-w")
    if args["-M"]:
      git_blame_cmd.append("-M")
    if args["-C"]:
      git_blame_cmd.append("-C")
    try:
      blame_out = _str(subprocess.check_output(git_blame_cmd,
                                               stderr=subprocess.STDOUT))
    except:
      continue
    # print (blame_out)
    auths = RE_AUTHS.findall(blame_out)

    for auth in map(_str, auths):
      try:
        auth_stats[auth]["loc"] += 1
      except KeyError:
        auth_stats[auth] = {"loc": 1, "files": set([fname])}
      else:
        auth_stats[auth]["files"].add(fname)

      if args["--bytype"]:
        fext_key = ("." + fext(fname)) if fext(fname) else "._None_ext"
        # auth_stats[auth].setdefault(fext_key, 0)
        try:
          auth_stats[auth][fext_key] += 1
        except KeyError:
          auth_stats[auth][fext_key] = 1

  # print (auth_stats.keys())
  auth_commits = _str(subprocess.check_output(
      git_cmd + ["shortlog", "-s", "-e"]))
  it_val_as = getattr(auth_stats, 'itervalues', auth_stats.values)
  for stats in it_val_as():
    stats.setdefault("commits", 0)
  # print (RE_NCOM_AUTH_EM.findall(auth_commits.strip()))
  for (ncom, auth, _) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
    try:
      auth_stats[_str(auth)]["commits"] += int(ncom)
    except KeyError:
      # pass
      auth_stats[_str(auth)] = {"loc": 0,
                                "files": set([]),
                                "commits": int(ncom)}

  stats_tot = dict((k, 0) for stats in it_val_as() for k in stats)
  # print (stats_tot)
  for k in stats_tot:
    stats_tot[k] = sum(int_cast_or_len(stats.get(k, 0))
                       for stats in it_val_as())

  extns = set()
  if args["--bytype"]:
    for stats in it_val_as():
      extns.update([fext(i) for i in stats["files"]])
  # print (extns)

  print('Total ' + '\nTotal '.join("{0:s}: {1:d}".format(k, v)
        for (k, v) in sorted(getattr(
            stats_tot, 'iteritems', stats_tot.items)())))

  print(tabulate(auth_stats, stats_tot, args["--sort"]))


def main():
  from docopt import docopt
  args = docopt(__doc__ + '\n' + __copyright__, version=__version__)
  # raise(Warning(str(args)))

  run(args)


if __name__ == "__main__":
  main()
