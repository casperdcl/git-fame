PYFILES = $(addsuffix .py,gitfame _utils)

clean:
	rm -f $(PYFILES:%.py=%.pyc) $(PYFILES:%.py=%.pyo)

test:
	flake8 --max-line-length=80 --ignore=E111,E114 --count --statistics --exit-zero $(PYFILES)
	nosetests gitfame.py --with-coverage --cover-erase --with-doctest --cover-package=gitfame,_utils -d -v

run:
	python -Oc "from gitfame import main; main()"
