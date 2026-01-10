"""
Retry utility with exponential backoff for network operations.

This module provides decorator-based retry functionality with exponential backoff,
useful for handling transient network errors and API rate limits.
"""
import time
import logging
from typing import Callable, TypeVar, Optional, Tuple, List
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.
    
    This decorator automatically retries a function when it raises specified exceptions,
    using exponential backoff to gradually increase delay between retries. Useful for
    handling transient network errors, API rate limits, and temporary service unavailability.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3).
                   Total attempts = max_retries + 1 (initial attempt + retries).
        initial_delay: Initial delay in seconds before first retry (default: 1.0).
                      Delay doubles (or uses exponential_base) with each retry.
        max_delay: Maximum delay in seconds between retries (default: 60.0).
                  Prevents excessive delays for very high retry counts.
        exponential_base: Base for exponential backoff calculation (default: 2.0).
                         Delay = initial_delay * (exponential_base ^ attempt_number).
        exceptions: Tuple of exception types to catch and retry on (default: (Exception,)).
                   Only these exception types trigger retries; other exceptions are re-raised.
        on_retry: Optional callback function(exception, attempt_number) called on each retry.
                If None, logs a warning message automatically.
                Useful for custom logging or metrics collection.
    
    Returns:
        Decorated function that automatically retries on specified exceptions.
        The decorated function has the same signature as the original function.
    
    Raises:
        The last exception raised if all retry attempts fail.
    
    Example:
        >>> @retry_with_backoff(max_retries=3, initial_delay=1.0)
        ... def download_file(url):
        ...     return requests.get(url).content
        >>> 
        >>> # Will retry up to 3 times with delays: 1s, 2s, 4s
        >>> content = download_file("https://example.com/file")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        if on_retry:
                            on_retry(e, attempt + 1)
                        else:
                            logger.warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                f"Retrying in {delay:.1f} seconds..."
                            )
                        
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator

