% GIT-FAME(1) git-fame User Manuals
% Casper da Costa-Luis <https://github.com/casperdcl>
% 2016-2018

# NAME

git-fame - Pretty-print `git` repository collaborators sorted by contributions.

# SYNOPSIS

gitfame [\--help | *options*] [<*gitdir*>]

# DESCRIPTION

See <https://github.com/casperdcl/git-fame>.

Probably not necessary on UNIX systems:

```sh
git config --global alias.fame "!python -m gitfame"
```

For example, to print statistics regarding all source files in a C++/CUDA
repository (``*.c/h/t(pp), *.cu(h)``), carefully handling whitespace and line
copies:

```sh
git fame --incl '\.[cht][puh]{0,2}$' -twMC
```

# OPTIONS

\<gitdir>
: [default: ./]
