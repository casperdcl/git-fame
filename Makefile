# IMPORTANT: for compatibility with `python -m pymake [alias]`, ensure:
# 1. Every alias is preceded by @[+]make (eg: @make alias)
# 2. A maximum of one @make alias or command per line
# see: https://github.com/tqdm/py-make/issues/1
.PHONY:
	prebuildclean
	build

gitfame/git-fame.1: .meta/.git-fame.1.md gitfame/_gitfame.py
	python -c 'import gitfame; print(gitfame._gitfame.__doc__.rstrip())' |\
    grep -A999 '^Options:$$' | tail -n+2 |\
    sed -r -e 's/\\/\\\\/g' \
      -e 's/^  (--\S+=)<(\S+)>\s+(.*)$$/\n\\\1*\2*\n: \3/' \
      -e 's/^  (-., )(--\S+=)<(\S+)>\s+(.*)$$/\n\\\1\\\2*\3*\n: \4/' \
      -e 's/^  (-., )(-\S+)\s*/\n\\\1\\\2\n: /' \
      -e 's/^  (--\S+)\s+/\n\\\1\n: /' \
      -e 's/^  (-.)\s+/\n\\\1\n: /' |\
    cat "$<" - |\
    pandoc -o "$@" -s -t man

prebuildclean:
	@+python -c "import shutil; shutil.rmtree('build', True)"
	@+python -c "import shutil; shutil.rmtree('dist', True)"
	@+python -c "import shutil; shutil.rmtree('git_fame.egg-info', True)"
	@+python -c "import shutil; shutil.rmtree('.eggs', True)"

build: gitfame/git-fame.1
	@make prebuildclean
	python -m build
	python -m twine check dist/*
