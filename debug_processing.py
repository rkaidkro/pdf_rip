#!/usr/bin/env python3
"""
Debug script to test the full processing pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from processor import DocumentProcessor
    from models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints
    from utils import validate_document_file
except ImportError:
    from src.processor import DocumentProcessor
    from src.models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints
    from src.utils import validate_document_file

def test_full_processing(pdf_path: str):
    """Test the full processing pipeline."""
    pdf_file = Path(pdf_path)
    
    print(f"Testing full processing: {pdf_file}")
    print("=" * 60)
    
    # Validate document
    is_valid, message = validate_document_file(pdf_file)
    print(f"Validation: {message}")
    
    if not is_valid:
        print("❌ Document is not valid")
        return
    
    # Create processing request
    request = ProcessingRequest(
        document_path=pdf_file,
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
    
    # Initialize processor
    processor = DocumentProcessor(Path("./debug_output"))
    
    try:
        # Process document
        result = processor.process(request)
        
        print(f"✅ Processing completed")
        print(f"Success: {result.run_report.success}")
        print(f"Markdown content length: {len(result.markdown_content)}")
        print(f"Defects: {len(result.run_report.defects)}")
        
        if result.run_report.defects:
            print("Defects found:")
            for defect in result.run_report.defects:
                print(f"  - {defect.severity}: {defect.description}")
        
        if result.markdown_content.strip():
            print("✅ Markdown content generated successfully")
            print(f"First 300 characters: {result.markdown_content[:300]}...")
        else:
            print("❌ No markdown content generated")
            
        # Check extraction result
        print(f"\nExtraction details:")
        print(f"Text content length: {len(result.markdown_content)}")
        print(f"Provenance records: {len(result.provenance_records)}")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_processing.py <pdf_file>")
        sys.exit(1)
    
    test_full_processing(sys.argv[1])
