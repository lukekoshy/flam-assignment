# QueueCTL - Background Job Queue System

A production-grade CLI-based background job queue system that manages jobs with worker processes, handles retries using exponential backoff, and maintains a Dead Letter Queue (DLQ) for permanently failed jobs.

## Features

- ✅ Job enqueuing and management via CLI
- ✅ Multiple worker processes with safe concurrent execution
- ✅ Automatic retries with exponential backoff
- ✅ Dead Letter Queue (DLQ) for failed jobs
- ✅ Persistent SQLite storage
- ✅ Configurable retry and backoff settings
- ✅ Clean CLI interface with comprehensive help

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/lukekoshy/flam-assignment.git
cd flam-assignment
```

2. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage Examples

### 1. Enqueue a Job

```bash
# Simple job (Linux/Mac)
python queuectl.py enqueue '{"id":"job1", "command":"echo Hello World"}'

# Simple job (Windows CMD)
python queuectl.py enqueue "{\"id\":\"job1\", \"command\":\"echo Hello World\"}"

# Job with custom retry settings (Linux/Mac)
python queuectl.py enqueue '{"id":"job2", "command":"sleep 5", "max_retries":5}'

# Job with custom retry settings (Windows CMD)
python queuectl.py enqueue "{\"id\":\"job2\", \"command\":\"sleep 5\", \"max_retries\":5}"
```

### 2. Manage Workers

```bash
# Start 3 worker processes
python queuectl.py worker start --count 3

# Stop all workers gracefully
python queuectl.py worker stop
```

### 3. Monitor Jobs

```bash
# Show queue status
python queuectl.py status

# List all pending jobs
python queuectl.py list --state pending

# View Dead Letter Queue
python queuectl.py dlq list
```

### 4. Configure Settings

```bash
# Set retry backoff base
python queuectl.py config set backoff_base 2

# Set default max retries
python queuectl.py config set default_max_retries 3
```

## Architecture Overview

### Components

1. **CLI Interface** (`cli.py`)
   - Handles command parsing and user interaction
   - Provides clean interface for all operations

2. **Database Layer** (`db.py`)
   - SQLite-based persistent storage
   - Handles job state transitions
   - Manages configuration

3. **Worker System** (`worker.py`)
   - Manages multiple worker processes
   - Handles job execution and retries
   - Implements exponential backoff
   - Provides graceful shutdown

### Job Lifecycle

1. Jobs start in `pending` state
2. Workers pick up and move to `processing`
3. Successful jobs move to `completed`
4. Failed jobs move to `failed` and retry with backoff
5. Jobs exceeding max retries move to `dead` (DLQ)

### Data Persistence

- Uses SQLite for robust, file-based storage
- Maintains job state across system restarts
- Prevents duplicate processing with locking
- Stores configuration values

## Assumptions & Trade-offs

1. **SQLite Choice**
   - Pros: Simple, reliable, no external dependencies
   - Cons: May not scale to extremely high throughput

2. **Process-based Workers**
   - Pros: True parallelism, isolation
   - Cons: Higher resource overhead than threads

3. **File-based Locking**
   - Pros: Simple, works across processes
   - Cons: Potential performance impact

4. **Shell Command Execution**
   - Pros: Flexible, supports any command
   - Cons: Security considerations for untrusted input

## Testing Instructions

1. Run the demo script to validate core flows:
```bash
python run_demo.py
```

This will test:
- Basic job execution
- Failed job retry mechanism
- Multiple worker processing
- DLQ functionality

2. Manual testing scenarios:

```bash
# 1. Test successful job
python queuectl.py enqueue '{"id":"test1","command":"echo Success"}'

# 2. Test failed job
python queuectl.py enqueue '{"id":"test2","command":"nonexistent_cmd"}'

# 3. Test multiple workers
python queuectl.py worker start --count 3
python queuectl.py enqueue '{"id":"multi1","command":"sleep 2"}'
python queuectl.py enqueue '{"id":"multi2","command":"sleep 2"}'
python queuectl.py status

# 4. Test DLQ retry
python queuectl.py dlq list
python queuectl.py dlq retry test2
```

## Recording

[Demo Video](https://drive.google.com/file/d/1bwl6uBL7HwsAc-iRgHRzcpPMDJA8ggjJ/view?usp=drive_link)
