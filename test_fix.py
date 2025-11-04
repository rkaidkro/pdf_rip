#!/usr/bin/env python3
"""
Test script to reprocess failed files and verify the fix.
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

def test_reprocessing():
    """Test reprocessing of failed files."""
    
    # Get all PDF files from processed/success
    processed_dir = Path("processed/success")
    pdf_files = list(processed_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to test")
    print("=" * 60)
    
    # Test with first 5 files
    test_files = pdf_files[:5]
    
    success_count = 0
    failure_count = 0
    
    for pdf_file in test_files:
        print(f"\nTesting: {pdf_file.name}")
        print("-" * 40)
        
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
        processor = DocumentProcessor(Path("./test_output"))
        
        try:
            # Process document
            result = processor.process(request)
            
            if result.run_report.success:
                print(f"✅ SUCCESS: {len(result.markdown_content)} characters extracted")
                success_count += 1
            else:
                print(f"❌ FAILED: {result.run_report.error_message}")
                failure_count += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failure_count += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results:")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {failure_count}")
    print(f"📊 Success Rate: {success_count/(success_count+failure_count)*100:.1f}%")

if __name__ == "__main__":
    test_reprocessing()
