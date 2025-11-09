@echo off
echo Testing QueueCTL System...

REM Clean up any existing database
if exist jobs.db del jobs.db

REM Test 1: Simple job
echo.
echo Test 1: Running simple job...
python queuectl.py enqueue "{\"id\":\"test1\",\"command\":\"echo Hello World\"}"

REM Start worker
echo.
echo Starting worker...
start /B python queuectl.py worker start

REM Wait a bit
timeout /t 2 /nobreak > nul

REM Check status
echo.
echo Checking status...
python queuectl.py status

REM Test 2: Failed job
echo.
echo Test 2: Testing failed job...
python queuectl.py enqueue "{\"id\":\"test2\",\"command\":\"nonexistent_cmd\"}"

REM Wait for retries
timeout /t 5 /nobreak > nul

REM Check DLQ
echo.
echo Checking DLQ...
python queuectl.py dlq list

REM Stop worker
echo.
echo Stopping worker...
python queuectl.py worker stop

echo.
echo Test completed!