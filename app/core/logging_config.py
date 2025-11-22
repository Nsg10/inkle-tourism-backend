# app/core/logging_config.py

import logging

# Create a logger for our application
logger = logging.getLogger("inkle_tourism_agent")

# Set log level
logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
