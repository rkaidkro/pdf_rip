"""
Data models for the PDF processing pipeline.
"""

from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime


class RunMode(str, Enum):
    """Processing modes for the pipeline."""
    PRODUCTION = "production"
    EVALUATION = "evaluation"
    BEDDING = "bedding"


class ComplianceConfig(BaseModel):
    """Compliance and governance configuration."""
    classification_tag: str = Field(default="UNCLASSIFIED", description="Document classification")
    pii_redaction: bool = Field(default=False, description="Enable PII redaction")
    export_assets: bool = Field(default=True, description="Export extracted assets")


class ProcessingCeilings(BaseModel):
    """Resource limits for processing."""
    max_runtime_s: int = Field(default=3600, description="Maximum runtime in seconds")
    max_memory_mb: int = Field(default=8192, description="Maximum memory usage in MB")


class DocumentHints(BaseModel):
    """Hints about document content to guide processing."""
    contains_math: Optional[bool] = None
    contains_tables: Optional[bool] = None
    is_scanned: Optional[bool] = None
    languages: List[str] = Field(default_factory=list)
    domain: Optional[str] = None


class ProcessingRequest(BaseModel):
    """Main processing request model."""
    # Support both PDF and Word documents
    pdf_path: Optional[Path] = None
    pdf_bytes: Optional[bytes] = None
    document_path: Optional[Path] = None  # Generic document path for any format
    document_bytes: Optional[bytes] = None  # Generic document bytes for any format
    original_filename: Optional[str] = None  # Original filename for output naming
    run_mode: RunMode = RunMode.PRODUCTION
    doc_hints: DocumentHints = Field(default_factory=DocumentHints)
    allowed_tools: List[str] = Field(default_factory=list)
    ceilings: ProcessingCeilings = Field(default_factory=ProcessingCeilings)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    # Vision validation options
    anthropic_api_key: Optional[str] = None  # API key for OpenAI Vision validation (kept for backward compatibility)
    openai_api_key: Optional[str] = None  # API key for OpenAI Vision validation
    enable_vision_validation: bool = Field(default=False, description="Enable OpenAI Vision validation")

    @model_validator(mode='after')
    def validate_input(self):
        """Ensure at least one input source is provided."""
        has_path = self.pdf_path is not None or self.document_path is not None
        has_bytes = self.pdf_bytes is not None or self.document_bytes is not None
        
        if not has_path and not has_bytes:
            raise ValueError("Either a document path or document bytes must be provided")
        return self


class ProvenanceRecord(BaseModel):
    """Provenance tracking for individual elements."""
    page: int
    bbox: List[float] = Field(description="[x1, y1, x2, y2] coordinates")
    tool: str
    confidence: float
    element_hash: str
    element_type: str
    content_preview: str = Field(default="", max_length=100)


class QualityMetrics(BaseModel):
    """Quality metrics for the conversion."""
    cer: float = Field(default=0.0, description="Character Error Rate")
    wer: float = Field(default=0.0, description="Word Error Rate")
    table_grits: float = Field(default=0.0, description="Table structure accuracy")
    math_token_match: float = Field(default=0.0, description="Math equation accuracy")
    structure_accuracy: float = Field(default=0.0, description="Heading/list structure accuracy")
    provenance_coverage: float = Field(default=0.0, description="Percentage of elements with provenance")
    # Vision validation metrics
    vision_confidence: Optional[float] = Field(default=None, description="Vision-based confidence score")
    content_completeness: Optional[float] = Field(default=None, description="Content completeness from vision validation")
    image_caption_accuracy: Optional[float] = Field(default=None, description="Image caption accuracy from vision validation")


class ProcessingDefect(BaseModel):
    """Record of processing defects or issues."""
    page: int
    element_type: str
    description: str
    severity: str = Field(description="low|medium|high|critical")
    tool_used: str
    fallback_applied: bool = False
    coordinates: Optional[List[float]] = None


class RunReport(BaseModel):
    """Comprehensive report of the processing run."""
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    input_file: str
    output_dir: str
    run_mode: RunMode
    tools_used: List[str]
    tool_versions: Dict[str, str]
    quality_metrics: QualityMetrics
    defects: List[ProcessingDefect] = Field(default_factory=list)
    processing_time_s: float
    memory_peak_mb: float
    router_decisions: Dict[str, Any] = Field(default_factory=dict)
    compliance_applied: ComplianceConfig
    success: bool = True
    error_message: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "run_id": "run_123",
                    "timestamp": "2025-01-01T00:00:00",
                    "input_file": "test.pdf",
                    "output_dir": "./output",
                    "run_mode": "production",
                    "tools_used": ["pymupdf"],
                    "tool_versions": {"pymupdf": "1.0.0"},
                    "quality_metrics": {
                        "cer": 0.0,
                        "wer": 0.0,
                        "table_grits": 0.0,
                        "math_token_match": 0.0,
                        "structure_accuracy": 0.0,
                        "provenance_coverage": 0.0
                    },
                    "defects": [],
                    "processing_time_s": 10.0,
                    "memory_peak_mb": 512.0,
                    "router_decisions": {},
                    "compliance_applied": {
                        "classification_tag": "UNCLASSIFIED",
                        "pii_redaction": False,
                        "export_assets": True
                    },
                    "success": True
                }
            ]
        }
    )


class ConversionResult(BaseModel):
    """Result of a PDF conversion operation."""
    markdown_content: str
    assets_dir: Path
    provenance_records: List[ProvenanceRecord]
    run_report: RunReport
    output_files: Dict[str, Path] = Field(default_factory=dict)
