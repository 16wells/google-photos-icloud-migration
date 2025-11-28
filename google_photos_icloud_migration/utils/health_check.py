"""
Health check utilities to verify system readiness before migration.
"""
import os
import shutil
import subprocess
import sys
import platform
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Result of a health check."""
    
    def __init__(self, name: str, passed: bool, message: str, severity: str = "error"):
        """
        Initialize health check result.
        
        Args:
            name: Name of the check
            passed: Whether the check passed
            message: Human-readable message
            severity: "error" or "warning"
        """
        self.name = name
        self.passed = passed
        self.message = message
        self.severity = severity


class HealthChecker:
    """Performs health checks before migration."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize health checker.
        
        Args:
            base_dir: Base directory for migration (for disk space checks)
        """
        self.base_dir = base_dir or Path("/tmp")
        self.results: List[HealthCheckResult] = []
    
    def check_all(self) -> Tuple[bool, List[HealthCheckResult]]:
        """
        Run all health checks.
        
        Returns:
            Tuple of (all_passed, list of results)
        """
        self.results = []
        
        self.check_python_version()
        self.check_dependencies()
        self.check_exiftool()
        self.check_disk_space()
        self.check_write_permissions()
        self.check_network_connectivity()
        
        all_passed = all(r.passed for r in self.results)
        return all_passed, self.results
    
    def check_python_version(self) -> None:
        """Check Python version is 3.11+."""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 11:
            self.results.append(HealthCheckResult(
                "Python Version",
                True,
                f"Python {version.major}.{version.minor}.{version.micro}"
            ))
        else:
            self.results.append(HealthCheckResult(
                "Python Version",
                False,
                f"Python {version.major}.{version.minor}.{version.micro} detected. "
                f"Python 3.11+ required."
            ))
    
    def check_dependencies(self) -> None:
        """Check that required Python packages are installed."""
        required_packages = [
            'googleapiclient',
            'google.auth',
            'yaml',
            'tqdm',
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace('.', '_'))
            except ImportError:
                missing.append(package)
        
        if not missing:
            self.results.append(HealthCheckResult(
                "Python Dependencies",
                True,
                "All required packages installed"
            ))
        else:
            self.results.append(HealthCheckResult(
                "Python Dependencies",
                False,
                f"Missing packages: {', '.join(missing)}. "
                f"Install with: pip install -r requirements.txt"
            ))
    
    def check_exiftool(self) -> None:
        """Check if ExifTool is installed."""
        try:
            result = subprocess.run(
                ['exiftool', '-ver'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.results.append(HealthCheckResult(
                    "ExifTool",
                    True,
                    f"ExifTool {version} installed"
                ))
            else:
                self.results.append(HealthCheckResult(
                    "ExifTool",
                    False,
                    "ExifTool not found. Install with: brew install exiftool (macOS)"
                ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.results.append(HealthCheckResult(
                "ExifTool",
                False,
                "ExifTool not found. Install with: brew install exiftool (macOS)"
            ))
    
    def check_disk_space(self, required_gb: Optional[float] = None) -> None:
        """Check available disk space."""
        try:
            stat = shutil.disk_usage(self.base_dir)
            available_gb = stat.free / (1024 ** 3)
            
            if required_gb:
                if available_gb >= required_gb:
                    self.results.append(HealthCheckResult(
                        "Disk Space",
                        True,
                        f"{available_gb:.1f} GB available (required: {required_gb:.1f} GB)"
                    ))
                else:
                    self.results.append(HealthCheckResult(
                        "Disk Space",
                        False,
                        f"Only {available_gb:.1f} GB available, but {required_gb:.1f} GB required"
                    ))
            else:
                # Just warn if less than 10GB
                if available_gb < 10:
                    self.results.append(HealthCheckResult(
                        "Disk Space",
                        False,
                        f"Low disk space: {available_gb:.1f} GB available",
                        severity="warning"
                    ))
                else:
                    self.results.append(HealthCheckResult(
                        "Disk Space",
                        True,
                        f"{available_gb:.1f} GB available"
                    ))
        except OSError as e:
            self.results.append(HealthCheckResult(
                "Disk Space",
                False,
                f"Could not check disk space: {e}"
            ))
    
    def check_write_permissions(self) -> None:
        """Check write permissions in base directory."""
        try:
            test_file = self.base_dir / '.health_check_test'
            test_file.write_text('test')
            test_file.unlink()
            
            self.results.append(HealthCheckResult(
                "Write Permissions",
                True,
                f"Can write to {self.base_dir}"
            ))
        except (OSError, PermissionError) as e:
            self.results.append(HealthCheckResult(
                "Write Permissions",
                False,
                f"Cannot write to {self.base_dir}: {e}"
            ))
    
    def check_network_connectivity(self) -> None:
        """Check network connectivity to required services."""
        import socket
        
        # Check DNS resolution and connectivity
        hosts_to_check = [
            ('Google Drive API', 'www.googleapis.com', 443),
            ('Apple iCloud', 'icloud.com', 443),
        ]
        
        failed = []
        for name, host, port in hosts_to_check:
            try:
                socket.create_connection((host, port), timeout=5)
            except (socket.error, OSError):
                failed.append(name)
        
        if not failed:
            self.results.append(HealthCheckResult(
                "Network Connectivity",
                True,
                "Can reach required services"
            ))
        else:
            self.results.append(HealthCheckResult(
                "Network Connectivity",
                False,
                f"Cannot reach: {', '.join(failed)}"
            ))
    
    def print_results(self) -> None:
        """Print health check results."""
        print("\n" + "=" * 60)
        print("Health Check Results")
        print("=" * 60)
        
        for result in self.results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status}: {result.name}")
            print(f"  {result.message}")
        
        print("=" * 60)
        
        if all(r.passed for r in self.results):
            print("All checks passed! ✓")
        else:
            failed = [r for r in self.results if not r.passed]
            errors = [r for r in failed if r.severity == "error"]
            warnings = [r for r in failed if r.severity == "warning"]
            
            if errors:
                print(f"\n{len(errors)} error(s) must be fixed before migration can proceed.")
            if warnings:
                print(f"{len(warnings)} warning(s) - migration may still work but could fail.")

