#!/usr/bin/env python
"""QueueCTL entry point script."""
import logging
import sys
from queue.cli import CLI

def main():
    """Main entry point."""
    # Configure logging to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('queuectl.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    try:
        cli = CLI()
        cli.run()
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()