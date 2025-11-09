#!/usr/bin/env python
"""QueueCTL entry point script."""
import logging
from queue.cli import CLI

def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    main()