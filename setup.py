try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup
from gitfame import __licence__, __author__, __version__
import io
try:
  import sys
  if '--cython' in sys.argv:
    sys.argv.remove('--cython')
    from Cython.Build import cythonize
  else:
    raise ValueError('--cython')
except:
  def cythonize(*args, **kwargs):
    return []


setup(
    name='git-fame',
    description='Pretty-print `git` repository collaborators'
                ' sorted by contributions',
    long_description=io.open('README.rst', mode='r', encoding='utf-8').read(),
    version=__version__,
    licence=__licence__,
    author=__author__.split('<')[0],
    author_email=__author__.split('<')[1][:-1],
    url='https://github.com/casperdcl/git-fame/',
    bugtrack_url='https://github.com/casperdcl/git-fame/issues/',
    platforms=['any'],
    packages=['gitfame'],
    provides=['gitfame'],
    ext_modules=cythonize(["gitfame/_gitfame.py", "gitfame/_utils.py"],
                          nthreads=2),
    classifiers=[
        # Trove classifiers
        # (https://pypi.python.org/pypi?%3Aaction=list_classifiers)
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Environment :: Console',
        'Framework :: IPython',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: BSD :: FreeBSD',
        'Operating System :: POSIX :: SunOS/Solaris',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: IronPython',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: System :: Monitoring',
        'Topic :: Terminals',
        'Topic :: Utilities',
        'Intended Audience :: Developers',
    ],
    keywords='git blame stat stats statistics count author commit commits' \
             ' log shortlog ls-files',
)
