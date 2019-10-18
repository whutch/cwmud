@echo off

IF /I "%1" == "clean" (
    CALL :clean-coverage
    CALL :clean-pyc
    CALL :clean-test
)

IF /I "%1" == "clean-coverage" (
    CALL :clean-coverage
)

IF /I "%1" == "clean-pyc" (
    CALL :clean-pyc
)

IF /I "%1" == "clean-test" (
    CALL :clean-test
)

IF /I "%1" == "coverage" (
    CALL :coverage
)

IF /I "%1" == "print-coverage" (
    CALL :print-coverage
)

IF /I "%1" == "test" (
    CALL :test
)

IF /I "%1" == "test-strict" (
    CALL :test-strict
)

IF /I "%1" == "tests" (
    CALL :test
)

EXIT /B %ERRORLEVEL%


:clean-coverage
    ECHO Cleaning coverage data.
    IF EXIST .coverage DEL /F/S/Q .coverage >NUL
    IF EXIST .coverage-html RD /S/Q .coverage-html
EXIT /B 0


:clean-pyc
    ECHO Cleaning cached bytecode.
    FOR /R %%d IN (__pycache__) DO IF EXIST %%d (RD /S/Q "%%d")
    DEL /F/S/Q .\*.pyc 2>NUL
EXIT /B 0


:clean-test
    ECHO Cleaning test data.
    IF EXIST .pytest_cache RD /S/Q .pytest_cache
EXIT /B 0


:coverage
    CALL :clean-coverage
    CALL :clean-test
    ECHO Generating coverage data.
    py.test --cov-report html --cov cwmud tests
EXIT /B 0


:print-coverage
    CALL :clean-coverage
    CALL :clean-test
    ECHO Printing coverage.
    py.test --cov cwmud tests
EXIT /B 0


:test
    CALL :clean-test
    ECHO Running tests.
    py.test --flake8 cwmud tests
EXIT /B 0


:test-strict
    CALL :clean-test
    ECHO Running strict tests.
    py.test --flake8 -x --strict cwmud tests
EXIT /B 0
