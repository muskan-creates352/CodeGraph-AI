def format_log_entry(level: str, message: str) -> str:
    """Format a log line with a level prefix."""
    return f"[{level.upper()}] {message}"


def log_info(message: str) -> None:
    """Log an info message."""
    entry = format_log_entry("info", message)
    print(entry)


def log_error(message: str) -> None:
    """Log an error message."""
    entry = format_log_entry("error", message)
    print(entry)
