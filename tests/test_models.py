"""
Tests for the data models.
"""

import pytest
from pathlib import Path
from src.models import (
    ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings,
    DocumentHints, ProvenanceRecord, QualityMetrics, ProcessingDefect,
    RunReport, ConversionResult
)


class TestProcessingRequest:
    """Test ProcessingRequest model."""
    
    def test_valid_request_with_path(self):
        """Test creating a valid request with PDF path."""
        request = ProcessingRequest(
            pdf_path=Path("test.pdf"),
            run_mode=RunMode.PRODUCTION
        )
        assert request.pdf_path == Path("test.pdf")
        assert request.run_mode == RunMode.PRODUCTION
        assert request.pdf_bytes is None
    
    def test_valid_request_with_bytes(self):
        """Test creating a valid request with PDF bytes."""
        pdf_bytes = b"fake pdf content"
        request = ProcessingRequest(
            pdf_bytes=pdf_bytes,
            run_mode=RunMode.EVALUATION
        )
        assert request.pdf_bytes == pdf_bytes
        assert request.pdf_path is None
        assert request.run_mode == RunMode.EVALUATION
    
    def test_invalid_request_no_input(self):
        """Test that request fails without input."""
        with pytest.raises(ValueError, match="Either pdf_path or pdf_bytes must be provided"):
            ProcessingRequest(run_mode=RunMode.PRODUCTION)
    
    def test_request_with_hints(self):
        """Test request with document hints."""
        request = ProcessingRequest(
            pdf_path=Path("test.pdf"),
            doc_hints=DocumentHints(
                contains_math=True,
                contains_tables=True,
                is_scanned=False,
                languages=["en", "es"],
                domain="academic"
            )
        )
        assert request.doc_hints.contains_math is True
        assert request.doc_hints.contains_tables is True
        assert request.doc_hints.is_scanned is False
        assert request.doc_hints.languages == ["en", "es"]
        assert request.doc_hints.domain == "academic"


class TestComplianceConfig:
    """Test ComplianceConfig model."""
    
    def test_default_config(self):
        """Test default compliance configuration."""
        config = ComplianceConfig()
        assert config.classification_tag == "UNCLASSIFIED"
        assert config.pii_redaction is False
        assert config.export_assets is True
    
    def test_custom_config(self):
        """Test custom compliance configuration."""
        config = ComplianceConfig(
            classification_tag="CONFIDENTIAL",
            pii_redaction=True,
            export_assets=False
        )
        assert config.classification_tag == "CONFIDENTIAL"
        assert config.pii_redaction is True
        assert config.export_assets is False


class TestProcessingCeilings:
    """Test ProcessingCeilings model."""
    
    def test_default_ceilings(self):
        """Test default processing ceilings."""
        ceilings = ProcessingCeilings()
        assert ceilings.max_runtime_s == 3600
        assert ceilings.max_memory_mb == 8192
    
    def test_custom_ceilings(self):
        """Test custom processing ceilings."""
        ceilings = ProcessingCeilings(
            max_runtime_s=1800,
            max_memory_mb=4096
        )
        assert ceilings.max_runtime_s == 1800
        assert ceilings.max_memory_mb == 4096


class TestProvenanceRecord:
    """Test ProvenanceRecord model."""
    
    def test_provenance_record(self):
        """Test creating a provenance record."""
        record = ProvenanceRecord(
            page=1,
            bbox=[10.0, 20.0, 100.0, 200.0],
            tool="pymupdf",
            confidence=0.95,
            element_hash="abc123",
            element_type="text",
            content_preview="Sample text content"
        )
        assert record.page == 1
        assert record.bbox == [10.0, 20.0, 100.0, 200.0]
        assert record.tool == "pymupdf"
        assert record.confidence == 0.95
        assert record.element_hash == "abc123"
        assert record.element_type == "text"
        assert record.content_preview == "Sample text content"


class TestQualityMetrics:
    """Test QualityMetrics model."""
    
    def test_quality_metrics(self):
        """Test creating quality metrics."""
        metrics = QualityMetrics(
            cer=0.001,
            wer=0.005,
            table_grits=0.95,
            math_token_match=0.98,
            structure_accuracy=0.99,
            provenance_coverage=1.0
        )
        assert metrics.cer == 0.001
        assert metrics.wer == 0.005
        assert metrics.table_grits == 0.95
        assert metrics.math_token_match == 0.98
        assert metrics.structure_accuracy == 0.99
        assert metrics.provenance_coverage == 1.0


class TestProcessingDefect:
    """Test ProcessingDefect model."""
    
    def test_processing_defect(self):
        """Test creating a processing defect."""
        defect = ProcessingDefect(
            page=1,
            element_type="text",
            description="OCR artifact detected",
            severity="low",
            tool_used="ocr_extractor",
            fallback_applied=True,
            coordinates=[10.0, 20.0, 100.0, 200.0]
        )
        assert defect.page == 1
        assert defect.element_type == "text"
        assert defect.description == "OCR artifact detected"
        assert defect.severity == "low"
        assert defect.tool_used == "ocr_extractor"
        assert defect.fallback_applied is True
        assert defect.coordinates == [10.0, 20.0, 100.0, 200.0]


class TestRunReport:
    """Test RunReport model."""
    
    def test_run_report(self):
        """Test creating a run report."""
        quality_metrics = QualityMetrics()
        compliance_config = ComplianceConfig()
        
        report = RunReport(
            run_id="test_run_123",
            input_file="test.pdf",
            output_dir="./output",
            run_mode=RunMode.PRODUCTION,
            tools_used=["pymupdf", "pdfplumber"],
            tool_versions={"pymupdf": "1.0.0"},
            quality_metrics=quality_metrics,
            defects=[],
            processing_time_s=10.5,
            memory_peak_mb=512.0,
            router_decisions={},
            compliance_applied=compliance_config,
            success=True
        )
        assert report.run_id == "test_run_123"
        assert report.input_file == "test.pdf"
        assert report.output_dir == "./output"
        assert report.run_mode == RunMode.PRODUCTION
        assert report.tools_used == ["pymupdf", "pdfplumber"]
        assert report.tool_versions == {"pymupdf": "1.0.0"}
        assert report.processing_time_s == 10.5
        assert report.memory_peak_mb == 512.0
        assert report.success is True


class TestConversionResult:
    """Test ConversionResult model."""
    
    def test_conversion_result(self):
        """Test creating a conversion result."""
        run_report = RunReport(
            run_id="test_run_123",
            input_file="test.pdf",
            output_dir="./output",
            run_mode=RunMode.PRODUCTION,
            tools_used=[],
            tool_versions={},
            quality_metrics=QualityMetrics(),
            defects=[],
            processing_time_s=10.0,
            memory_peak_mb=512.0,
            router_decisions={},
            compliance_applied=ComplianceConfig(),
            success=True
        )
        
        result = ConversionResult(
            markdown_content="# Test Document\n\nThis is test content.",
            assets_dir=Path("./output/assets"),
            provenance_records=[],
            run_report=run_report,
            output_files={"markdown": Path("./output/document.md")}
        )
        assert result.markdown_content == "# Test Document\n\nThis is test content."
        assert result.assets_dir == Path("./output/assets")
        assert result.provenance_records == []
        assert result.run_report == run_report
        assert result.output_files["markdown"] == Path("./output/document.md")
