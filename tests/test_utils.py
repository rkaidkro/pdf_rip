"""
Tests for utility functions.
"""

import pytest
from pathlib import Path
from src.utils import (
    generate_run_id, calculate_element_hash, sanitize_filename,
    calculate_cer, calculate_wer, ensure_directory, save_jsonl, load_jsonl
)


class TestRunIdGeneration:
    """Test run ID generation."""
    
    def test_generate_run_id(self):
        """Test that run ID is generated correctly."""
        run_id = generate_run_id()
        assert run_id.startswith("run_")
        assert len(run_id) > 10  # Should be reasonably long
        assert "_" in run_id


class TestElementHash:
    """Test element hash calculation."""
    
    def test_calculate_element_hash(self):
        """Test element hash calculation."""
        content = "test content"
        bbox = [10.0, 20.0, 100.0, 200.0]
        page = 1
        
        hash1 = calculate_element_hash(content, bbox, page)
        hash2 = calculate_element_hash(content, bbox, page)
        
        # Same inputs should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 characters
        
        # Different inputs should produce different hashes
        hash3 = calculate_element_hash("different content", bbox, page)
        assert hash1 != hash3


class TestFilenameSanitization:
    """Test filename sanitization."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test invalid characters
        assert sanitize_filename("file<name>.txt") == "file_name_.txt"
        assert sanitize_filename("file:name.txt") == "file_name.txt"
        assert sanitize_filename("file/name.txt") == "file_name.txt"
        
        # Test length limit
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 200
        assert sanitized.endswith(".txt")
        
        # Test normal filename
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"


class TestErrorRateCalculation:
    """Test error rate calculations."""
    
    def test_calculate_cer(self):
        """Test character error rate calculation."""
        # Perfect match
        assert calculate_cer("hello", "hello") == 0.0
        
        # One character difference
        assert calculate_cer("hello", "helo") == 0.2  # 1/5 = 0.2
        
        # Empty reference
        assert calculate_cer("", "hello") == 1.0
        
        # Empty hypothesis
        assert calculate_cer("hello", "") == 1.0
        
        # Both empty
        assert calculate_cer("", "") == 0.0
    
    def test_calculate_wer(self):
        """Test word error rate calculation."""
        # Perfect match
        assert calculate_wer("hello world", "hello world") == 0.0
        
        # One word difference
        assert calculate_wer("hello world", "hello there") == 0.5  # 1/2 = 0.5
        
        # Empty reference
        assert calculate_wer("", "hello world") == 1.0
        
        # Empty hypothesis
        assert calculate_wer("hello world", "") == 1.0
        
        # Both empty
        assert calculate_wer("", "") == 0.0


class TestFileOperations:
    """Test file operations."""
    
    def test_ensure_directory(self, tmp_path):
        """Test directory creation."""
        test_dir = tmp_path / "test_subdir"
        ensure_directory(test_dir)
        assert test_dir.exists()
        assert test_dir.is_dir()
        
        # Should not fail if directory already exists
        ensure_directory(test_dir)
        assert test_dir.exists()
    
    def test_save_and_load_jsonl(self, tmp_path):
        """Test JSONL save and load operations."""
        test_file = tmp_path / "test.jsonl"
        test_data = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"}
        ]
        
        # Save data
        save_jsonl(test_data, test_file)
        assert test_file.exists()
        
        # Load data
        loaded_data = load_jsonl(test_file)
        assert loaded_data == test_data
        
        # Test loading non-existent file
        non_existent_file = tmp_path / "nonexistent.jsonl"
        loaded_data = load_jsonl(non_existent_file)
        assert loaded_data == []
    
    def test_save_jsonl_empty_data(self, tmp_path):
        """Test saving empty JSONL data."""
        test_file = tmp_path / "empty.jsonl"
        save_jsonl([], test_file)
        assert test_file.exists()
        
        loaded_data = load_jsonl(test_file)
        assert loaded_data == []
