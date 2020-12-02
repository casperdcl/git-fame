#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from os import path

from setuptools import setup

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

setup(use_scm_version=True, test_suite='nose.collector', ext_modules=ext_modules)
