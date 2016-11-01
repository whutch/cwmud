
.DEFAULT_GOAL := nothing

.PHONY: clean clean-coverage clean-pyc clean-test coverage nothing test tests

clean: clean-coverage clean-pyc clean-test

clean-coverage:
	rm -f .coverage
	rm -rf .coverage-html

clean-pyc:
	find . -type f -and -name "*.pyc" | xargs --no-run-if-empty rm
	find . -type d -and -name "__pycache__" | xargs --no-run-if-empty rm -r

clean-test:
	rm -rf .cache

coverage: clean-coverage clean-test
	py.test --cov-report html --cov cwmud tests

nothing:

print-coverage: clean-coverage clean-test
	py.test --cov cwmud tests

test: clean-test
	py.test --flake8 cwmud tests

test-strict: clean-test
	py.test --flake8 -x --strict cwmud tests

tests: test
