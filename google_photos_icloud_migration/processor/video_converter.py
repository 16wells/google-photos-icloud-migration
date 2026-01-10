"""
Convert unsupported video formats to Photos-compatible formats.

This module handles video format conversion using ffmpeg, with support for:
- Secure temporary file handling during conversion
- Metadata preservation during conversion
- Comprehensive error handling and validation
- Progress tracking for long-running conversions
"""
import logging
import subprocess
import shutil
import tempfile
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
        Convert a video file to Photos-compatible format using ffmpeg.
        
        This method converts unsupported video formats (AVI, MKV, etc.) to
        formats supported by Apple Photos (MOV or MP4). The conversion uses
        secure temporary file handling and preserves metadata when requested.
        
        Args:
            input_path: Path to input video file to convert
            output_path: Optional explicit output file path.
                       If None, output path is derived from input_path and output_dir.
            output_dir: Optional output directory for converted file.
                       If None, converted file is placed in the same directory as input.
                       Only used if output_path is not specified.
            
        Returns:
            Tuple of (output_file_path, success_boolean).
            - If successful: (path_to_converted_file, True)
            - If conversion not needed: (original_file_path, True)
            - If conversion failed: (original_file_path, False)
        
        Raises:
            ExtractionError: If ffmpeg is not installed or conversion fails
        
        Note:
            Uses secure temporary file handling and validates all file paths
            to prevent security issues. Automatically cleans up partial files
            on conversion errors.
        """
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_path}")
            return (input_path, False)
        
        if not self.needs_conversion(input_path):
            logger.debug(f"File {input_path.name} is already in a supported format")
            return (input_path, True)
        
        # Determine output path using secure tempfile handling
        if output_path is None:
            output_path = self.get_output_path(input_path, output_dir)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if already converted
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"⏭️  Converted file already exists: {output_path.name}")
            return (output_path, True)
        
        logger.info(f"🔄 Converting {input_path.name} to {self.output_format.upper()} format...")
        logger.debug(f"   Input: {input_path}")
        logger.debug(f"   Output: {output_path}")
        
        # Validate file path (prevent command injection)
        from google_photos_icloud_migration.utils.security import validate_subprocess_path
        validate_subprocess_path(input_path)
        validate_subprocess_path(output_path)
        
        # Use secure temporary file for atomic write
        temp_output = None
        try:
            # Create temporary file in same directory for atomic rename
            with tempfile.NamedTemporaryFile(
                dir=output_path.parent,
                prefix=f'.tmp_{output_path.stem}_',
                suffix=f'.{self.output_format}',
                delete=False
            ) as temp_file:
                temp_output = Path(temp_file.name)
            
            # Build ffmpeg command with high-quality settings
            # Use secure temporary file for output, then atomic rename
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
            
            # Use temporary file for output (atomic write)
            args.append(str(temp_output))
            
            # Run ffmpeg with timeout handling
            # Note: Popen doesn't support timeout directly, use run() with timeout instead
            try:
                # Use run() with timeout for better control
                result = subprocess.run(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600,  # 1 hour timeout for very long videos
                    check=False  # Don't raise on non-zero exit, check manually
                )
                stdout = result.stdout
                stderr = result.stderr
                return_code = result.returncode
            except subprocess.TimeoutExpired as e:
                logger.error(f"❌ ffmpeg conversion timed out for {input_path.name} after 1 hour")
                # Clean up temporary file on timeout
                if temp_output and temp_output.exists():
                    temp_output.unlink()
                return (input_path, False)
            
            # Parse stderr for progress information (for logging)
            duration = None
            if stderr:
                for line in stderr.split('\n'):
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
                    
                    if 'time=' in line and duration:
                        # Extract current time for progress
                        try:
                            time_str = line.split('time=')[1].split()[0]
                            # Parse HH:MM:SS.ms format
                            parts = time_str.split(':')
                            if len(parts) == 3:
                                hours, minutes, seconds = parts
                                seconds = seconds.split('.')[0]
                                elapsed = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
                                progress = (elapsed / duration) * 100
                                logger.debug(f"   Conversion progress: {progress:.1f}% ({time_str})")
                        except (ValueError, IndexError):
                            pass
            
            # Check return code
            if return_code != 0:
                logger.error(f"❌ ffmpeg conversion failed for {input_path.name}")
                logger.error(f"   Error: {stderr[-500:] if stderr else 'Unknown error'}")
                # Clean up temporary file on error
                if temp_output and temp_output.exists():
                    temp_output.unlink()
                return (input_path, False)
            
            # Verify temporary output file exists and has content
            if not temp_output.exists() or temp_output.stat().st_size == 0:
                logger.error(f"❌ Conversion produced empty or missing file: {temp_output.name}")
                return (input_path, False)
            
            # Set secure file permissions on temporary file
            try:
                temp_output.chmod(0o600)  # Owner read/write only
            except (OSError, PermissionError):
                pass  # Best effort
            
            # Atomic rename from temporary file to final output
            temp_output.replace(output_path)
            
            # Log file size change
            input_size = input_path.stat().st_size / (1024 * 1024)  # MB
            output_size = output_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✓ Converted {input_path.name}")
            logger.info(f"   Size: {input_size:.1f} MB → {output_size:.1f} MB")
            
            return (output_path, True)
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"❌ ffmpeg conversion timed out for {input_path.name} after 1 hour")
            if temp_output and temp_output.exists():
                temp_output.unlink()
            return (input_path, False)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ ffmpeg conversion failed for {input_path.name}: {e}")
            if temp_output and temp_output.exists():
                temp_output.unlink()
            return (input_path, False)
        except (OSError, IOError) as e:
            logger.error(f"❌ File I/O error during conversion of {input_path.name}: {e}")
            if temp_output and temp_output.exists():
                temp_output.unlink()
            return (input_path, False)
        except Exception as e:
            logger.error(f"❌ Unexpected error converting {input_path.name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            if temp_output and temp_output.exists():
                temp_output.unlink()
            return (input_path, False)
        finally:
            # Ensure temporary file is cleaned up even on unexpected errors
            if temp_output and temp_output.exists():
                try:
                    temp_output.unlink()
                except OSError:
                    pass  # Best effort cleanup
    
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




