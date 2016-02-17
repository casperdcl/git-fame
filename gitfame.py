#!/usr/bin/env python
"""
Usage:
  gitfame.py [options] [<gitdir>]

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from (default: False).
Arguments:
  [<gitdir>]     Git directory (default: .).
"""
from __future__ import print_function
import subprocess
from tqdm import tqdm
import re
__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__licence__ = "MPLv2.0"


RE_AUTHS = re.compile('^author (.+)$', flags=re.M)


def line_break(*col_widths):
  return '+' + '+'.join('-' * i for i in col_widths) + '+'


def remove_all(s, remove_chars, replace=''):
  res = s
  for c in remove_chars:
    res = res.replace(c, replace)
  return res


def main(args):
  # gitdir = args["<gitdir>"]

  file_list = subprocess.check_output(["git", "ls-files"]).strip().split('\n')
  # TODO: --exclude

  auth_stats = {}

  for fname in tqdm(file_list):
    blame_cmd = ["git", "blame", fname, "--line-porcelain"]
    if args["--ignore-whitespace"]:
      blame_cmd.append("-w")
    blame_out = subprocess.check_output(blame_cmd)
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
      auth_stats[auth]["commits"] = int(auth_ncom_em.group(1))

  LINE_BREAK = (line_break(32, 8))
  print (LINE_BREAK)
  print ("| {0:30s} | {1:>6s} |".format("Author", "loc"))
  print (LINE_BREAK)
  for (auth, stats) in auth_stats.iteritems():
    # print (stats)
    print ("| {0:30s} | {1:6d} |".format(auth, stats["loc"]))
    # TODO: --bytype
    # TODO: --progress
    print (LINE_BREAK)


if __name__ == '__main__':
  from docopt import docopt
  args = docopt(__doc__, version='0.1.3')
  # raise(Warning(str(args)))
  # if args['<gitdir>'] is None:
  #   args['<gitdir>'] = '.'
  #   # sys.argv[0][:sys.argv[0].replace('\\','/').rfind('/')]
  main(args)
