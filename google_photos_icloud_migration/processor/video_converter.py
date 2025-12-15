"""
Convert unsupported video formats to Photos-compatible formats.
"""
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
from tqdm import tqdm

from google_photos_icloud_migration.exceptions import ExtractionError

logger = logging.getLogger(__name__)

# Formats that Photos framework supports
SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.m4v', '.3gp'}

# Formats that need conversion
UNSUPPORTED_VIDEO_FORMATS = {'.avi', '.mkv', '.webm', '.flv', '.wmv', '.divx', '.xvid'}


class VideoConverter:
    """Handles conversion of unsupported video formats to Photos-compatible formats."""
    
    def __init__(self, output_format: str = 'mov', preserve_metadata: bool = True):
        """
        Initialize the video converter.
        
        Args:
            output_format: Target format ('mov' or 'mp4'). Default 'mov' for better compatibility.
            preserve_metadata: Whether to preserve video metadata during conversion
        """
        self.output_format = output_format.lower()
        if self.output_format not in ('mov', 'mp4'):
            raise ValueError("Output format must be 'mov' or 'mp4'")
        
        self.preserve_metadata = preserve_metadata
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> None:
        """Check if ffmpeg is installed."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            # Extract version from output
            version_line = result.stdout.split('\n')[0]
            logger.info(f"ffmpeg found: {version_line}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise ExtractionError(
                "ffmpeg is not installed. Please install it:\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: apt-get install ffmpeg\n"
                "  Or download from: https://ffmpeg.org/download.html\n"
                "\n"
                "Without ffmpeg, AVI and other unsupported video formats cannot be converted."
            ) from e
    
    def needs_conversion(self, file_path: Path) -> bool:
        """
        Check if a video file needs conversion.
        
        Args:
            file_path: Path to video file
            
        Returns:
            True if file needs conversion, False otherwise
        """
        ext = file_path.suffix.lower()
        return ext in UNSUPPORTED_VIDEO_FORMATS
    
    def get_output_path(self, input_path: Path, output_dir: Optional[Path] = None) -> Path:
        """
        Get the output path for converted video.
        
        Args:
            input_path: Original video file path
            output_dir: Optional output directory (if None, same directory as input)
            
        Returns:
            Path to output file
        """
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir / f"{input_path.stem}.{self.output_format}"
        else:
            return input_path.parent / f"{input_path.stem}.{self.output_format}"
    
    def convert_video(self, input_path: Path, output_path: Optional[Path] = None,
                     output_dir: Optional[Path] = None) -> Tuple[Path, bool]:
        """
        Convert a video file to supported format.
        
        Args:
            input_path: Path to input video file
            output_path: Optional explicit output path
            output_dir: Optional output directory (if output_path not specified)
            
        Returns:
            Tuple of (output_path, success)
        """
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_path}")
            return (input_path, False)
        
        if not self.needs_conversion(input_path):
            logger.debug(f"File {input_path.name} is already in a supported format")
            return (input_path, True)
        
        # Determine output path
        if output_path is None:
            output_path = self.get_output_path(input_path, output_dir)
        
        # Check if already converted
        if output_path.exists():
            logger.info(f"⏭️  Converted file already exists: {output_path.name}")
            return (output_path, True)
        
        logger.info(f"🔄 Converting {input_path.name} to {self.output_format.upper()} format...")
        logger.debug(f"   Input: {input_path}")
        logger.debug(f"   Output: {output_path}")
        
        # Validate file path (prevent command injection)
        from google_photos_icloud_migration.utils.security import validate_subprocess_path
        validate_subprocess_path(input_path)
        
        # Build ffmpeg command
        # Use high-quality settings that preserve video quality while ensuring compatibility
        args = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'libx264',  # H.264 codec (widely supported)
            '-preset', 'medium',  # Encoding speed vs compression tradeoff
            '-crf', '23',  # High quality (lower = better quality, 18-28 is good range)
            '-c:a', 'aac',  # AAC audio codec (widely supported)
            '-b:a', '192k',  # Audio bitrate
            '-movflags', '+faststart',  # Enable streaming/quick start
            '-y',  # Overwrite output file if exists
        ]
        
        # Preserve metadata if requested
        if self.preserve_metadata:
            args.extend([
                '-map_metadata', '0',  # Copy all metadata from input
                '-map_metadata:s', '0',  # Copy stream metadata
            ])
        
        # Add output path
        args.append(str(output_path))
        
        try:
            # Run ffmpeg with progress logging
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Monitor progress (ffmpeg outputs progress to stderr)
            duration = None
            for line in process.stderr:
                if 'Duration:' in line:
                    # Extract duration
                    try:
                        duration_str = line.split('Duration:')[1].split(',')[0].strip()
                        # Parse HH:MM:SS.ms format
                        parts = duration_str.split(':')
                        if len(parts) == 3:
                            hours, minutes, seconds = parts
                            seconds = seconds.split('.')[0]
                            duration = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
                            logger.debug(f"   Video duration: {duration_str} ({duration}s)")
                    except (ValueError, IndexError):
                        pass
                
                if 'time=' in line:
                    # Extract current time for progress
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        # Parse HH:MM:SS.ms format
                        parts = time_str.split(':')
                        if len(parts) == 3:
                            hours, minutes, seconds = parts
                            seconds = seconds.split('.')[0]
                            elapsed = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
                            if duration:
                                progress = (elapsed / duration) * 100
                                logger.debug(f"   Conversion progress: {progress:.1f}% ({time_str})")
                    except (ValueError, IndexError):
                        pass
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"❌ ffmpeg conversion failed for {input_path.name}")
                logger.error(f"   Error: {stderr[-500:]}")  # Last 500 chars of error
                if output_path.exists():
                    output_path.unlink()  # Clean up partial file
                return (input_path, False)
            
            # Verify output file exists and has content
            if not output_path.exists() or output_path.stat().st_size == 0:
                logger.error(f"❌ Conversion produced empty or missing file: {output_path.name}")
                return (input_path, False)
            
            # Log file size change
            input_size = input_path.stat().st_size / (1024 * 1024)  # MB
            output_size = output_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✓ Converted {input_path.name}")
            logger.info(f"   Size: {input_size:.1f} MB → {output_size:.1f} MB")
            
            return (output_path, True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ ffmpeg conversion failed for {input_path.name}: {e}")
            logger.error(f"   Command: {' '.join(args)}")
            if output_path.exists():
                output_path.unlink()  # Clean up partial file
            return (input_path, False)
        except (OSError, IOError) as e:
            logger.error(f"❌ File I/O error during conversion of {input_path.name}: {e}")
            if output_path.exists():
                output_path.unlink()  # Clean up partial file
            return (input_path, False)
        except Exception as e:
            logger.error(f"❌ Unexpected error converting {input_path.name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            if output_path.exists():
                output_path.unlink()  # Clean up partial file
            return (input_path, False)
    
    def convert_if_needed(self, file_path: Path, output_dir: Optional[Path] = None) -> Path:
        """
        Convert video file if needed, otherwise return original path.
        
        This is a convenience method that checks if conversion is needed
        and performs it automatically.
        
        Args:
            file_path: Path to video file
            output_dir: Optional output directory for converted file
            
        Returns:
            Path to file (original if no conversion needed, converted file otherwise)
        """
        if not self.needs_conversion(file_path):
            return file_path
        
        output_path, success = self.convert_video(file_path, output_dir=output_dir)
        if success and output_path != file_path:
            return output_path
        else:
            # Conversion failed, return original (upload will fail with clear error)
            return file_path




