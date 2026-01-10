"""
Tests for health check utilities.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from google_photos_icloud_migration.utils.health_check import (
    HealthChecker,
    HealthCheckResult,
)


class TestHealthCheckResult:
    """Tests for HealthCheckResult class."""
    
    def test_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult("Test Check", True, "Test passed")
        assert result.name == "Test Check"
        assert result.passed is True
        assert result.message == "Test passed"
        assert result.severity == "error"
    
    def test_result_with_severity(self):
        """Test result with warning severity."""
        result = HealthCheckResult("Test Check", False, "Test warning", severity="warning")
        assert result.severity == "warning"


class TestHealthChecker:
    """Tests for HealthChecker class."""
    
    def test_checker_initialization(self):
        """Test initializing health checker."""
        checker = HealthChecker()
        assert checker.base_dir == Path("/tmp")
        assert checker.results == []
    
    def test_checker_with_custom_dir(self):
        """Test checker with custom base directory."""
        custom_dir = Path("/custom/path")
        checker = HealthChecker(custom_dir)
        assert checker.base_dir == custom_dir
    
    def test_check_python_version_pass(self):
        """Test Python version check passes for Python 3.11+."""
        checker = HealthChecker()
        checker.check_python_version()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "Python Version"
        
        # Should pass if Python 3.11+
        if sys.version_info >= (3, 11):
            assert result.passed is True
        else:
            assert result.passed is False
    
    def test_check_exiftool_not_found(self):
        """Test ExifTool check when not installed."""
        checker = HealthChecker()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            checker.check_exiftool()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "ExifTool"
        assert result.passed is False
    
    def test_check_exiftool_found(self):
        """Test ExifTool check when installed."""
        checker = HealthChecker()
        
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "12.50\n"
            mock_run.return_value = mock_result
            checker.check_exiftool()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "ExifTool"
        # Should pass if ExifTool found
        if mock_run.called:
            assert result.passed is True
    
    def test_check_disk_space_sufficient(self):
        """Test disk space check with sufficient space."""
        checker = HealthChecker()
        
        with patch('shutil.disk_usage') as mock_disk:
            # Mock 50GB free space
            mock_stat = MagicMock()
            mock_stat.free = 50 * (1024 ** 3)
            mock_disk.return_value = mock_stat
            
            checker.check_disk_space()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "Disk Space"
        assert result.passed is True
    
    def test_check_disk_space_low(self):
        """Test disk space check with low space."""
        checker = HealthChecker()
        
        with patch('shutil.disk_usage') as mock_disk:
            # Mock 5GB free space (less than 10GB warning threshold)
            mock_stat = MagicMock()
            mock_stat.free = 5 * (1024 ** 3)
            mock_disk.return_value = mock_stat
            
            checker.check_disk_space()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "Disk Space"
        assert result.passed is False
    
    def test_check_write_permissions_pass(self):
        """Test write permissions check when permissions are OK."""
        checker = HealthChecker()
        
        with patch.object(Path, 'write_text') as mock_write, \
             patch.object(Path, 'unlink') as mock_unlink:
            checker.check_write_permissions()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "Write Permissions"
        # Should pass if no exception raised
        assert result.passed is True
    
    def test_check_write_permissions_fail(self):
        """Test write permissions check when permissions fail."""
        checker = HealthChecker()
        
        with patch.object(Path, 'write_text', side_effect=PermissionError("Access denied")):
            checker.check_write_permissions()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "Write Permissions"
        assert result.passed is False
    
    def test_check_network_connectivity(self):
        """Test network connectivity check."""
        checker = HealthChecker()
        
        with patch('socket.create_connection') as mock_connect:
            mock_connect.return_value = None
            checker.check_network_connectivity()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "Network Connectivity"
        # Should pass if connection succeeds
        if mock_connect.called:
            assert result.passed is True
    
    def test_check_all(self):
        """Test running all health checks."""
        checker = HealthChecker()
        
        with patch('subprocess.run', side_effect=FileNotFoundError()), \
             patch('shutil.disk_usage') as mock_disk, \
             patch.object(Path, 'write_text'), \
             patch.object(Path, 'unlink'), \
             patch('socket.create_connection'):
            mock_stat = MagicMock()
            mock_stat.free = 50 * (1024 ** 3)
            mock_disk.return_value = mock_stat
            
            all_passed, results = checker.check_all()
        
        # Should have run multiple checks
        assert len(results) >= 4  # Python version, dependencies, ExifTool, disk space, etc.
        assert isinstance(all_passed, bool)
    
    def test_print_results(self, capsys):
        """Test printing health check results."""
        checker = HealthChecker()
        checker.results = [
            HealthCheckResult("Test 1", True, "Passed"),
            HealthCheckResult("Test 2", False, "Failed", severity="error"),
        ]
        
        checker.print_results()
        output = capsys.readouterr().out
        
        assert "Health Check Results" in output
        assert "Test 1" in output
        assert "Test 2" in output
