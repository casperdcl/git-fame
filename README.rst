git-fame
========

Pretty-print ``git`` repository collaborators sorted by contributions.

|PyPI-Versions| |PyPI-Status| |Docker| |Snapcraft|

|Build-Status| |Coverage-Status| |Branch-Coverage-Status| |Codacy-Grade| |Libraries-Rank| |PyPI-Downloads|

|DOI-URI| |LICENCE| |OpenHub-Status| |Gift-Casper|

.. code:: sh

    ~$ git fame --cost hour,month
    Blame: 100%|██████████| 74/74 [00:00<00:00, 96.51file/s]
    Total commits: 1173
    Total ctimes: 1055
    Total files: 180
    Total hours: 255.1
    Total loc: 2716
    Total months: 8.7
    | Author                     |   hrs |   mths |   loc |   coms |   fils |  distribution   |
    |:---------------------------|------:|-------:|------:|-------:|-------:|:----------------|
    | Casper da Costa-Luis       |   100 |      7 |  2171 |    770 |     63 | 79.9/65.6/35.0  |
    | Stephen Larroque           |    16 |      1 |   243 |    202 |     19 | 8.9/17.2/10.6   |
    | Kyle Altendorf             |     6 |      0 |    41 |     31 |      3 | 1.5/ 2.6/ 1.7   |
    | Guangshuo Chen             |     2 |      0 |    35 |     18 |      6 | 1.3/ 1.5/ 3.3   |
    | Matthew Stevens            |     2 |      0 |    32 |      3 |      2 | 1.2/ 0.3/ 1.1   |
    | Noam Yorav-Raphael         |     3 |      0 |    23 |     11 |      4 | 0.8/ 0.9/ 2.2   |
    | Daniel Panteleit           |     2 |      0 |    16 |      2 |      2 | 0.6/ 0.2/ 1.1   |
    | Mikhail Korobov            |     2 |      0 |    15 |     11 |      6 | 0.6/ 0.9/ 3.3   |
    | Hadrien Mary               |     3 |      0 |    15 |     31 |     10 | 0.6/ 2.6/ 5.6   |
    | Johannes Hansen            |     2 |      0 |    14 |      1 |      2 | 0.5/ 0.1/ 1.1   |

The ``distribution`` column is a percentage breakdown of ``loc/coms/fils``.
(e.g. in the table above, Casper has written surviving code in
``63/180 = 35.0%`` of all files).

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

Latest Snapcraft release
~~~~~~~~~~~~~~~~~~~~~~~~

|Snapcraft|

.. code:: sh

    snap install git-fame

Latest Docker release
~~~~~~~~~~~~~~~~~~~~~

|Docker|

.. code:: sh

    docker pull casperdcl/git-fame
    docker run --rm casperdcl/git-fame --help
    docker run --rm -v </local/path/to/repository>:/repo casperdcl/git-fame

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

The list of all changes is available on the Releases page: |GitHub-Status|.


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

