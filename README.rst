git-fame
========

Pretty-print ``git`` repository collaborators sorted by contributions.

|Py-Versions| |PyPI| |Conda-Forge| |Docker| |Snapcraft|

|Build-Status| |Coverage-Status| |Branch-Coverage-Status| |Codacy-Grade| |Libraries-Rank| |PyPI-Downloads|

|DOI-URI| |LICENCE| |OpenHub-Status| |Sponsor-Casper|

.. code:: sh

    ~$ git fame --cost hour,month --loc ins
    Processing: 100%|██████████████████████████| 1/1 [00:00<00:00,  2.16repo/s]
    Total commits: 1775
    Total ctimes: 2770
    Total files: 461
    Total hours: 449.7
    Total loc: 41659
    Total months: 151.0
    | Author               |   hrs |   mths |   loc |   coms |   fils |  distribution   |
    |:---------------------|------:|-------:|------:|-------:|-------:|:----------------|
    | Casper da Costa-Luis |   228 |    108 | 28572 |   1314 |    172 | 68.6/74.0/37.3  |
    | Stephen Larroque     |    28 |     18 |  5243 |    203 |     25 | 12.6/11.4/ 5.4  |
    | pgajdos              |     2 |      9 |  2606 |      2 |     18 | 6.3/ 0.1/ 3.9   |
    | Martin Zugnoni       |     2 |      5 |  1656 |      3 |      3 | 4.0/ 0.2/ 0.7   |
    | Kyle Altendorf       |     7 |      2 |   541 |     31 |      7 | 1.3/ 1.7/ 1.5   |
    | Hadrien Mary         |     5 |      1 |   469 |     31 |     17 | 1.1/ 1.7/ 3.7   |
    | Richard Sheridan     |     2 |      1 |   437 |     23 |      3 | 1.0/ 1.3/ 0.7   |
    | Guangshuo Chen       |     3 |      1 |   321 |     18 |      7 | 0.8/ 1.0/ 1.5   |
    | Noam Yorav-Raphael   |     4 |      1 |   229 |     11 |      6 | 0.5/ 0.6/ 1.3   |
    | github-actions[bot]  |     2 |      1 |   186 |      1 |     51 | 0.4/ 0.1/11.1   |
    ...

The ``distribution`` column is a percentage breakdown of ``loc/coms/fils``.
(e.g. in the table above, Casper has written surviving code in
``172/461 = 37.3%`` of all files).

------------------------------------------

.. contents:: Table of contents
   :backlinks: top
   :local:


Installation
------------

Latest PyPI stable release
~~~~~~~~~~~~~~~~~~~~~~~~~~

|PyPI| |PyPI-Downloads| |Libraries-Dependents|

.. code:: sh

    pip install git-fame

Latest development release on GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

|GitHub-Status| |GitHub-Stars| |GitHub-Commits| |GitHub-Forks| |GitHub-Updated|

Pull and install:

.. code:: sh

    pip install "git+https://github.com/casperdcl/git-fame.git@main#egg=git-fame"

Latest Conda release
~~~~~~~~~~~~~~~~~~~~

|Conda-Forge|

.. code:: sh

    conda install -c conda-forge git-fame

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

On Windows, run:

.. code:: sh

    git config --global alias.fame "!python -m gitfame"

This is probably not necessary on UNIX systems.
If ``git fame`` doesn't work after restarting the terminal on Linux & Mac OS, try (with single quotes):

.. code:: sh

    git config --global alias.fame '!python -m gitfame'

Tab completion
~~~~~~~~~~~~~~

Optionally, systems with ``bash-completion`` can install tab completion
support. The
`git-fame_completion.bash <https://raw.githubusercontent.com/casperdcl/git-fame/main/git-fame_completion.bash>`__
file needs to be copied to an appropriate folder.

On Ubuntu, the procedure would be:

.. code:: sh

    $ # Ensure completion works for `git` itself
    $ sudo apt-get install bash-completion

    $ # Install `git fame` completions
    $ sudo wget \
        https://raw.githubusercontent.com/casperdcl/git-fame/main/git-fame_completion.bash \
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

|Py-Versions| |README-Hits|

