"""Worker process management and job execution."""
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from threading import Event, Thread
from typing import Optional, Dict, List

from .db import Database

logger = logging.getLogger(__name__)

class Worker:
    """Individual worker process that executes jobs."""
    
    def __init__(self, db: Database):
        """Initialize worker with database connection."""
        self.db = db
        self.id = str(uuid.uuid4())
        self.stop_event = Event()
        self.current_job: Optional[Dict] = None

    def start(self):
        """Start the worker loop."""
        logger.info(f"Worker {self.id} starting")
        
        while not self.stop_event.is_set():
            try:
                # Try to get and lock a job
                job = self.db.fetch_and_lock_job(self.id)
                if not job:
                    # No jobs available, wait a bit
                    time.sleep(1)
                    continue

                self.current_job = job
                self._process_job(job)
                self.current_job = None
                
            except Exception as e:
                logger.error(f"Worker {self.id} error: {e}")
                time.sleep(1)

        logger.info(f"Worker {self.id} stopped")

    def stop(self):
        """Signal the worker to stop after current job."""
        logger.info(f"Worker {self.id} stopping...")
        self.stop_event.set()

    def _process_job(self, job: Dict):
        """Process a single job with retries and backoff."""
        logger.info(f"Processing job {job['id']}")
        
        try:
            # Execute the command
            process = subprocess.run(
                job["command"],
                shell=True,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                # Success
                self.db.update_job_state(
                    job_id=job["id"],
                    state="completed",
                    worker_id=None
                )
            else:
                # Command failed
                self._handle_failure(
                    job,
                    f"Command failed with exit code {process.returncode}: {process.stderr}"
                )
                
        except Exception as e:
            # System error
            self._handle_failure(job, str(e))

    def _handle_failure(self, job: Dict, error: str):
        """Handle job failure with retry logic."""
        self.db.update_job_state(
            job_id=job["id"],
            state="failed",
            error=error,
            worker_id=None,
            increment_attempts=True
        )
        
        # Check if we should move to DLQ
        if job["attempts"] + 1 >= job["max_retries"]:
            self.db.move_to_dlq(job["id"], error)
            return
            
        # Calculate next retry time with exponential backoff
        base = self.db.get_config("backoff_base", 2)
        delay = base ** (job["attempts"] + 1)  # exponential backoff
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)
        
        self.db.set_next_retry(job["id"], next_retry.isoformat())

class WorkerManager:
    """Manages multiple worker processes."""
    
    def __init__(self, db: Database):
        """Initialize worker manager."""
        self.db = db
        self.workers: List[Worker] = []
        self.worker_threads: List[Thread] = []
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start_workers(self, count: int = 1):
        """Start the specified number of worker processes."""
        for _ in range(count):
            worker = Worker(self.db)
            thread = Thread(target=worker.start)
            
            self.workers.append(worker)
            self.worker_threads.append(thread)
            thread.start()

    def stop_workers(self):
        """Stop all workers gracefully."""
        logger.info("Stopping all workers...")
        
        # Signal all workers to stop
        for worker in self.workers:
            worker.stop()
            
        # Wait for all threads to finish
        for thread in self.worker_threads:
            thread.join()
            
        self.workers = []
        self.worker_threads = []
        
        logger.info("All workers stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.stop_workers()
        sys.exit(0)