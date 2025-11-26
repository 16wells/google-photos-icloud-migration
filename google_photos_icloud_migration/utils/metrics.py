"""
Metrics tracking for migration operations.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a single processing stage."""
    stage_name: str
    start_time: float
    end_time: Optional[float] = None
    items_processed: int = 0
    items_successful: int = 0
    items_failed: int = 0
    bytes_processed: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        total = self.items_processed
        if total == 0:
            return 0.0
        return (self.items_successful / total) * 100
    
    @property
    def throughput(self) -> float:
        """Get throughput in items per second."""
        duration = self.duration
        if duration == 0:
            return 0.0
        return self.items_processed / duration
    
    @property
    def speed_mbps(self) -> float:
        """Get processing speed in MB/s."""
        duration = self.duration
        if duration == 0:
            return 0.0
        mb_processed = self.bytes_processed / (1024 * 1024)
        return mb_processed / duration
    
    def finish(self):
        """Mark stage as finished."""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            'stage_name': self.stage_name,
            'duration_seconds': self.duration,
            'items_processed': self.items_processed,
            'items_successful': self.items_successful,
            'items_failed': self.items_failed,
            'bytes_processed': self.bytes_processed,
            'success_rate_percent': self.success_rate,
            'throughput_items_per_sec': self.throughput,
            'speed_mbps': self.speed_mbps,
            'error_count': len(self.errors),
        }


class MetricsTracker:
    """Tracks metrics across all migration stages."""
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.stages: Dict[str, StageMetrics] = {}
        self.current_stage: Optional[str] = None
        self.start_time = time.time()
    
    def start_stage(self, stage_name: str) -> None:
        """Start tracking a new stage."""
        if self.current_stage:
            self.finish_stage()
        
        self.current_stage = stage_name
        self.stages[stage_name] = StageMetrics(
            stage_name=stage_name,
            start_time=time.time()
        )
        logger.info(f"Starting stage: {stage_name}")
    
    def finish_stage(self) -> Optional[StageMetrics]:
        """Finish tracking the current stage."""
        if not self.current_stage:
            return None
        
        stage = self.stages[self.current_stage]
        stage.finish()
        logger.info(
            f"Finished stage: {self.current_stage} "
            f"({stage.items_processed} items, {stage.success_rate:.1f}% success, "
            f"{stage.duration:.1f}s)"
        )
        self.current_stage = None
        return stage
    
    def record_item(self, stage_name: Optional[str] = None, 
                   successful: bool = True, bytes_processed: int = 0) -> None:
        """Record processing of an item."""
        stage_name = stage_name or self.current_stage
        if not stage_name or stage_name not in self.stages:
            logger.warning(f"Attempted to record item for unknown stage: {stage_name}")
            return
        
        stage = self.stages[stage_name]
        stage.items_processed += 1
        if successful:
            stage.items_successful += 1
        else:
            stage.items_failed += 1
        stage.bytes_processed += bytes_processed
    
    def record_error(self, stage_name: Optional[str] = None, error: str = "") -> None:
        """Record an error in the current stage."""
        stage_name = stage_name or self.current_stage
        if stage_name and stage_name in self.stages:
            self.stages[stage_name].errors.append(error)
    
    def get_summary(self) -> Dict:
        """Get summary of all metrics."""
        total_duration = time.time() - self.start_time
        
        # Finish current stage if any
        if self.current_stage:
            self.finish_stage()
        
        stage_summaries = {
            name: stage.to_dict() for name, stage in self.stages.items()
        }
        
        total_items = sum(s.items_processed for s in self.stages.values())
        total_successful = sum(s.items_successful for s in self.stages.values())
        total_failed = sum(s.items_failed for s in self.stages.values())
        total_bytes = sum(s.bytes_processed for s in self.stages.values())
        
        return {
            'total_duration_seconds': total_duration,
            'total_items_processed': total_items,
            'total_items_successful': total_successful,
            'total_items_failed': total_failed,
            'total_bytes_processed': total_bytes,
            'overall_success_rate_percent': (total_successful / total_items * 100) if total_items > 0 else 0,
            'average_speed_mbps': (total_bytes / (1024 * 1024) / total_duration) if total_duration > 0 else 0,
            'stages': stage_summaries,
        }
    
    def save_to_file(self, file_path: Path) -> None:
        """Save metrics summary to JSON file."""
        summary = self.get_summary()
        with open(file_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Metrics saved to {file_path}")

