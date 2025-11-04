"""
Comprehensive tests for the document processing pipeline.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.processor import DocumentProcessor
from src.models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints
from src.utils import validate_document_file


class TestProcessingPipeline:
    """Test the complete document processing pipeline."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def processor(self, temp_output_dir):
        """Create a document processor."""
        return DocumentProcessor(temp_output_dir)
    
    def test_pdf_processing_success(self, processor, temp_output_dir):
        """Test successful PDF processing."""
        # Use the test PDF from examples
        pdf_path = Path("examples/test_document.pdf")
        
        if not pdf_path.exists():
            pytest.skip("Test PDF not found")
        
        # Create processing request
        request = ProcessingRequest(
            document_path=pdf_path,
            run_mode=RunMode.PRODUCTION,
            compliance=ComplianceConfig(
                classification_tag="UNCLASSIFIED",
                pii_redaction=False
            ),
            ceilings=ProcessingCeilings(
                max_runtime_s=3600,
                max_memory_mb=8192
            ),
            doc_hints=DocumentHints()
        )
        
        # Process document
        result = processor.process(request)
        
        # Assertions
        assert result.run_report.success is True, f"Processing failed: {result.run_report.error_message}"
        assert len(result.markdown_content) > 0, "Markdown content should not be empty"
        assert len(result.provenance_records) > 0, "Should have provenance records"
        
        # Check output files
        doc_output_dir = temp_output_dir / "test_document"
        assert doc_output_dir.exists(), "Output directory should exist"
        assert (doc_output_dir / "document.md").exists(), "Markdown file should exist"
        assert (doc_output_dir / "provenance.jsonl").exists(), "Provenance file should exist"
        assert (doc_output_dir / "run_report.json").exists(), "Run report should exist"
        
        # Check markdown content
        with open(doc_output_dir / "document.md", 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 0, "Markdown file should not be empty"
    
    def test_word_processing_success(self, processor, temp_output_dir):
        """Test successful Word document processing."""
        # Use the test Word document from examples
        docx_path = Path("examples/test_document.docx")
        
        if not docx_path.exists():
            pytest.skip("Test Word document not found")
        
        # Create processing request
        request = ProcessingRequest(
            document_path=docx_path,
            run_mode=RunMode.PRODUCTION,
            compliance=ComplianceConfig(
                classification_tag="UNCLASSIFIED",
                pii_redaction=False
            ),
            ceilings=ProcessingCeilings(
                max_runtime_s=3600,
                max_memory_mb=8192
            ),
            doc_hints=DocumentHints()
        )
        
        # Process document
        result = processor.process(request)
        
        # Assertions
        assert result.run_report.success is True, f"Processing failed: {result.run_report.error_message}"
        assert len(result.markdown_content) > 0, "Markdown content should not be empty"
        assert len(result.provenance_records) > 0, "Should have provenance records"
        
        # Check output files
        doc_output_dir = temp_output_dir / "test_document"
        assert doc_output_dir.exists(), "Output directory should exist"
        assert (doc_output_dir / "document.md").exists(), "Markdown file should exist"
        
        # Check markdown content
        with open(doc_output_dir / "document.md", 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 0, "Markdown file should not be empty"
    
    def test_empty_content_detection(self, processor, temp_output_dir):
        """Test that empty content is properly detected and marked as failed."""
        # Create a minimal PDF with no text content
        # This test ensures the quality assurance system works correctly
        
        # For this test, we'll create a request with no document path
        # which should result in empty content
        request = ProcessingRequest(
            document_path=None,
            pdf_bytes=b"",  # Empty bytes
            run_mode=RunMode.PRODUCTION,
            compliance=ComplianceConfig(
                classification_tag="UNCLASSIFIED",
                pii_redaction=False
            ),
            ceilings=ProcessingCeilings(
                max_runtime_s=3600,
                max_memory_mb=8192
            ),
            doc_hints=DocumentHints()
        )
        
        # Process document
        result = processor.process(request)
        
        # Should fail due to empty content
        assert result.run_report.success is False, "Should fail with empty content"
        assert len(result.markdown_content) == 0, "Should have no markdown content"
        
        # Check for appropriate defects
        defects = result.run_report.defects
        assert len(defects) > 0, "Should have defects for empty content"
        
        # Check for high severity defects
        high_severity_defects = [d for d in defects if d.severity == "high"]
        assert len(high_severity_defects) > 0, "Should have high severity defects"
    
    def test_document_path_handling(self, processor, temp_output_dir):
        """Test that both document_path and pdf_path are handled correctly."""
        # Use the test PDF
        pdf_path = Path("examples/test_document.pdf")
        
        if not pdf_path.exists():
            pytest.skip("Test PDF not found")
        
        # Test with document_path (new field)
        request1 = ProcessingRequest(
            document_path=pdf_path,
            run_mode=RunMode.PRODUCTION,
            compliance=ComplianceConfig(),
            ceilings=ProcessingCeilings(),
            doc_hints=DocumentHints()
        )
        
        result1 = processor.process(request1)
        assert result1.run_report.success is True, "Should succeed with document_path"
        
        # Test with pdf_path (old field)
        request2 = ProcessingRequest(
            pdf_path=pdf_path,
            run_mode=RunMode.PRODUCTION,
            compliance=ComplianceConfig(),
            ceilings=ProcessingCeilings(),
            doc_hints=DocumentHints()
        )
        
        result2 = processor.process(request2)
        assert result2.run_report.success is True, "Should succeed with pdf_path"
        
        # Both should produce the same content
        assert result1.markdown_content == result2.markdown_content, "Both paths should produce same content"
    
    def test_quality_assurance_integration(self, processor, temp_output_dir):
        """Test that quality assurance properly detects issues."""
        # Use the test PDF
        pdf_path = Path("examples/test_document.pdf")
        
        if not pdf_path.exists():
            pytest.skip("Test PDF not found")
        
        # Process in evaluation mode to trigger full QA
        request = ProcessingRequest(
            document_path=pdf_path,
            run_mode=RunMode.EVALUATION,
            compliance=ComplianceConfig(),
            ceilings=ProcessingCeilings(),
            doc_hints=DocumentHints()
        )
        
        result = processor.process(request)
        
        # Should succeed but may have quality issues
        assert result.run_report.success is True, "Should succeed in evaluation mode"
        assert len(result.markdown_content) > 0, "Should have content"
        
        # Check quality metrics
        metrics = result.run_report.quality_metrics
        assert metrics is not None, "Should have quality metrics"
        
        # Check for defects (may have minor issues)
        defects = result.run_report.defects
        # Note: We don't assert on defect count as it depends on content quality
    
    def test_error_handling(self, processor, temp_output_dir):
        """Test error handling for invalid files."""
        # Create a request with a non-existent file
        non_existent_path = Path("/non/existent/file.pdf")
        
        request = ProcessingRequest(
            document_path=non_existent_path,
            run_mode=RunMode.PRODUCTION,
            compliance=ComplianceConfig(),
            ceilings=ProcessingCeilings(),
            doc_hints=DocumentHints()
        )
        
        # Should handle the error gracefully
        result = processor.process(request)
        
        # Should fail
        assert result.run_report.success is False, "Should fail with non-existent file"
        assert result.run_report.error_message is not None, "Should have error message"


class TestFolderProcessor:
    """Test the folder-based processing system."""
    
    def test_folder_processor_creation(self):
        """Test that folder processor can be created."""
        from src.folder_processor import create_folder_processor
        
        processor = create_folder_processor(
            input_folder="./test_input",
            processed_folder="./test_processed",
            markdown_output_folder="./test_markdown",
            watch_mode=False,
            log_level="INFO"
        )
        
        assert processor is not None, "Folder processor should be created"
        assert processor.input_folder == Path("./test_input")
        assert processor.processed_folder == Path("./test_processed")
        assert processor.markdown_output_folder == Path("./test_markdown")
        assert processor.watch_mode is False
    
    def test_document_validation(self):
        """Test document validation."""
        # Test valid PDF
        pdf_path = Path("examples/test_document.pdf")
        if pdf_path.exists():
            is_valid, message = validate_document_file(pdf_path)
            assert is_valid is True, f"Valid PDF should pass validation: {message}"
        
        # Test valid Word document
        docx_path = Path("examples/test_document.docx")
        if docx_path.exists():
            is_valid, message = validate_document_file(docx_path)
            assert is_valid is True, f"Valid Word document should pass validation: {message}"
        
        # Test invalid file
        non_existent_path = Path("/non/existent/file.pdf")
        is_valid, message = validate_document_file(non_existent_path)
        assert is_valid is False, "Non-existent file should fail validation"
