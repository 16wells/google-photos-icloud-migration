"""
Report generator for migration results.
"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .migration_statistics import MigrationStatistics


class ReportGenerator:
    """Generates comprehensive migration reports."""
    
    def __init__(self, statistics: MigrationStatistics, base_dir: Path, 
                 log_file: Optional[Path] = None,
                 failed_uploads_file: Optional[Path] = None,
                 corrupted_zips_file: Optional[Path] = None):
        """
        Initialize report generator.
        
        Args:
            statistics: Migration statistics object
            base_dir: Base directory for migration
            log_file: Path to log file
            failed_uploads_file: Path to failed uploads JSON file
            corrupted_zips_file: Path to corrupted zips JSON file
        """
        self.stats = statistics
        self.base_dir = base_dir
        self.log_file = log_file
        self.failed_uploads_file = failed_uploads_file
        self.corrupted_zips_file = corrupted_zips_file
    
    def _format_size(self, bytes_size: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
    
    def _format_duration(self, seconds: Optional[float]) -> str:
        """Format duration to human-readable string."""
        if seconds is None:
            return "N/A"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def _calculate_success_rate(self, successful: int, total: int) -> float:
        """Calculate success rate percentage."""
        if total == 0:
            return 0.0
        return (successful / total) * 100.0
    
    def generate_text_report(self) -> str:
        """Generate a text-formatted report."""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("GOOGLE PHOTOS TO iCLOUD PHOTOS MIGRATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        if self.stats.start_time and self.stats.end_time:
            lines.append(f"Start Time:     {self.stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"End Time:       {self.stats.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Duration:       {self._format_duration(self.stats.get_duration())}")
        lines.append("")
        
        # Overall Statistics
        total_zips = self.stats.zip_files_total
        successful_zips = self.stats.zip_files_processed_successfully
        failed_zips = self.stats.zip_files_processed_failed
        
        lines.append("Overall Results:")
        lines.append(f"  Zip Files Processed:     {successful_zips}/{total_zips} successful")
        if failed_zips > 0:
            lines.append(f"  Zip Files Failed:         {failed_zips}/{total_zips}")
        success_rate = self._calculate_success_rate(successful_zips, total_zips)
        lines.append(f"  Success Rate:             {success_rate:.1f}%")
        lines.append("")
        
        # Media Files
        lines.append("Media Files:")
        lines.append(f"  Total Found:               {self.stats.media_files_found}")
        lines.append(f"  With Metadata:             {self.stats.media_files_with_metadata}")
        lines.append(f"  Processed:                {self.stats.media_files_processed}")
        if self.stats.media_files_processing_failed > 0:
            lines.append(f"  Processing Failed:         {self.stats.media_files_processing_failed}")
        lines.append("")
        
        # Upload Statistics
        total_uploads = self.stats.files_uploaded_successfully + self.stats.files_upload_failed
        upload_success_rate = self._calculate_success_rate(
            self.stats.files_uploaded_successfully, 
            total_uploads
        ) if total_uploads > 0 else 0.0
        
        lines.append("Upload Results:")
        lines.append(f"  Successfully Uploaded:     {self.stats.files_uploaded_successfully}")
        if self.stats.files_upload_failed > 0:
            lines.append(f"  Upload Failed:             {self.stats.files_upload_failed}")
        if self.stats.files_verification_failed > 0:
            lines.append(f"  Verification Failed:        {self.stats.files_verification_failed}")
        lines.append(f"  Upload Success Rate:       {upload_success_rate:.1f}%")
        if self.stats.total_uploaded_size > 0:
            lines.append(f"  Total Uploaded Size:        {self._format_size(self.stats.total_uploaded_size)}")
        lines.append("")
        
        # Albums
        lines.append("Albums:")
        lines.append(f"  Albums Identified:         {self.stats.albums_identified}")
        if self.stats.albums_from_structure > 0:
            lines.append(f"  From Directory Structure:   {self.stats.albums_from_structure}")
        if self.stats.albums_from_json > 0:
            lines.append(f"  From JSON Metadata:        {self.stats.albums_from_json}")
        lines.append("")
        
        # Phase-by-Phase Breakdown
        lines.append("=" * 80)
        lines.append("PHASE-BY-PHASE BREAKDOWN")
        lines.append("=" * 80)
        lines.append("")
        
        # Phase 1: Download
        lines.append("Phase 1: Download from Google Drive")
        lines.append("-" * 80)
        lines.append(f"  Total Zip Files:           {self.stats.zip_files_total}")
        lines.append(f"  Downloaded:                 {self.stats.zip_files_downloaded}")
        if self.stats.zip_files_skipped_existing > 0:
            lines.append(f"  Skipped (Already Existed):  {self.stats.zip_files_skipped_existing}")
        if self.stats.zip_files_failed_download > 0:
            lines.append(f"  Download Failed:            {self.stats.zip_files_failed_download}")
        if self.stats.zip_files_corrupted > 0:
            lines.append(f"  Corrupted:                  {self.stats.zip_files_corrupted}")
        if self.stats.total_downloaded_size > 0:
            lines.append(f"  Total Downloaded Size:      {self._format_size(self.stats.total_downloaded_size)}")
        lines.append("")
        
        # Phase 2: Extraction
        lines.append("Phase 2: Extraction")
        lines.append("-" * 80)
        lines.append(f"  Extracted Successfully:     {self.stats.zip_files_extracted}")
        if self.stats.zip_files_extraction_failed > 0:
            lines.append(f"  Extraction Failed:          {self.stats.zip_files_extraction_failed}")
        lines.append("")
        
        # Phase 3: Metadata Processing
        lines.append("Phase 3: Metadata Processing")
        lines.append("-" * 80)
        lines.append(f"  Media Files Found:          {self.stats.media_files_found}")
        lines.append(f"  With JSON Metadata:         {self.stats.media_files_with_metadata}")
        lines.append(f"  Successfully Processed:     {self.stats.media_files_processed}")
        if self.stats.media_files_processing_failed > 0:
            lines.append(f"  Processing Failed:          {self.stats.media_files_processing_failed}")
        lines.append("")
        
        # Phase 4: Album Parsing
        lines.append("Phase 4: Album Parsing")
        lines.append("-" * 80)
        lines.append(f"  Albums Identified:          {self.stats.albums_identified}")
        lines.append("")
        
        # Phase 5: Upload
        lines.append("Phase 5: Upload to iCloud Photos")
        lines.append("-" * 80)
        lines.append(f"  Successfully Uploaded:      {self.stats.files_uploaded_successfully}")
        if self.stats.files_upload_failed > 0:
            lines.append(f"  Upload Failed:              {self.stats.files_upload_failed}")
        if self.stats.files_verification_failed > 0:
            lines.append(f"  Verification Failed:        {self.stats.files_verification_failed}")
        lines.append("")
        
        # Error Summary
        total_errors = (
            len(self.stats.zip_download_errors) +
            len(self.stats.extraction_errors) +
            len(self.stats.metadata_errors) +
            len(self.stats.upload_errors) +
            len(self.stats.verification_errors)
        )
        
        if total_errors > 0:
            lines.append("=" * 80)
            lines.append("ERROR SUMMARY")
            lines.append("=" * 80)
            lines.append("")
            
            if len(self.stats.zip_download_errors) > 0:
                lines.append(f"Download Errors:             {len(self.stats.zip_download_errors)}")
            if len(self.stats.extraction_errors) > 0:
                lines.append(f"Extraction Errors:            {len(self.stats.extraction_errors)}")
            if len(self.stats.metadata_errors) > 0:
                lines.append(f"Metadata Processing Errors:   {len(self.stats.metadata_errors)}")
            if len(self.stats.upload_errors) > 0:
                lines.append(f"Upload Errors:                {len(self.stats.upload_errors)}")
            if len(self.stats.verification_errors) > 0:
                lines.append(f"Verification Errors:          {len(self.stats.verification_errors)}")
            lines.append("")
            lines.append("Note: See detailed error logs in the log file and error tracking files.")
            lines.append("")
        
        # File References
        lines.append("=" * 80)
        lines.append("FILE REFERENCES")
        lines.append("=" * 80)
        lines.append("")
        
        if self.log_file and self.log_file.exists():
            lines.append(f"Detailed Log File:            {self.log_file.absolute()}")
            lines.append("  Contains: All operations, errors, and debug information")
        else:
            lines.append("Detailed Log File:            Not available")
        
        lines.append("")
        
        if self.failed_uploads_file and self.failed_uploads_file.exists():
            try:
                with open(self.failed_uploads_file, 'r') as f:
                    failed_data = json.load(f)
                failed_count = len(failed_data)
                lines.append(f"Failed Uploads File:         {self.failed_uploads_file.absolute()}")
                lines.append(f"  Contains: {failed_count} files that failed to upload")
                lines.append("  Format: JSON with file paths and album information")
            except Exception:
                lines.append(f"Failed Uploads File:         {self.failed_uploads_file.absolute()}")
                lines.append("  (File exists but could not be read)")
        else:
            lines.append("Failed Uploads File:          None (all uploads succeeded)")
        
        lines.append("")
        
        if self.corrupted_zips_file and self.corrupted_zips_file.exists():
            try:
                with open(self.corrupted_zips_file, 'r') as f:
                    corrupted_data = json.load(f)
                corrupted_count = len(corrupted_data)
                lines.append(f"Corrupted Zip Files File:    {self.corrupted_zips_file.absolute()}")
                lines.append(f"  Contains: {corrupted_count} corrupted zip files")
                lines.append("  Format: JSON with file IDs and error information")
            except Exception:
                lines.append(f"Corrupted Zip Files File:    {self.corrupted_zips_file.absolute()}")
                lines.append("  (File exists but could not be read)")
        else:
            lines.append("Corrupted Zip Files File:     None (no corrupted files)")
        
        lines.append("")
        
        # Recommendations
        lines.append("=" * 80)
        lines.append("RECOMMENDATIONS & NEXT STEPS")
        lines.append("=" * 80)
        lines.append("")
        
        recommendations = []
        
        if self.stats.files_upload_failed > 0 or (self.failed_uploads_file and self.failed_uploads_file.exists()):
            recommendations.append(
                f"• Retry failed uploads by running:\n"
                f"  python main.py --config config.yaml --retry-failed"
            )
        
        if self.stats.zip_files_corrupted > 0 or (self.corrupted_zips_file and self.corrupted_zips_file.exists()):
            recommendations.append(
                "• Re-download corrupted zip files from Google Drive:\n"
                "  - Check the corrupted_zips.json file for file IDs\n"
                "  - Manually download from Google Drive or delete local files and re-run"
            )
        
        if self.stats.files_verification_failed > 0:
            recommendations.append(
                "• Review verification failures - some files may not have uploaded correctly\n"
                "  Check the log file for specific verification error details"
            )
        
        if self.stats.zip_files_failed_download > 0:
            recommendations.append(
                "• Review download failures - check network connectivity and Google Drive access"
            )
        
        if self.stats.zip_files_extraction_failed > 0:
            recommendations.append(
                "• Review extraction failures - some zip files may be corrupted or incomplete"
            )
        
        if not recommendations:
            recommendations.append("✓ Migration completed successfully! All files processed and uploaded.")
        
        for i, rec in enumerate(recommendations, 1):
            lines.append(rec)
            if i < len(recommendations):
                lines.append("")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generate_html_report(self) -> str:
        """Generate an HTML-formatted report."""
        # For now, return a simple HTML version
        # This could be enhanced with charts, tables, etc.
        html_lines = []
        html_lines.append("<!DOCTYPE html>")
        html_lines.append("<html>")
        html_lines.append("<head>")
        html_lines.append("  <title>Migration Report</title>")
        html_lines.append("  <style>")
        html_lines.append("    body { font-family: Arial, sans-serif; margin: 20px; }")
        html_lines.append("    h1 { color: #333; }")
        html_lines.append("    h2 { color: #666; border-bottom: 2px solid #ccc; padding-bottom: 5px; }")
        html_lines.append("    .stat { margin: 10px 0; }")
        html_lines.append("    .success { color: green; }")
        html_lines.append("    .error { color: red; }")
        html_lines.append("    .warning { color: orange; }")
        html_lines.append("    pre { background: #f5f5f5; padding: 10px; border-radius: 5px; }")
        html_lines.append("  </style>")
        html_lines.append("</head>")
        html_lines.append("<body>")
        html_lines.append("  <h1>Google Photos to iCloud Photos Migration Report</h1>")
        html_lines.append("  <pre>")
        html_lines.append(self.generate_text_report())
        html_lines.append("  </pre>")
        html_lines.append("</body>")
        html_lines.append("</html>")
        return "\n".join(html_lines)
    
    def save_report(self, output_path: Optional[Path] = None, format: str = 'text') -> Path:
        """
        Save report to file.
        
        Args:
            output_path: Optional output path (defaults to base_dir/migration_report.txt)
            format: Report format ('text' or 'html')
        
        Returns:
            Path to saved report file
        """
        if output_path is None:
            if format == 'html':
                output_path = self.base_dir / 'migration_report.html'
            else:
                output_path = self.base_dir / 'migration_report.txt'
        
        if format == 'html':
            content = self.generate_html_report()
        else:
            content = self.generate_text_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
