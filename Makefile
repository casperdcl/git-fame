PYFILES = $(addprefix gitfame/,$(addsuffix .py,_gitfame _utils __init__ __main__))

.PHONY: distclean prebuildclean clean test run build release upload


distclean: prebuildclean clean
	@+rm -f $(PYFILES:%.py=%.so)
	@+rm -f $(PYFILES:%.py=%.c)
prebuildclean:
	@+rm -rf build/ dist/ git_fame.egg-info/
clean:
	@+rm -f $(PYFILES:%.py=%.pyc) $(PYFILES:%.py=%.pyo)
	@+rm -rf .coverage

test:
	flake8 --max-line-length=80 --ignore=E111,E114 --count --statistics $(PYFILES)
	nosetests gitfame.py --with-coverage --cover-erase --with-doctest --cover-package=gitfame,_utils -d -v

run:
	python -Om gitfame

build: prebuildclean
	python setup.py build_ext --inplace
	# python setup.py sdist --formats=gztar,zip bdist_wininst
	python setup.py sdist bdist_wheel

release: build clean

upload: prebuildclean test
	python setup.py sdist bdist_wheel upload
