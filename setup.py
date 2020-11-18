#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ast import literal_eval
from io import open as io_open
from os import path
from setuptools import setup
import sys

src_dir = path.abspath(path.dirname(__file__))
if sys.argv[1].lower().strip() == 'make':  # exec Makefile commands
    import pymake
    fpath = path.join(src_dir, 'Makefile')
    pymake.main(['-f', fpath] + sys.argv[2:])
    # Stop to avoid setup.py raising non-standard command error
    sys.exit(0)

ext_modules = []
if '--cython' in sys.argv:
    sys.argv.remove('--cython')
    try:
        from Cython.Build import cythonize
        ext_modules = cythonize([
            "gitfame/_gitfame.py", "gitfame/_utils.py"], nthreads=2)
    except ImportError:
        pass

__author__ = None
__licence__ = None
for line in io_open(path.join(src_dir, 'gitfame', '_gitfame.py'), mode='r'):
    if line.startswith('__author__'):
        __author__ = literal_eval(line.split('=', 1)[1].strip())
    elif line.startswith('__licence__'):
        __licence__ = literal_eval(line.split('=', 1)[1].strip())

setup(
    use_scm_version=True,
    license=__licence__.lstrip('[').split(']')[0],
    author=__author__.split('<')[0].strip(),
    author_email=__author__.split('<')[1][:-1],
    test_suite='nose.collector',
    ext_modules=ext_modules,
)
