#!/usr/bin/env python
"""
Usage:
  gitfame.py [options] [<gitdir>]

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  --sort=<key>   Options: [default: loc], files, commits.
  --exclude-files=<f>      Comma-separated list (default: "").
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from (default: False).
  -s, --silent-progress    Suppress `tqdm` (default: False).
Arguments:
  [<gitdir>]     Git directory (default: ./).
"""
from __future__ import print_function
from __future__ import division
import subprocess
from tqdm import tqdm
import re
__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__date__ = "2016"


RE_AUTHS = re.compile('^author (.+)$', flags=re.M)


def tr_hline(col_widths, hl='-', x='+'):
  return x + x.join(hl * i for i in col_widths) + x


def int_cast_or_len(i):
  try:
    return int(i)
  except:
    return len(i)


def Max(it):
  try:
    return max(it)
  except ValueError as e:
    if 'empty sequence' in str(e):
      return 0
    raise


def main(args):
  gitdir = args["<gitdir>"].rstrip('\\/')
  git_cmd = ["git", "--git-dir", gitdir + "/.git", "--work-tree", gitdir]
  exclude_files = args["--exclude-files"].split(',')

  file_list = subprocess.check_output(git_cmd +
                                      ["ls-files"]).strip().split('\n')
  # TODO: --exclude-regex

  auth_stats = {}

  for fname in tqdm(file_list, desc="Blame", disable=args["--silent-progress"]):
    if fname in exclude_files:
      continue

    git_blame_cmd = git_cmd + ["blame", fname, "--line-porcelain"]
    if args["--ignore-whitespace"]:
      git_blame_cmd.append("-w")
    try:
      blame_out = subprocess.check_output(git_blame_cmd,
                                          stderr=subprocess.STDOUT)
    except:
      continue
    auths = RE_AUTHS.findall(blame_out)

    for auth in auths:
      try:
        auth_stats[auth]["loc"] += 1
      except KeyError:
        auth_stats[auth] = {"loc": 1, "files": set([fname])}
      else:
        auth_stats[auth]["files"].add(fname)

  for auth in auth_stats.iterkeys():
    auth_commits = subprocess.check_output(git_cmd +
                                           ["shortlog", "-s", "-e"])
    auth_ncom_em = re.search(r"^\s*(\d+)\s+(" + auth + ")\s+<(.+?)>",
                             auth_commits, flags=re.M)
    if auth_ncom_em:
      # print (auth_ncom_em.group(1))
      auth_stats[auth]["commits"] = int(auth_ncom_em.group(1))

  if not len(auth_stats):
    auth_stats[""] = {"loc": 0, "files": set(), "commits": 0}

  stats_tot = dict((k, 0) for stats in auth_stats.itervalues() for k in stats)
  # print (stats_tot)
  for k in stats_tot:
    stats_tot[k] = sum(int_cast_or_len(stats.get(k, 0))
                       for stats in auth_stats.itervalues())
  print ('Total ' + '\nTotal '.join("{0:s}: {1:d}".format(k, v)
         for (k, v) in stats_tot.iteritems()))

  # Columns: Author | loc | coms | fils | distribution
  COL_LENS = [
    max(6, max(len(a) for a in auth_stats)),
    max(3, max(len(str(stats["loc"]))
               for stats in auth_stats.itervalues())),
    max(4, max(len(str(stats.get("commits", 0)))
               for stats in auth_stats.itervalues())),
    max(4, max(len(str(len(stats.get("files", []))))
               for stats in auth_stats.itervalues())),
    12
  ]

  COL_NAMES = [
      "Author" + ' ' * (COL_LENS[0] - 6),
      ' ' * (COL_LENS[1] - 3) + "loc",
      ' ' * (COL_LENS[2] - 4) + "coms",
      ' ' * (COL_LENS[3] - 4) + "fils",
      " distribution "
  ]

  tbl_row_fmt = "| {0:<%ds} | {1:>%dd} | {2:>%dd} | {3:>%dd} |" \
                " {4:4.1f}/{5:4.1f}/{6:4.1f} |" % tuple(COL_LENS[:4])

  TR_HLINE = tr_hline([len(i) + 2 for i in COL_NAMES])
  print (TR_HLINE)
  print (("| {0:s} | {1:s} | {2:s} | {3:s} | {4} |").format(*COL_NAMES))
  print (tr_hline([len(i) + 2 for i in COL_NAMES], '='))
  for (auth, stats) in sorted(auth_stats.iteritems(),
                              key=lambda (x, y): int_cast_or_len(
                                  y.get(args["--sort"], 0)),
                              reverse=True):
    # print (stats)
    loc = stats["loc"]
    commits = stats.get("commits", 0)
    files = len(stats.get("files", []))
    print (tbl_row_fmt.format(
        auth[:len(COL_NAMES[0]) + 1], loc, commits, files,
        100 * loc / max(1, stats_tot["loc"]),
        100 * commits / max(1, stats_tot["commits"]),
        100 * files / max(1, stats_tot["files"])).replace('100.0', ' 100'))
    # TODO: --bytype
  print (TR_HLINE)


if __name__ == "__main__":
  from docopt import docopt
  args = docopt(__doc__, version="0.5.1")
  # raise(Warning(str(args)))

  if args["<gitdir>"] is None:
    args["<gitdir>"] = './'
    # sys.argv[0][:sys.argv[0].replace('\\','/').rfind('/')]

  if args["--sort"] not in ["loc", "commits", "files"]:
    raise(Warning("--sort argument unrecognised\n" + __doc__))

  if not args["--exclude-files"]:
    args["--exclude-files"] = ""

  main(args)
