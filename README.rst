git-fame
========

Pretty-print ``git`` repository collaborators sorted by contributions.

|PyPI-Status| |PyPI-Versions|

|Build-Status| |Coverage-Status| |Branch-Coverage-Status| |Codacy-Grade| |Libraries-Rank|

|DOI-URI| |LICENCE| |OpenHub-Status| |Gift-Casper|

.. code:: sh

    ~$ git fame
    Blame: 100%|███████████████████████████████████| 11/11 [00:00<00:00, 208.43it/s]
    Total commits: 302
    Total files: 37
    Total loc: 3134
    +----------------------+------+------+------+----------------+
    | Author               |  loc | coms | fils |  distribution  |
    +======================+======+======+======+================+
    | Casper da Costa-Luis | 3123 |  297 |   35 | 99.6/98.3/85.4 |
    | Not Committed Yet    |    7 |    4 |    2 |  0.2/ 1.3/ 4.9 |
    | Evïan Etàcidñys      |    4 |    1 |    1 |  0.1/ 0.3/ 2.4 |
    +----------------------+------+------+------+----------------+

The ``distribution`` column is a percentage breakdown of the other columns
(e.g. in the table above, Casper has written surviving code in
``35/37 = 85.4%`` of all files)

------------------------------------------

.. contents:: Table of contents
   :backlinks: top
   :local:


Installation
------------

Latest PyPI stable release
~~~~~~~~~~~~~~~~~~~~~~~~~~

|PyPI-Status| |PyPI-Downloads| |Libraries-Dependents|

.. code:: sh

    pip install git-fame

Latest development release on GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

|GitHub-Status| |GitHub-Stars| |GitHub-Commits| |GitHub-Forks| |GitHub-Updated|

Pull and install in the current directory:

.. code:: sh

    pip install -e git+https://github.com/casperdcl/git-fame.git@master#egg=git-fame

Register alias with git
~~~~~~~~~~~~~~~~~~~~~~~

This is probably not necessary on UNIX systems.

.. code:: sh

    git config --global alias.fame "!python -m gitfame"

Tab completion
~~~~~~~~~~~~~~

Optionally, systems with ``bash-completion`` can install tab completion
support. The
`git-fame_completion.bash <https://raw.githubusercontent.com/casperdcl/git-fame/master/git-fame_completion.bash>`__
file needs to be copied to an appropriate folder.

On Ubuntu, the procedure would be:

.. code:: sh

    $ # Ensure completion works for `git` itself
    $ sudo apt-get install bash-completion

    $ # Install `git fame` completions
    $ sudo wget \
        https://raw.githubusercontent.com/casperdcl/git-fame/master/git-fame_completion.bash \
        -O /etc/bash_completion.d/git-fame_completion.bash

followed by a terminal restart.


Changelog
---------

The list of all changes is available either on GitHub's Releases:
|GitHub-Status| or on crawlers such as
`allmychanges.com <https://allmychanges.com/p/python/git-fame/>`_.


Usage
-----

.. code:: sh

    git fame              # If alias registered with git (see above)
    git-fame              # Alternative execution as python console script
    python -m gitfame     # Alternative execution as python module
    git-fame -h           # Print help

For example, to print statistics regarding all source files in a C++/CUDA
repository (``*.c/h/t(pp), *.cu(h)``), carefully handling whitespace and line
copies:

.. code:: sh

    git fame --incl '\.[cht][puh]{0,2}$' -twMC

It is also possible to run from within a python shell or script.

.. code:: python

    >>> import gitfame
    >>> gitfame.main(['--sort=commits', '-wt', '/path/to/my/repo'])


Documentation
-------------

|PyPI-Versions| |README-Hits|

.. code:: sh

    Usage:
      gitfame [--help | options] [<gitdir>]

    Arguments:
      <gitdir>       Git directory [default: ./].

    Options:
      -h, --help     Print this help and exit.
      -v, --version  Print module version and exit.
      --branch=<b>    Branch or tag [default: HEAD] up to which to check.
      --sort=<key>    [default: loc]|commits|files.
      --excl=<f>      Excluded files (default: None).
                      In no-regex mode, may be a comma-separated list.
                      Escape (\,) for a literal comma (may require \\, in shell).
      --incl=<f>      Included files [default: .*]. See `--excl` for format.
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
      -M              Detect intra-file line moves and copies [default: False].
      -C              Detect inter-file line moves and copies [default: False].
      --manpath=<path>         Directory in which to install git-fame man pages.
      --log=<lvl>     FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.


Contributions
-------------

|GitHub-Commits| |GitHub-Issues| |GitHub-PRs| |OpenHub-Status|

All source code is hosted on `GitHub <https://github.com/casperdcl/git-fame>`__.
Contributions are welcome.