.. code::

    Usage:
      git-fame [--help | options] [<gitdir>...]

    Arguments:
      <gitdir>       Git directory [default: ./].
                     May be specified multiple times to aggregate across
                     multiple repositories.

    Options:
      -h, --help     Print this help and exit.
      -v, --version  Print module version and exit.
      --branch=<b>   Branch or tag [default: HEAD] up to which to check.
      --sort=<key>   [default: loc]|commits|files|hours|months.
      --loc=<type>   surv(iving)|ins(ertions)|del(etions)
                     What `loc` represents. Use 'ins,del' to count both.
                     defaults to 'surviving' unless `--cost` is specified.
      --excl=<f>     Excluded files (default: None).
                     In no-regex mode, may be a comma-separated list.
                     Escape (\,) for a literal comma (may require \\, in shell).
      --incl=<f>     Included files [default: .*]. See `--excl` for format.
      --since=<date>  Date from which to check. Can be absoulte (eg: 1970-01-31)
                      or relative to now (eg: 3.weeks).
      --until=<date>  Date to which to check. See `--since` for format.
      --cost=<method>  Include time cost in person-months (COCOMO) or
                       person-hours (based on commit times).
                       Methods: month(s)|cocomo|hour(s)|commit(s).
                       May be multiple comma-separated values.
                       Alters `--loc` default to imply 'ins' (COCOMO) or
                       'ins,del' (hours).
      -R, --recurse  Recursively find repositories & submodules within <gitdir>.
      -n, --no-regex  Assume <f> are comma-separated exact matches
                      rather than regular expressions [default: False].
                      NB: if regex is enabled ',' is equivalent to '|'.
      -s, --silent-progress    Suppress `tqdm` [default: False].
      --warn-binary  Don't silently skip files which appear to be binary data
                     [default: False].
      -e, --show-email  Show author email instead of name [default: False].
      --enum         Show row numbers [default: False].
      -t, --bytype             Show stats per file extension [default: False].
      -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                               version and the child's to find where the lines
                               came from [default: False].
      -M             Detect intra-file line moves and copies [default: False].
      -C             Detect inter-file line moves and copies [default: False].
      --ignore-rev=<rev>       Ignore changes made by the given revision
                               (requires `--loc=surviving`).
      --ignore-revs-file=<f>   Ignore revisions listed in the given file
                               (requires `--loc=surviving`).
      --format=<format>        Table format
          [default: pipe]|md|markdown|yaml|yml|json|csv|tsv|tabulate.
          May require `git-fame[<format>]`, e.g. `pip install git-fame[yaml]`.
          Any `tabulate.tabulate_formats` is also accepted.
      --manpath=<path>         Directory in which to install git-fame man pages.
      --log=<lvl>    FATAL|CRITICAL|ERROR|WARN(ING)|[default: INFO]|DEBUG|NOTSET.


If multiple user names and/or emails correspond to the same user, aggregate
``git-fame`` statistics and maintain a ``git`` repository properly by adding a
`.mailmap file <https://git-scm.com/docs/git-blame#_mapping_authors>`_.

FAQs
~~~~

Options such as ``-w``, ``-M``, and ``-C`` can increase accuracy, but take
longer to compute.

Note that specifying ``--sort=hours`` or ``--sort=months`` requires ``--cost``
to be specified appropriately.

Note that ``--cost=months`` (``--cost=COCOMO``) approximates
`person-months <https://en.wikipedia.org/wiki/COCOMO>`_ and should be used with
``--loc=ins``.

Meanwhile, ``--cost=hours`` (``--cost=commits``) approximates
`person-hours <https://github.com/kimmobrunfeldt/git-hours/blob/8aaeee237cb9d9028e7a2592a25ad8468b1f45e4/index.js#L114-L143>`_.

Extra care should be taken when using ``ins`` and/or ``del`` for ``--loc``
since all historical files (including those no longer surviving) are counted.
In such cases, ``--excl`` may need to be significantly extended.
On the plus side, it is faster to compute ``ins`` and ``del`` compared to
``surv``.

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

- Casper da Costa-Luis (`casperdcl <https://github.com/casperdcl>`__ |Sponsor-Casper|)

We are grateful for all |GitHub-Contributions|.

|README-Hits|

.. |Build-Status| image:: https://img.shields.io/github/actions/workflow/status/casperdcl/git-fame/test.yml?branch=main&label=git-fame&logo=GitHub
   :target: https://github.com/casperdcl/git-fame/actions/workflows/test.yml
.. |Coverage-Status| image:: https://img.shields.io/coveralls/github/casperdcl/git-fame/main?logo=coveralls
   :target: https://coveralls.io/github/casperdcl/git-fame
