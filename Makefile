PYFILES = $(addsuffix .py,$(addprefix gitfame/,_gitfame _utils __init__ __main__ $(addprefix tests/test_,gitfame utils)))

.PHONY: distclean prebuildclean clean test run build release upload


distclean: prebuildclean clean
	@+rm -f $(PYFILES:%.py=%.so)
	@+rm -f $(PYFILES:%.py=%.c)
prebuildclean:
	@+rm -rf build/ dist/ git_fame.egg-info/
clean:
	@+rm -f $(PYFILES:%.py=%.pyc) $(PYFILES:%.py=%.pyo)
	@+rm -rf .coverage

test: flake8 testcoverage testsetup

run:
	python -Om gitfame

build: prebuildclean
	python setup.py build_ext --inplace
	python setup.py sdist --formats=gztar,zip bdist_wheel
	# python setup.py sdist --formats=gztar,zip bdist_wheel bdist_wininst

release: build clean

upload: prebuildclean test
	python setup.py sdist --formats=gztar,zip bdist_wheel upload
	# python setup.py sdist --formats=gztar,zip bdist_wheel bdist_wininst upload

testsetup:
	python setup.py check --metadata --strict

testcoverage:
	rm -f .coverage  # coverage erase
	nosetests gitfame --with-coverage --cover-package=gitfame --cover-erase --cover-min-percentage=80 -d -v gitfame/

flake8:
	@+flake8 --max-line-length=80 --count --statistics --ignore=E111,E114 $(PYFILES)
