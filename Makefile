
.DEFAULT_GOAL := nothing

.PHONY: clean clean-coverage clean-pyc clean-test coverage nothing test tests

clean: clean-coverage clean-pyc clean-test

clean-coverage:
	-rm .coverage
	-rm -r .coverage-html

clean-pyc:
	-find . -type f -and -name "*.pyc" | xargs rm
	-find . -type d -and -name "__pycache__" | xargs rm -r

clean-test:
	-rm -r .cache

coverage: clean-coverage clean-test
	py.test --cov-report html --cov atria tests

nothing:

test: clean-test
	py.test --flake8 atria tests

tests: test