.. |Branch-Coverage-Status| image:: https://codecov.io/gh/casperdcl/git-fame/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/casperdcl/git-fame
.. |Codacy-Grade| image:: https://api.codacy.com/project/badge/Grade/bde789ee0e57491eb2bb8609bd4190c3
   :target: https://www.codacy.com/app/casper-dcl/git-fame/dashboard
.. |GitHub-Status| image:: https://img.shields.io/github/tag/casperdcl/git-fame.svg?maxAge=86400&logo=github
   :target: https://github.com/casperdcl/git-fame/releases
.. |GitHub-Forks| image:: https://img.shields.io/github/forks/casperdcl/git-fame.svg?logo=github
   :target: https://github.com/casperdcl/git-fame/network
.. |GitHub-Stars| image:: https://img.shields.io/github/stars/casperdcl/git-fame.svg?logo=github
   :target: https://github.com/casperdcl/git-fame/stargazers
.. |GitHub-Commits| image:: https://img.shields.io/github/commit-activity/y/casperdcl/git-fame?label=commits&logo=git
   :target: https://github.com/casperdcl/git-fame/graphs/commit-activity
.. |GitHub-Issues| image:: https://img.shields.io/github/issues-closed/casperdcl/git-fame.svg?logo=github
   :target: https://github.com/casperdcl/git-fame/issues
.. |GitHub-PRs| image:: https://img.shields.io/github/issues-pr-closed/casperdcl/git-fame.svg?logo=github
   :target: https://github.com/casperdcl/git-fame/pulls
.. |GitHub-Contributions| image:: https://img.shields.io/github/contributors/casperdcl/git-fame.svg?logo=github
   :target: https://github.com/casperdcl/git-fame/graphs/contributors
.. |GitHub-Updated| image:: https://img.shields.io/github/last-commit/casperdcl/git-fame?label=pushed&logo=github
   :target: https://github.com/casperdcl/git-fame/pulse
.. |Sponsor-Casper| image:: https://img.shields.io/badge/sponsor-FOSS-dc10ff.svg?logo=Contactless%20Payment
   :target: https://cdcl.ml/sponsor
.. |PyPI| image:: https://img.shields.io/pypi/v/git-fame.svg?logo=PyPI&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |PyPI-Downloads| image:: https://img.shields.io/pypi/dm/git-fame.svg?label=pypi%20downloads&logo=DocuSign
   :target: https://pypi.org/project/git-fame
.. |Py-Versions| image:: https://img.shields.io/pypi/pyversions/git-fame.svg?logo=python&logoColor=white
   :target: https://pypi.org/project/git-fame
.. |Conda-Forge| image:: https://img.shields.io/conda/v/conda-forge/git-fame.svg?label=conda-forge&logo=conda-forge
   :target: https://anaconda.org/conda-forge/git-fame
.. |Snapcraft| image:: https://img.shields.io/badge/snap-install-blue.svg?logo=snapcraft&logoColor=white
   :target: https://snapcraft.io/git-fame
.. |Docker| image:: https://img.shields.io/badge/docker-pull-blue.svg?logo=docker&logoColor=white
   :target: https://hub.docker.com/r/casperdcl/git-fame
.. |Libraries-Rank| image:: https://img.shields.io/librariesio/sourcerank/pypi/git-fame.svg?color=green&logo=koding
   :target: https://libraries.io/pypi/git-fame
.. |Libraries-Dependents| image:: https://img.shields.io/librariesio/dependent-repos/pypi/git-fame.svg?logo=koding
    :target: https://github.com/casperdcl/git-fame/network/dependents
.. |OpenHub-Status| image:: https://www.openhub.net/p/git-fame/widgets/project_thin_badge?format=gif
   :target: https://www.openhub.net/p/git-fame?ref=Thin+badge
.. |LICENCE| image:: https://img.shields.io/pypi/l/git-fame.svg?color=purple&logo=SPDX
   :target: https://raw.githubusercontent.com/casperdcl/git-fame/main/LICENCE
.. |DOI-URI| image:: https://img.shields.io/badge/DOI-10.5281/zenodo.2544975-blue.svg?color=purple&logo=ORCID
   :target: https://doi.org/10.5281/zenodo.2544975
.. |README-Hits| image:: https://cgi.cdcl.ml/hits?q=git-fame&style=social&r=https://github.com/casperdcl/git-fame
   :target: https://cgi.cdcl.ml/hits?q=git-fame&a=plot&r=https://github.com/casperdcl/git-fame&style=social
