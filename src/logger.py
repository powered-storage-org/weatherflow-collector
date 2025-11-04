# logger.py

"""
Logging Configuration Module

This module provides a centralized configuration for logging across the application.
It uses fmtlog structured logging format that outputs logs as key=value pairs for
better machine readability and parsing.

Key Features:
- FmtlogFormatter: A custom logging formatter that outputs logs in fmtlog format
  (ts=... level=... msg=... key=value).
- configure_logging: A function to configure the root logger with custom settings,
  including setting the log level, adding a console handler with the fmtlog formatter,
  and setting up a file handler for logging to a file with a daily rotation.

The fmtlog format enhances machine readability and allows for easy parsing and filtering
of log messages. The module ensures that all parts of the application use a consistent
logging format and level.

Usage:
The module is used to configure the logging at the start of the application. It sets
up handlers for both console and file outputs, applying the fmtlog formatter to both.
The file handler writes logs to a file with the current date in its filename, allowing
for easier log management and review.

Dependencies:
- datetime: Used for timestamp formatting and generating log file names.
- os: Used for creating the log directory if it does not exist.
- config: Configuration module containing settings like log levels and log directory path.

Author: Dave Schmid
Created: 2023-12-17
Updated: 2025-01-XX - Changed to fmtlog structured logging format
"""
import config
from datetime import datetime, timezone
import inspect
import logging
import os
import time

# Custom Formatter to output logs in fmtlog structured format
class FmtlogFormatter(logging.Formatter):
    """Formatter that outputs logs in fmtlog structured format: ts=... level=... msg=... key=value"""
    
    LEVEL_MAPPING = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }
    
    def __init__(self):
        super().__init__()
    
    def _escape_value(self, value):
        """Escape and quote values if they contain spaces or special characters"""
        if value is None:
            return None
        value_str = str(value)
        # If value contains spaces, quotes, or equals sign, quote and escape it
        if any(c in value_str for c in [' ', '=', '"', '\n', '\t']):
            # Escape quotes and backslashes
            escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        return value_str
    
    def _should_include_field(self, key, value):
        """Determine if a field should be included in the log output"""
        # Skip empty strings and None values
        if value is None or value == "":
            return False
        # Skip certain fields that are typically empty or not useful
        if key in ['taskName'] and (value == "" or value is None):
            return False
        return True
    
    def format(self, record):
        # Format timestamp in ISO 8601 format with nanoseconds (UTC)
        # Use time.time_ns() for nanosecond precision if available (Python 3.7+)
        try:
            ns = time.time_ns()
            seconds = ns // 1_000_000_000
            nanoseconds = ns % 1_000_000_000
            dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
            timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S') + f".{nanoseconds:09d}Z"
        except AttributeError:
            # Fallback for older Python versions
            dt = datetime.now(timezone.utc)
            microseconds = dt.microsecond
            timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S') + f".{microseconds:06d}000Z"
        
        # Get lowercase log level
        level = self.LEVEL_MAPPING.get(record.levelno, record.levelname.lower())
        
        # Build the base log line: ts=... level=... msg=...
        parts = [
            f"ts={timestamp}",
            f"level={level}",
            f'msg={self._escape_value(record.getMessage())}'
        ]
        
        # Add module name
        parts.append(f"module={self._escape_value(record.name)}")
        
        # Add function name if available
        if record.funcName:
            parts.append(f"func={self._escape_value(record.funcName)}")
        
        # Add line number if available
        if record.lineno:
            parts.append(f"line={record.lineno}")
        
        # Add pathname if available (skip if empty)
        if record.pathname and self._should_include_field('pathname', record.pathname):
            escaped_pathname = self._escape_value(record.pathname)
            if escaped_pathname:
                parts.append(f"pathname={escaped_pathname}")
        
        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            # Skip standard logging fields
            if key in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                continue
            # Only include non-empty fields
            if self._should_include_field(key, value):
                escaped_value = self._escape_value(value)
                if escaped_value is not None:
                    parts.append(f"{key}={escaped_value}")
        
        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            parts.append(f"error={self._escape_value(exc_text)}")
        
        return " ".join(parts)


def get_log_level_for_module(module_name, log_levels, default_level="DEBUG"):
    parts = module_name.split(".")
    for i in range(len(parts), 0, -1):
        name_to_check = ".".join(parts[:i])
        if name_to_check in log_levels:
            return log_levels[name_to_check]
    return default_level


def configure_logging():
    # Configure root logger
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()  # Clear existing handlers
    logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

    # Console logging configuration
    console_enabled = config.WEATHERFLOW_COLLECTOR_LOGGER_CONSOLE_ENABLED
    if console_enabled:
        console_formatter = FmtlogFormatter()
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

    # File logging configuration
    file_enabled = config.WEATHERFLOW_COLLECTOR_LOGGER_FILE_ENABLED
    if file_enabled:
        file_formatter = FmtlogFormatter()
        log_directory = config.WEATHERFLOW_COLLECTOR_LOG_DIRECTORY
        os.makedirs(log_directory, exist_ok=True)
        log_file_name = f"application_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_file_path = os.path.join(log_directory, log_file_name)
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)


def get_module_logger(name=None):
    if name is None:
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module is not None else "__main__"

    module_logger = logging.getLogger(name)
    module_logger.propagate = False

    # Add console handler based on config
    if config.WEATHERFLOW_COLLECTOR_LOGGER_CONSOLE_ENABLED:
        console_handler_exists = any(
            isinstance(handler, logging.StreamHandler)
            for handler in module_logger.handlers
        )
        if not console_handler_exists:
            console_level_name = get_log_level_for_module(
                name, config.WEATHERFLOW_COLLECTOR_CONSOLE_LOG_LEVELS, "INFO"
            )
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(FmtlogFormatter())
            console_handler.setLevel(getattr(logging, console_level_name))
            module_logger.addHandler(console_handler)

    # Add file handler based on config
    if config.WEATHERFLOW_COLLECTOR_LOGGER_FILE_ENABLED:
        file_handler_exists = any(
            isinstance(handler, logging.FileHandler)
            for handler in module_logger.handlers
        )
        if not file_handler_exists:
            file_level_name = get_log_level_for_module(
                name, config.WEATHERFLOW_COLLECTOR_FILE_LOG_LEVELS, "DEBUG"
            )
            log_directory = config.WEATHERFLOW_COLLECTOR_LOG_DIRECTORY
            os.makedirs(log_directory, exist_ok=True)
            log_file_name = f"{name}.log"
            log_file_path = os.path.join(log_directory, log_file_name)
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(FmtlogFormatter())
            file_handler.setLevel(getattr(logging, file_level_name))
            module_logger.addHandler(file_handler)

    return module_logger


# Call configure_logging to set up the logging environment
configure_logging()
