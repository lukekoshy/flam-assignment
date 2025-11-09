"""Fixed demo script for Windows PowerShell compatibility."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

def run_command(cmd):
    """Run queuectl command and return output."""
    result = subprocess.run(
        f'python queuectl.py {cmd}',
        shell=True,
        capture_output=True,
        text=True
    )
    print(f"Command: {cmd}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
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
    run_command(f'enqueue \'{json.dumps(job)}\'')
    
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
    run_command("status")
    run_command("list --state completed")

    # Test 2: Failed job with retry
    print("\n2. Testing failed job with retry...")
    job = {
        "id": "job2",
        "command": "nonexistent_command"
    }
    run_command(f'enqueue \'{json.dumps(job)}\'')
    
    # Wait for retries and DLQ
    time.sleep(5)
    print("\nChecking DLQ...")
    run_command("dlq list")

    # Test 3: Multiple workers
    print("\n3. Testing multiple workers...")
    worker_process.terminate()
    worker_process.wait()
    
    # Enqueue multiple jobs
    for i in range(3):
        job = {
            "id": f"multi{i}",
            "command": f"echo Job {i} && timeout 2"
        }
        run_command(f'enqueue \'{json.dumps(job)}\'')
    
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
    run_command("status")
    run_command("list --state completed")
    
    # Clean up
    worker_process.terminate()
    worker_process.wait()
    
    print("\nDemo completed!")

if __name__ == "__main__":
    main()