LICENCE
-------

Open Source (OSI approved): |LICENCE|

Citation information: |DOI-URI|


Authors
-------

|OpenHub-Status|

- Casper da Costa-Luis (`casperdcl <https://github.com/casperdcl>`__ |Gift-Casper|)

We are grateful for all |GitHub-Contributions|.

|README-Hits|

.. |Build-Status| image:: https://img.shields.io/travis/casperdcl/git-fame/master.svg?logo=travis
   :target: https://travis-ci.org/casperdcl/git-fame
.. |Coverage-Status| image:: https://coveralls.io/repos/casperdcl/git-fame/badge.svg?branch=master
   :target: https://coveralls.io/github/casperdcl/git-fame
.. |Branch-Coverage-Status| image:: https://codecov.io/gh/casperdcl/git-fame/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/casperdcl/git-fame
.. |Codacy-Grade| image:: https://api.codacy.com/project/badge/Grade/bde789ee0e57491eb2bb8609bd4190c3
   :target: https://www.codacy.com/app/casper-dcl/git-fame/dashboard
.. |GitHub-Status| image:: https://img.shields.io/github/tag/casperdcl/git-fame.svg?maxAge=86400&logo=github&logoColor=white
   :target: https://github.com/casperdcl/git-fame/releases
.. |GitHub-Forks| image:: https://img.shields.io/github/forks/casperdcl/git-fame.svg?logo=github&logoColor=white
   :target: https://github.com/casperdcl/git-fame/network
.. |GitHub-Stars| image:: https://img.shields.io/github/stars/casperdcl/git-fame.svg?logo=github&logoColor=white
   :target: https://github.com/casperdcl/git-fame/stargazers
.. |GitHub-Commits| image:: https://img.shields.io/github/commit-activity/y/casperdcl/git-fame.svg?logo=git&logoColor=white
   :target: https://github.com/casperdcl/git-fame/graphs/commit-activity
.. |GitHub-Issues| image:: https://img.shields.io/github/issues-closed/casperdcl/git-fame.svg?logo=github&logoColor=white
   :target: https://github.com/casperdcl/git-fame/issues
.. |GitHub-PRs| image:: https://img.shields.io/github/issues-pr-closed/casperdcl/git-fame.svg?logo=github&logoColor=white
   :target: https://github.com/casperdcl/git-fame/pulls
.. |GitHub-Contributions| image:: https://img.shields.io/github/contributors/casperdcl/git-fame.svg?logo=github&logoColor=white
   :target: https://github.com/casperdcl/git-fame/graphs/contributors
.. |GitHub-Updated| image:: https://img.shields.io/github/last-commit/casperdcl/git-fame/master.svg?logo=github&logoColor=white&label=pushed
   :target: https://github.com/casperdcl/git-fame/pulse
.. |Gift-Casper| image:: https://img.shields.io/badge/gift-donate-dc10ff.svg
   :target: https://caspersci.uk.to/donate.html
.. |PyPI-Status| image:: https://img.shields.io/pypi/v/git-fame.svg
   :target: https://pypi.org/project/git-fame
.. |PyPI-Downloads| image:: https://img.shields.io/pypi/dm/git-fame.svg?label=pypi%20downloads&logo=python&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |PyPI-Versions| image:: https://img.shields.io/pypi/pyversions/git-fame.svg?logo=python&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |Libraries-Rank| image:: https://img.shields.io/librariesio/sourcerank/pypi/git-fame.svg?logo=koding&logoColor=white
   :target: https://libraries.io/pypi/git-fame
.. |Libraries-Dependents| image:: https://img.shields.io/librariesio/dependent-repos/pypi/git-fame.svg?logo=koding&logoColor=white
    :target: https://github.com/casperdcl/git-fame/network/dependents
.. |OpenHub-Status| image:: https://www.openhub.net/p/git-fame/widgets/project_thin_badge?format=gif
   :target: https://www.openhub.net/p/git-fame?ref=Thin+badge
.. |LICENCE| image:: https://img.shields.io/pypi/l/git-fame.svg
   :target: https://raw.githubusercontent.com/casperdcl/git-fame/master/LICENCE
.. |DOI-URI| image:: https://img.shields.io/badge/DOI-10.5281/zenodo.2544975-blue.svg
   :target: https://doi.org/10.5281/zenodo.2544975
.. |README-Hits| image:: https://caspersci.uk.to/cgi-bin/hits.cgi?q=git-fame&style=social&r=https://github.com/casperdcl/git-fame
   :target: https://caspersci.uk.to/cgi-bin/hits.cgi?q=git-fame&a=plot&r=https://github.com/casperdcl/git-fame&style=social
