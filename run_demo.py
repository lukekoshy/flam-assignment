"""Demo script to validate core functionality."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

def run_command(cmd):
    """Run queuectl command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def main():
    """Run demo scenarios."""
    print("\n=== QueueCTL Demo ===\n")

    # Ensure we start fresh
    if os.path.exists("jobs.db"):
        os.remove("jobs.db")

    # Test 1: Basic successful job
    print("\n1. Testing basic successful job...")
    job = {
        "id": "job1",
        "command": "echo Hello World"
    }
    run_command(f'python queuectl.py enqueue \'{json.dumps(job)}\'')
    
    # Start worker
    print("\nStarting worker...")
    worker_process = subprocess.Popen(
        ["python", "queuectl.py", "worker", "start"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for job to complete
    time.sleep(2)
    print("\nChecking job status...")
    print(run_command("python queuectl.py list"))

    # Test 2: Failed job with retry
    print("\n2. Testing failed job with retry...")
    job = {
        "id": "job2",
        "command": "nonexistent_command",
        "max_retries": 2
    }
    run_command(f'python queuectl.py enqueue \'{json.dumps(job)}\'')
    
    # Wait for retries and DLQ
    time.sleep(5)
    print("\nChecking DLQ...")
    print(run_command("python queuectl.py dlq list"))

    # Test 3: Multiple workers
    print("\n3. Testing multiple workers...")
    # Stop existing worker
    worker_process.terminate()
    worker_process.wait()
    
    # Enqueue multiple jobs
    for i in range(3):
        job = {
            "id": f"multi{i}",
            "command": f"echo Job {i} && sleep 2"
        }
        run_command(f'python queuectl.py enqueue \'{json.dumps(job)}\'')
    
    # Start multiple workers
    print("\nStarting 3 workers...")
    worker_process = subprocess.Popen(
        ["python", "queuectl.py", "worker", "start", "--count", "3"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for jobs to complete
    time.sleep(4)
    print("\nFinal status:")
    print(run_command("python queuectl.py status"))
    
    # Clean up
    worker_process.terminate()
    worker_process.wait()
    
    print("\nDemo completed!")

if __name__ == "__main__":
    main()