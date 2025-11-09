#!/bin/bash

# Exit on error
set -e

# Test successful job
echo "Testing successful job..."
python queuectl.py enqueue '{"id":"success1", "command":"echo Success"}'

# Start worker
echo "Starting worker..."
python queuectl.py worker start --count 1 &
WORKER_PID=$!

# Wait for job to complete
sleep 2
python queuectl.py status

# Test failed job
echo -e "\nTesting failed job..."
python queuectl.py enqueue '{"id":"fail1", "command":"nonexistent_cmd"}'
sleep 5

# Check DLQ
echo -e "\nChecking DLQ..."
python queuectl.py dlq list

# Stop worker
kill $WORKER_PID

echo -e "\nTests completed!"