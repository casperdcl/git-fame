# IMPORTANT: for compatibility with `python setup.py make [alias]`, ensure:
# 1. Every alias is preceded by @[+]make (eg: @make alias)
# 2. A maximum of one @make alias or command per line
# see: https://github.com/tqdm/py-make/issues/1

.PHONY:
	alltests
	all
	flake8
	test
	testnose
	testsetup
	testcoverage
	testtimer
	distclean
	coverclean
	prebuildclean
	clean
	toxclean
	installdev
	install
	build
	buildupload
	pypi
	help
	none
	run

help:
	@python setup.py make -p

alltests:
	@+make testcoverage
	@+make flake8
	@+make testsetup

all:
	@+make alltests
	@+make build

flake8:
	@+flake8 --max-line-length=80 --ignore=E111,E114 --exclude .tox,build \
    -j 8 --count --statistics --exit-zero .

test:
	tox --skip-missing-interpreters

testnose:
	nosetests gitfame -d -v

testsetup:
	@make gitfame/git-fame.1
	python setup.py check --restructuredtext --strict
	python setup.py make none

testcoverage:
	@make coverclean
	nosetests gitfame --with-coverage --cover-package=gitfame --cover-erase --cover-min-percentage=80 -d -v

testtimer:
	nosetests gitfame --with-timer -d -v

gitfame/git-fame.1: .git-fame.1.md gitfame/_gitfame.py
	python -m gitfame --help | tail -n+9 | head -n-2 |\
    sed -r -e 's/\\/\\\\/g' \
      -e 's/^  (--\S+) (\S+)\s*(.*)$$/\n\\\1=*\2*\n: \3/' \
      -e 's/^  (-\S+, )(-\S+)\s*/\n\\\1\\\2\n: /' |\
    cat "$<" - |\
    pandoc -o "$@" -s -t man

distclean:
	@+make coverclean
	@+make prebuildclean
	@+make clean
prebuildclean:
	@+python -c "import shutil; shutil.rmtree('build', True)"
	@+python -c "import shutil; shutil.rmtree('dist', True)"
	@+python -c "import shutil; shutil.rmtree('git_fame.egg-info', True)"
coverclean:
	@+python -c "import os; os.remove('.coverage') if os.path.exists('.coverage') else None"
	@+python -c "import shutil; shutil.rmtree('gitfame/__pycache__', True)"
	@+python -c "import shutil; shutil.rmtree('gitfame/tests/__pycache__', True)"
clean:
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('*.py[co]')]"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('gitfame/*.py[co]')]"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('gitfame/*.c')]"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('gitfame/*.so')]"
	@+python -c "import os, glob; [os.remove(i) for i in glob.glob('gitfame/tests/*.py[co]')]"
toxclean:
	@+python -c "import shutil; shutil.rmtree('.tox', True)"


installdev:
	python setup.py develop --uninstall
	python setup.py develop

install:
	python setup.py install

build:
	@make prebuildclean
	@make testsetup
	python setup.py sdist bdist_wheel
	# python setup.py bdist_wininst

pypi:
	twine upload dist/*

buildupload:
	@make build
	@make pypi

none:
	# used for unit testing

run:
	python -Om gitfame
