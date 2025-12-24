@echo off
REM Script to run auth provider tests with proper Docker infrastructure (Windows)

setlocal enabledelayedexpansion

echo ========================================
echo SARK Auth Provider Test Runner
echo ========================================
echo.

set COMMAND=%1
set TEST_TYPE=%2

if "%COMMAND%"=="" set COMMAND=run
if "%TEST_TYPE%"=="" set TEST_TYPE=all

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop and try again
    exit /b 1
)
echo [OK] Docker is running
echo.

if "%COMMAND%"=="start" goto start
if "%COMMAND%"=="stop" goto stop
if "%COMMAND%"=="run" goto run
if "%COMMAND%"=="test" goto test
goto usage

:start
    echo Starting test services...
    call :cleanup
    call :start_services
    call :wait_services
    echo.
    echo [OK] Services are ready for testing
    goto :eof

:stop
    call :cleanup
    goto :eof

:run
    call :cleanup
    call :start_services
    call :wait_services
    call :run_tests
    set TEST_RESULT=!errorlevel!
    call :cleanup
    exit /b !TEST_RESULT!

:test
    call :run_tests
    goto :eof

:usage
    echo Usage: %0 {start^|stop^|run^|test} [test_type]
    echo.
    echo Commands:
    echo   start       - Start Docker test services
    echo   stop        - Stop and remove Docker test services
    echo   run         - Full test run (start services, run tests, cleanup)
    echo   test        - Run tests only (services must be started separately)
    echo.
    echo Test types (for 'run' and 'test'):
    echo   all         - Run all auth provider tests (default)
    echo   unit        - Run only unit tests
    echo   integration - Run only integration tests
    echo   ldap        - Run only LDAP tests
    echo   oidc        - Run only OIDC tests
    echo   saml        - Run only SAML tests
    echo   coverage    - Run all tests with coverage report
    echo.
    echo Examples:
    echo   %0 run               # Full test run
    echo   %0 run ldap          # Test only LDAP provider
    echo   %0 run coverage      # Run with coverage report
    echo   %0 start             # Start services for manual testing
    echo   %0 stop              # Stop all test services
    exit /b 1

:cleanup
    echo Cleaning up test containers...
    docker stop test_ldap test_oidc test_saml_idp >nul 2>&1
    docker rm test_ldap test_oidc test_saml_idp >nul 2>&1
    echo [OK] Cleanup complete
    echo.
    goto :eof

:start_services
    echo Starting test services...

    echo Starting LDAP...
    docker compose -f tests\fixtures\docker-compose.ldap.yml up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start LDAP service
        exit /b 1
    )

    echo Starting OIDC...
    docker compose -f tests\fixtures\docker-compose.oidc.yml up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start OIDC service
        exit /b 1
    )

    echo Starting SAML...
    docker compose -f tests\fixtures\docker-compose.saml.yml up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start SAML service
        exit /b 1
    )

    echo [OK] Services started
    echo.
    goto :eof

:wait_services
    echo Waiting for services to be ready...

    REM Wait for LDAP
    echo Waiting for LDAP...
    set timeout=30
    :wait_ldap
    docker exec test_ldap ldapsearch -x -H ldap://localhost:389 -b dc=example,dc=com -D "cn=admin,dc=example,dc=com" -w admin >nul 2>&1
    if not errorlevel 1 goto ldap_ready
    timeout /t 1 /nobreak >nul
    set /a timeout-=1
    if !timeout! gtr 0 goto wait_ldap
    echo [ERROR] LDAP service timeout
    exit /b 1
    :ldap_ready
    echo [OK] LDAP ready

    REM Wait for OIDC
    echo Waiting for OIDC...
    set timeout=30
    :wait_oidc
    curl -s http://localhost:8080/default/.well-known/openid-configuration >nul 2>&1
    if not errorlevel 1 goto oidc_ready
    timeout /t 1 /nobreak >nul
    set /a timeout-=1
    if !timeout! gtr 0 goto wait_oidc
    echo [ERROR] OIDC service timeout
    exit /b 1
    :oidc_ready
    echo [OK] OIDC ready

    REM Wait for SAML
    echo Waiting for SAML...
    set timeout=30
    :wait_saml
    curl -s http://localhost:8082/simplesaml/ >nul 2>&1
    if not errorlevel 1 goto saml_ready
    timeout /t 1 /nobreak >nul
    set /a timeout-=1
    if !timeout! gtr 0 goto wait_saml
    echo [ERROR] SAML service timeout
    exit /b 1
    :saml_ready
    echo [OK] SAML ready

    echo [OK] All services ready
    echo.
    goto :eof

:run_tests
    echo Running tests...
    echo.

    if "%TEST_TYPE%"=="ldap" (
        pytest tests\unit\auth\providers\test_ldap_provider.py tests\integration\auth\test_ldap_integration.py -v
    ) else if "%TEST_TYPE%"=="oidc" (
        pytest tests\unit\auth\providers\test_oidc_provider.py tests\integration\auth\test_oidc_integration.py -v
    ) else if "%TEST_TYPE%"=="saml" (
        pytest tests\unit\auth\providers\test_saml_provider.py tests\integration\auth\test_saml_integration.py -v
    ) else if "%TEST_TYPE%"=="unit" (
        pytest tests\unit\auth\providers\ -v -m "not integration"
    ) else if "%TEST_TYPE%"=="integration" (
        pytest tests\integration\auth\ -v -m integration
    ) else if "%TEST_TYPE%"=="coverage" (
        pytest tests\unit\auth\providers\ tests\integration\auth\ --cov=src\sark\services\auth\providers --cov-report=html --cov-report=term-missing -v
    ) else (
        pytest tests\unit\auth\providers\ tests\integration\auth\ -v
    )

    set TEST_RESULT=!errorlevel!
    echo.

    if !TEST_RESULT! equ 0 (
        echo [OK] Tests passed
    ) else (
        echo [ERROR] Tests failed
    )

    exit /b !TEST_RESULT!

endlocal
