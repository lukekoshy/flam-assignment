"""Command-line interface for the job queue system."""
import argparse
import json
import logging
import sys
import uuid
from typing import Optional

from .db import Database
from .worker import WorkerManager

logger = logging.getLogger(__name__)

class CLI:
    """CLI handler for the queue system."""
    
    def __init__(self):
        """Initialize CLI with database connection."""
        self.db = Database()
        self.worker_manager = WorkerManager(self.db)

    def run(self):
        """Parse and handle CLI commands."""
        parser = argparse.ArgumentParser(
            description="QueueCTL - Background Job Queue System"
        )
        subparsers = parser.add_subparsers(dest="command", help="Commands")

        # Enqueue command
        enqueue_parser = subparsers.add_parser("enqueue", help="Add a new job to the queue")
        enqueue_parser.add_argument("job_json", help="Job specification as JSON string")

        # Worker commands
        worker_parser = subparsers.add_parser("worker", help="Worker management")
        worker_subparsers = worker_parser.add_subparsers(dest="worker_command")
        
        worker_start = worker_subparsers.add_parser("start", help="Start worker processes")
        worker_start.add_argument(
            "--count",
            type=int,
            default=1,
            help="Number of workers to start"
        )
        
        worker_subparsers.add_parser("stop", help="Stop all workers")

        # Status command
        subparsers.add_parser("status", help="Show queue status")

        # List jobs command
        list_parser = subparsers.add_parser("list", help="List jobs")
        list_parser.add_argument(
            "--state",
            choices=["pending", "processing", "completed", "failed", "dead"],
            help="Filter by job state"
        )

        # DLQ commands
        dlq_parser = subparsers.add_parser("dlq", help="Dead Letter Queue operations")
        dlq_subparsers = dlq_parser.add_subparsers(dest="dlq_command")
        
        dlq_subparsers.add_parser("list", help="List jobs in DLQ")
        
        dlq_retry = dlq_subparsers.add_parser("retry", help="Retry a job from DLQ")
        dlq_retry.add_argument("job_id", help="ID of the job to retry")

        # Config commands
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_subparsers = config_parser.add_subparsers(dest="config_command")
        
        config_set = config_subparsers.add_parser("set", help="Set config value")
        config_set.add_argument("key", help="Config key")
        config_set.add_argument("value", help="Config value")
        
        config_get = config_subparsers.add_parser("get", help="Get config value")
        config_get.add_argument("key", help="Config key")

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(1)

        try:
            # Route to appropriate handler
            if args.command == "enqueue":
                self._handle_enqueue(args)
            elif args.command == "worker":
                self._handle_worker(args)
            elif args.command == "status":
                self._handle_status()
            elif args.command == "list":
                self._handle_list(args)
            elif args.command == "dlq":
                self._handle_dlq(args)
            elif args.command == "config":
                self._handle_config(args)
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)

    def _handle_enqueue(self, args):
        """Handle job enqueue command."""
        try:
            job_data = json.loads(args.job_json)
            if "id" not in job_data:
                job_data["id"] = str(uuid.uuid4())
            if "command" not in job_data:
                raise ValueError("Job must include 'command' field")
                
            if self.db.enqueue(job_data):
                print(f"Job {job_data['id']} enqueued successfully")
            else:
                print(f"Failed to enqueue job (ID may already exist)")
                sys.exit(1)
                
        except json.JSONDecodeError:
            print("Error: Invalid JSON format")
            sys.exit(1)
        except Exception as e:
            print(f"Error enqueueing job: {e}")
            sys.exit(1)

    def _handle_worker(self, args):
        """Handle worker management commands."""
        if args.worker_command == "start":
            try:
                self.worker_manager.start_workers(args.count)
                print(f"Started {args.count} worker(s)")
            except Exception as e:
                print(f"Error starting workers: {e}")
                sys.exit(1)
        elif args.worker_command == "stop":
            try:
                self.worker_manager.stop_workers()
                print("Workers stopped")
            except Exception as e:
                print(f"Error stopping workers: {e}")
                sys.exit(1)

    def _handle_status(self):
        """Show queue status."""
        try:
            stats = {
                "pending": len(self.db.list_jobs("pending")),
                "processing": len(self.db.list_jobs("processing")),
                "completed": len(self.db.list_jobs("completed")),
                "failed": len(self.db.list_jobs("failed")),
                "dead": len(self.db.list_jobs("dead"))
            }
            
            print("\nQueue Status:")
            print("-" * 40)
            for state, count in stats.items():
                print(f"{state.capitalize():12} : {count}")
            
            # Show processing jobs with more detail
            processing_jobs = self.db.list_jobs("processing")
            if processing_jobs:
                print("\nCurrently Processing Jobs:")
                for job in processing_jobs:
                    print(f"- Job {job['id']} (Worker: {job['worker_id']})")
            
            print("-" * 40)
            
        except Exception as e:
            print(f"Error getting status: {e}")
            sys.exit(1)

    def _handle_list(self, args):
        """Handle job listing command."""
        try:
            jobs = self.db.list_jobs(args.state)
            if not jobs:
                print("No jobs found")
                return
                
            print("\nJobs:")
            print("-" * 80)
            for job in jobs:
                print(
                    f"ID: {job['id']}\n"
                    f"Command: {job['command']}\n"
                    f"State: {job['state']}\n"
                    f"Attempts: {job['attempts']}/{job['max_retries']}\n"
                    f"Created: {job['created_at']}\n"
                    f"Updated: {job['updated_at']}\n"
                    f"{'-' * 80}"
                )
                
        except Exception as e:
            print(f"Error listing jobs: {e}")
            sys.exit(1)

    def _handle_dlq(self, args):
        """Handle DLQ operations."""
        if not args.dlq_command:
            print("Error: DLQ command required")
            sys.exit(1)
            
        try:
            if args.dlq_command == "list":
                jobs = self.db.list_jobs("dead")
                if not jobs:
                    print("DLQ is empty")
                    return
                    
                print("\nDead Letter Queue:")
                print("-" * 80)
                for job in jobs:
                    print(
                        f"ID: {job['id']}\n"
                        f"Command: {job['command']}\n"
                        f"Error: {job['last_error']}\n"
                        f"Attempts: {job['attempts']}/{job['max_retries']}\n"
                        f"{'-' * 80}"
                    )
            
            elif args.dlq_command == "retry":
                if self.db.retry_dlq_job(args.job_id):
                    print(f"Job {args.job_id} moved back to pending queue")
                else:
                    print(f"Failed to retry job {args.job_id}")
                    sys.exit(1)
                    
        except Exception as e:
            print(f"Error in DLQ operation: {e}")
            sys.exit(1)

    def _handle_config(self, args):
        """Handle configuration commands."""
        if not args.config_command:
            print("Error: Config command required")
            sys.exit(1)
            
        try:
            if args.config_command == "set":
                # Try to parse value as JSON for proper typing
                try:
                    value = json.loads(args.value)
                except json.JSONDecodeError:
                    value = args.value
                    
                if self.db.set_config(args.key, value):
                    print(f"Config {args.key} set to {value}")
                else:
                    print(f"Failed to set config {args.key}")
                    sys.exit(1)
                    
            elif args.config_command == "get":
                value = self.db.get_config(args.key)
                if value is not None:
                    print(f"{args.key}: {value}")
                else:
                    print(f"No value set for {args.key}")
                    
        except Exception as e:
            print(f"Error in config operation: {e}")
            sys.exit(1)