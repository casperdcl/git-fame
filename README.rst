gitfame
=======

|PyPi Status|

Pretty-print ``git`` repository collaborators sorted by contributions.

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

Latest pypi stable release
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

    pip install git-fame

Latest development release on github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pull and install in the current directory:

.. code:: sh

    pip install -e git+https://github.com/casperdcl/git-fame.git@master#egg=git_fame

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
    $ sudo cp git-fame_completion.bash /etc/bash_completion.d/

followed by a terminal restart.


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
    >>> import sys
    >>> sys.argv = ['', '--sort=commits', '-wt', './path/to/my/repo']
    >>> gitfame.main()


Documentation
-------------

.. code:: sh

    Usage:
      gitfame [--help | options] [<gitdir>]

    Options:
      -h, --help     Print this help and exit.
      -v, --version  Print module version and exit.
      --sort=<key>    Options: [default: loc], files, commits.
      --excl=<f>      Excluded files [default: None].
                      In no-regex mode, may be a comma-separated list.
                      Escape (\,) for a literal comma (may require \\, in shell).
      --incl=<f>      Included files [default: .*]. See `--excl` for format.
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

    Arguments:
      <gitdir>       Git directory [default: ./].


Licence
-------

OSI approved.

Copyright (c) 2016 Casper da Costa-Luis.

This Source Code Form is subject to the terms of the
Mozilla Public License, v. 2.0.
If a copy of the MPL was not distributed with this file, You can obtain one
at `https://mozilla.org/MPL/2.0/ <https://mozilla.org/MPL/2.0/>`__.


Authors
-------

- Casper da Costa-Luis <casper@caspersci.uk.to>

.. |PyPi Status| image:: https://img.shields.io/pypi/v/git-fame.svg
   :target: https://pypi.python.org/pypi/git-fame
