# IMPORTANT: for compatibility with `python setup.py make [alias]`, ensure:
# 1. Every alias is preceded by @[+]make (eg: @make alias)
# 2. A maximum of one @make alias or command per line
#
# Sample makefile compatible with `python setup.py make`:
#```
#all:
#	@make test
#	@make install
#test:
#	nosetest
#install:
#	python setup.py install
#```

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
	installdev
	install
	build
	pypimeta
	pypi
	none
	run

help:
	@python setup.py make

alltests:
	@+make testcoverage
	@+make flake8
	@+make testsetup

all:
	@+make alltests
	@+make build

flake8:
	@+flake8 --max-line-length=80 --ignore=E111,E114 --exclude .tox --count --statistics --exit-zero .

test:
	tox --skip-missing-interpreters

testnose:
	nosetests gitfame -d -v

testsetup:
	python setup.py check --restructuredtext --strict
	python setup.py make none

testcoverage:
	@make coverclean
	nosetests gitfame --with-coverage --cover-package=gitfame --cover-erase --cover-min-percentage=80 -d -v

testtimer:
	nosetests gitfame --with-timer -d -v

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
	python setup.py sdist --formats=gztar,zip bdist_wheel
	python setup.py bdist_wininst

pypimeta:
	python setup.py register

pypi:
	twine upload dist/*

buildupload:
	@make testsetup
	@make build
	@make pypimeta
	@make pypi

none:
	# used for unit testing

run:
	python -Om gitfame

gitfame/git-fame.1: .git-fame.1.md
	python -m gitfame --help | tail -n+9 | head -n-2 | cat "$<" - |\
  sed -r 's/^  (--\S+) (\S+)\s*(.*)$$/\n\\\1=*\2*\n: \3/' |\
  sed -r 's/^  (-\S+, )(-\S+)\s*/\n\\\1\\\2\n: /' |\
  pandoc -o "$@" -s -t man
