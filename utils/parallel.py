"""
Parallel processing utilities for I/O-bound and CPU-bound operations.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Callable, List, TypeVar, Optional, Dict, Any
from functools import wraps
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


def parallel_map(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
    use_processes: bool = False,
    chunk_size: Optional[int] = None
) -> List[R]:
    """
    Apply a function to a list of items in parallel.
    
    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of worker threads/processes (None = auto)
        use_processes: If True, use processes instead of threads (for CPU-bound tasks)
        chunk_size: Optional chunk size for processing (None = process all at once)
    
    Returns:
        List of results in the same order as input items
    """
    if not items:
        return []
    
    if len(items) == 1:
        return [func(items[0])]
    
    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    with executor_class(max_workers=max_workers) as executor:
        if chunk_size:
            # Process in chunks
            results = []
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                chunk_results = list(executor.map(func, chunk))
                results.extend(chunk_results)
            return results
        else:
            # Process all at once
            return list(executor.map(func, items))


def parallel_map_with_results(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
    use_processes: bool = False
) -> Dict[T, R]:
    """
    Apply a function to items in parallel and return a dictionary mapping items to results.
    
    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of worker threads/processes
        use_processes: If True, use processes instead of threads
    
    Returns:
        Dictionary mapping input items to their results
    """
    if not items:
        return {}
    
    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    results = {}
    with executor_class(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(func, item): item for item in items}
        
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                results[item] = future.result()
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
                raise
    
    return results