.. code::

    Usage:
      gitfame [--help | options] [<gitdir>...]

    Arguments:
      <gitdir>       Git directory [default: ./].
                     May be specified multiple times to aggregate across
                     multiple repositories.

    Options:
      -h, --help     Print this help and exit.
      -v, --version  Print module version and exit.
      --branch=<b>   Branch or tag [default: HEAD] up to which to check.
      --sort=<key>   [default: loc]|commits|files|hours|months.
      --loc=<type>   surviving|ins(ertions)|del(etions)
                     What `loc` represents. Use 'ins,del' to count both.
                     defaults to 'surviving' unless `--cost` is specified.
      --excl=<f>     Excluded files (default: None).
                     In no-regex mode, may be a comma-separated list.
                     Escape (\,) for a literal comma (may require \\, in shell).
      --incl=<f>     Included files [default: .*]. See `--excl` for format.
      --since=<date>  Date from which to check. Can be absoulte (eg: 1970-01-31)
                      or relative to now (eg: 3.weeks).
      --cost=<method>  Include time cost in person-months (COCOMO) or
                       person-hours (based on commit times).
                       Methods: month(s)|cocomo|hour(s)|commit(s).
                       May be multiple comma-separated values.
                       Alters `--loc` default to imply 'ins' (COCOMO) or
                       'ins,del' (hours).
      -n, --no-regex  Assume <f> are comma-separated exact matches
                      rather than regular expressions [default: False].
                      NB: if regex is enabled ',' is equivalent to '|'.
      -s, --silent-progress    Suppress `tqdm` [default: False].
      --warn-binary   Don't silently skip files which appear to be binary data
                      [default: False].
      -e, --show-email  Show author email instead of name [default: False].
      --enum    Show row numbers [default: False].
      -t, --bytype             Show stats per file extension [default: False].
      -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                               version and the child's to find where the lines
                               came from [default: False].
      -M  Detect intra-file line moves and copies [default: False].
      -C  Detect inter-file line moves and copies [default: False].
      --format=<format>        Table format
          [default: pipe]|md|markdown|yaml|yml|json|csv|tsv|tabulate.
          May require `git-fame[<format>]`, e.g. `pip install git-fame[yaml]`.
          Any `tabulate.tabulate_formats` is also accepted.
      --manpath=<path>         Directory in which to install git-fame man pages.
      --log=<lvl>     FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.


If multiple user names and/or emails correspond to the same user, aggregate
``git-fame`` statistics and maintain a ``git`` repository properly by adding a
`.mailmap file <https://git-scm.com/docs/git-blame#_mapping_authors>`_.

Examples
--------

CODEOWNERS
~~~~~~~~~~

Generating
`CODEOWNERS <https://help.github.com/en/articles/about-code-owners>`__:

.. code:: sh

    # bash syntax function for current directory git repository
    owners(){
      for f in $(git ls-files); do
        # filename
        echo -n "$f "
        # author emails if loc distribution >= 30%
        git fame -esnwMC --incl "$f" | tr '/' '|' \
          | awk -F '|' '(NR>6 && $6>=30) {print $2}' \
          | xargs echo
      done
    }

    # print to screen and file
    owners | tee .github/CODEOWNERS

    # same but with `tqdm` progress for large repos
    owners \
      | tqdm --total $(git ls-files | wc -l) \
        --unit file --desc "Generating CODEOWNERS" \
      > .github/CODEOWNERS

Zenodo config
~~~~~~~~~~~~~

Generating `.zenodo.json <https://developers.zenodo.org/#deposit-metadata>`__:

.. code:: sh

    git fame -wMC --format json \
      | jq -c '{creators: [.data[] | {name: .[0]}]}' \
      | sed -r -e 's/(\{"name")/\n    \1/g' -e 's/:/: /g' \
      > .zenodo.json

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

.. |Build-Status| image:: https://img.shields.io/github/workflow/status/casperdcl/git-fame/Test/master?logo=GitHub
   :target: https://github.com/casperdcl/git-fame/actions?query=workflow%3ATest
.. |Coverage-Status| image:: https://img.shields.io/coveralls/github/casperdcl/git-fame/master?logo=coveralls
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
   :target: https://caspersci.uk.to/donate
.. |PyPI-Status| image:: https://img.shields.io/pypi/v/git-fame.svg?logo=python&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |PyPI-Downloads| image:: https://img.shields.io/pypi/dm/git-fame.svg?label=pypi%20downloads&logo=python&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |PyPI-Versions| image:: https://img.shields.io/pypi/pyversions/git-fame.svg?logo=python&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |Snapcraft| image:: https://img.shields.io/badge/snap-install-82BEA0.svg?logo=snapcraft
   :target: https://snapcraft.io/git-fame
.. |Docker| image:: https://img.shields.io/badge/docker-pull-blue.svg?logo=docker
   :target: https://hub.docker.com/r/casperdcl/git-fame
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
