# IMPORTANT: for compatibility with `python -m pymake [alias]`, ensure:
# 1. Every alias is preceded by @[+]make (eg: @make alias)
# 2. A maximum of one @make alias or command per line
# see: https://github.com/tqdm/py-make/issues/1

.PHONY:
	alltests
	all
	flake8
	test
	pytest
	testsetup
	testcoverage
	testtimer
	distclean
	coverclean
	prebuildclean
	clean
	toxclean
	install_build
	install_dev
	install
	build
	buildupload
	pypi
	docker
	help
	none
	run

help:
	@python -m pymake -p

alltests:
	@+make testcoverage
	@+make flake8
	@+make testsetup

all:
	@+make alltests
	@+make build

flake8:
	@+pre-commit run -a flake8

test:
	tox --skip-missing-interpreters -p all

pytest:
	pytest

testsetup:
	@make gitfame/git-fame.1
	@make help

testcoverage:
	@make coverclean
	pytest --cov=gitfame --cov-report=xml --cov-report=term --cov-fail-under=80

testtimer:
	pytest

gitfame/git-fame.1: .meta/.git-fame.1.md gitfame/_gitfame.py
	python -c 'import gitfame; print(gitfame._gitfame.__doc__.rstrip())' |\
    grep -A999 '^Options:$$' | tail -n+2 |\
    sed -r -e 's/\\/\\\\/g' \
      -e 's/^  (--\S+=)<(\S+)>\s+(.*)$$/\n\\\1*\2*\n: \3/' \
      -e 's/^  (-., )(-\S+)\s*/\n\\\1\\\2\n: /' \
      -e 's/^  (--\S+)\s+/\n\\\1\n: /' \
      -e 's/^  (-.)\s+/\n\\\1\n: /' |\
    cat "$<" - |\
    pandoc -o "$@" -s -t man

.dockerignore:
	@+python -c "fd=open('.dockerignore', 'w'); fd.write('*\n!dist/*.whl\n')"

distclean:
	@+make coverclean
	@+make prebuildclean
	@+make clean
prebuildclean:
	@+python -c "import shutil; shutil.rmtree('build', True)"
	@+python -c "import shutil; shutil.rmtree('dist', True)"
	@+python -c "import shutil; shutil.rmtree('git_fame.egg-info', True)"
	@+python -c "import shutil; shutil.rmtree('.eggs', True)"
	@+python -c "import os; os.remove('gitfame/_dist_ver.py') if os.path.exists('gitfame/_dist_ver.py') else None"
coverclean:
	@+python -c "import os; os.remove('.coverage') if os.path.exists('.coverage') else None"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('.coverage.*')]"
	@+python -c "import shutil; shutil.rmtree('gitfame/__pycache__', True)"
	@+python -c "import shutil; shutil.rmtree('tests/__pycache__', True)"
clean:
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('*.py[co]')]"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('gitfame/*.py[co]')]"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('tests/*.py[co]')]"
toxclean:
	@+python -c "import shutil; shutil.rmtree('.tox', True)"

install:
	python -m pip install .
install_dev:
	python -m pip install -e .
install_build:
	python -m pip install -r .meta/requirements-build.txt

build:
	@make prebuildclean
	@make testsetup
	python -m build
	python -m twine check dist/*

pypi:
	python -m twine upload dist/*

buildupload:
	@make build
	@make pypi

docker:
	@make build
	@make .dockerignore
	docker build . -t casperdcl/git-fame
	docker tag casperdcl/git-fame:latest casperdcl/git-fame:$(shell docker run --rm casperdcl/git-fame -v)
none:
	# used for unit testing

run:
	python -Om gitfame
