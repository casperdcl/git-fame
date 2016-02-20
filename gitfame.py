#!/usr/bin/env python
"""
Usage:
  gitfame.py [options] [<gitdir>]

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  --sort=<key>   Options: [default: loc], files, commits.
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from (default: False).
  -s, --silent-progress    Suppress `tqdm`.
Arguments:
  [<gitdir>]     Git directory (default: ./).
"""
from __future__ import print_function
from __future__ import division
import subprocess
from tqdm import tqdm
import re
__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__licence__ = "MPLv2.0"


RE_AUTHS = re.compile('^author (.+)$', flags=re.M)


def tr_hline(col_widths):
  return '+' + '+'.join('-' * i for i in col_widths) + '+'


def int_cast_or_len(i):
  try:
    return int(i)
  except:
    return len(i)


def main(args):
  # TODO: gitdir = args["<gitdir>"]

  file_list = subprocess.check_output(["git", "ls-files"]).strip().split('\n')
  # TODO: --exclude

  auth_stats = {}

  for fname in tqdm(file_list, desc="Blame", disable=args["--silent-progress"]):
    git_blame_cmd = ["git", "blame", fname, "--line-porcelain"]
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
    auth_commits = subprocess.check_output(["git", "shortlog", "-s", "-e"])
    auth_ncom_em = re.search(r"^\s*(\d+)\s+(" + auth + ")\s+<(.+?)>",
                             auth_commits, flags=re.M)
    if auth_ncom_em:
      # print (auth_ncom_em.group(1))
      auth_stats[auth]["commits"] = int(auth_ncom_em.group(1))

  stats_tot = dict((k, 0) for stats in auth_stats.itervalues() for k in stats)
  # print (stats_tot)
  for k in stats_tot:
    stats_tot[k] = sum(int_cast_or_len(stats.get(k, 0))
                       for stats in auth_stats.itervalues())
  print ('Total ' + '\nTotal '.join("{0:s}: {1:d}".format(k, v)
         for (k, v) in stats_tot.iteritems()))

  COL_NAMES = [
      "Author" + ' ' * (min(30, max(len(a) for a in auth_stats)) - 6),
      "   loc",
      "coms",
      "fils",
      " distribution "
  ]
  TR_HLINE = tr_hline([len(i) + 2 for i in COL_NAMES])
  print (TR_HLINE)
  print (("| {0:s} | {1:>6s} | {2:>4s} | {3:>4s} | {4} |").format(*COL_NAMES))
  print (TR_HLINE)
  for (auth, stats) in sorted(auth_stats.iteritems(),
                              key=lambda (x, y): int_cast_or_len(
                                  y.get(args["--sort"], 0)),
                              reverse=True):
    # print (stats)
    loc = stats["loc"]
    commits = stats.get("commits", 0)
    files = len(stats.get("files", []))
    print (("| {0:<" + str(len(COL_NAMES[0]) + 1) +
            "s}| {1:6d} | {2:4d} | {3:4d}"
            " | {4:4.1f}/{5:4.1f}/{6:4.1f} |").format(
        auth[:len(COL_NAMES[0]) + 1], loc, commits, files,
        100 * loc / stats_tot["loc"],
        100 * commits / stats_tot["commits"],
        100 * files / stats_tot["files"]).replace('100.0', ' 100'))
    # TODO: --bytype
  print (TR_HLINE)


if __name__ == '__main__':
  from docopt import docopt
  args = docopt(__doc__, version='0.3.2')
  # raise(Warning(str(args)))
  if args['<gitdir>'] is None:
    args['<gitdir>'] = '.'
    # sys.argv[0][:sys.argv[0].replace('\\','/').rfind('/')]
  if args["--sort"] not in ["loc", "commits", "files"]:
    raise(Warning("--sort argument unrecognised\n" + __doc__))
  main(args)
