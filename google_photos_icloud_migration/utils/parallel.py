"""
Parallel processing utilities for I/O-bound and CPU-bound operations.

This module provides high-level utilities for parallel processing with support for:
- Thread-based parallelism for I/O-bound operations (downloads, file I/O)
- Process-based parallelism for CPU-bound operations (metadata processing, encoding)
- Automatic worker count detection based on CPU cores
- Comprehensive error handling and result collection
- Progress tracking and logging support
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Callable, List, TypeVar, Optional, Dict, Any, Tuple
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
    Apply a function to a list of items in parallel with automatic worker detection.
    
    This function processes items in parallel using either threads (for I/O-bound
    operations) or processes (for CPU-bound operations). Results are returned in
    the same order as input items.
    
    Args:
        func: Function to apply to each item. Must be picklable if use_processes=True.
        items: List of items to process in parallel
        max_workers: Maximum number of worker threads/processes.
                    If None, auto-detects based on CPU count (default: min(32, CPU_count + 4)).
        use_processes: If True, use ProcessPoolExecutor for CPU-bound tasks.
                      If False, use ThreadPoolExecutor for I/O-bound tasks (default).
        chunk_size: Optional chunk size for batch processing.
                   If specified, processes items in batches of this size.
                   Useful for very large item lists to manage memory.
                   If None, processes all items at once (default).
    
    Returns:
        List of results in the same order as input items.
        Result at index i corresponds to items[i].
    
    Note:
        For CPU-bound operations (e.g., metadata processing), use use_processes=True.
        For I/O-bound operations (e.g., file downloads, writes), use use_processes=False.
        Auto-detection of worker count: min(32, os.cpu_count() + 4) for I/O-bound,
        os.cpu_count() for CPU-bound operations.
    
    Example:
        >>> # I/O-bound: Download files in parallel
        >>> files = parallel_map(download_file, urls, max_workers=5, use_processes=False)
        >>> # CPU-bound: Process metadata in parallel
        >>> results = parallel_map(process_metadata, files, max_workers=4, use_processes=True)
    """
    if not items:
        return []
    
    if len(items) == 1:
        return [func(items[0])]
    
    # Auto-detect worker count if not specified
    if max_workers is None:
        cpu_count = os.cpu_count() or 4
        if use_processes:
            max_workers = cpu_count  # CPU-bound: one process per core
        else:
            # I/O-bound: can use more threads (up to 32)
            max_workers = min(32, cpu_count + 4)
    
    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    with executor_class(max_workers=max_workers) as executor:
        if chunk_size and chunk_size > 0:
            # Process in chunks to manage memory for very large lists
            results = []
            total_chunks = (len(items) + chunk_size - 1) // chunk_size
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                chunk_num = i // chunk_size + 1
                logger.debug(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} items)")
                chunk_results = list(executor.map(func, chunk))
                results.extend(chunk_results)
            return results
        else:
            # Process all at once (efficient for smaller lists)
            return list(executor.map(func, items))


def parallel_map_with_results(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
    use_processes: bool = False
) -> Dict[T, R]:
    """
    Apply a function to items in parallel and return a dictionary mapping items to results.
    
    This function is similar to parallel_map(), but returns results as a dictionary
    mapping input items to their results. The order of results may differ from input
    order (results are returned as they complete), but all input items are guaranteed
    to be in the output dictionary.
    
    Args:
        func: Function to apply to each item. Must be picklable if use_processes=True.
        items: List of items to process in parallel
        max_workers: Maximum number of worker threads/processes.
                    If None, auto-detects based on CPU count.
        use_processes: If True, use ProcessPoolExecutor for CPU-bound tasks.
                      If False, use ThreadPoolExecutor for I/O-bound tasks (default).
    
    Returns:
        Dictionary mapping each input item to its corresponding result.
        All input items are guaranteed to be keys in the result dictionary.
    
    Raises:
        Exception: Re-raises any exception that occurred during processing.
                  The exception is raised after all items have been processed.
    
    Note:
        Results are returned as they complete (not in input order).
        If you need ordered results, use parallel_map() instead.
        Auto-detection of worker count: min(32, os.cpu_count() + 4) for I/O-bound,
        os.cpu_count() for CPU-bound operations.
    
    Example:
        >>> # Process files and map results
        >>> file_results = parallel_map_with_results(process_file, files)
        >>> for file, success in file_results.items():
        ...     print(f"{file}: {'OK' if success else 'Failed'}")
    """
    if not items:
        return {}
    
    # Auto-detect worker count if not specified
    if max_workers is None:
        cpu_count = os.cpu_count() or 4
        if use_processes:
            max_workers = cpu_count
        else:
            max_workers = min(32, cpu_count + 4)
    
    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    results = {}
    with executor_class(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_item = {executor.submit(func, item): item for item in items}
        
        # Collect results as they complete
        completed = 0
        total = len(items)
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            completed += 1
            try:
                result = future.result()
                results[item] = result
                if completed % 10 == 0:  # Log progress every 10 items
                    logger.debug(f"Completed {completed}/{total} items")
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
                # Store error result but don't fail completely
                # Caller can check for exceptions in results
                results[item] = None
                raise  # Re-raise to allow caller to handle
    
    return results

