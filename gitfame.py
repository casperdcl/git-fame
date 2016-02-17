#!/usr/bin/env python
"""
Usage:
  gitfame.py [options] [<gitdir>]

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
Arguments:
  [<gitdir>]     Git directory (default: .).
"""
from __future__ import print_function
import sys
import subprocess
from tqdm import tqdm
__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"


def remove_all(s, remove_chars, replace=''):
  res = s
  for c in remove_chars:
    res = res.replace(c, replace)
  return res


def main(args):
  gitdir = args['<gitdir>']

  file_list = subprocess.check_output(["git", "ls-files"]).strip().split('\n')
  print(file_list)

  for fname in tqdm(file_list):
    pass

if __name__ == '__main__':
  from docopt import docopt
  args = docopt(__doc__, version='0.1.3')
  # raise(Warning(str(args)))
  if args['<gitdir>'] is None:
    args['<gitdir>'] = '.'
    # sys.argv[0][:sys.argv[0].replace('\\','/').rfind('/')]
  main(args)
