#!/usr/bin/env python3
"""
Simple test script to verify the output structure.
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

def test_output_structure():
    """Test the output structure with a simple document."""
    
    # Use a test document
    test_file = Path("processed/success/Aditya_Agashe - cl_1756546765.docx")
    
    if not test_file.exists():
        print("❌ Test file not found")
        return
    
    print(f"Testing with: {test_file}")
    
    # Create processing request
    request = ProcessingRequest(
        document_path=test_file,
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
    
    # Initialize processor with test output directory
    output_dir = Path("./test_output")
    processor = DocumentProcessor(output_dir)
    
    try:
        # Process document
        result = processor.process(request)
        
        print(f"✅ Processing completed")
        print(f"Success: {result.run_report.success}")
        print(f"Markdown content length: {len(result.markdown_content)}")
        
        # Check output structure
        expected_folder = output_dir / "Aditya_Agashe - cl"
        expected_markdown = expected_folder / "Aditya_Agashe - cl.md"
        
        print(f"\nChecking output structure:")
        print(f"Expected folder: {expected_folder}")
        print(f"Expected markdown: {expected_markdown}")
        
        if expected_folder.exists():
            print(f"✅ Folder exists: {expected_folder}")
        else:
            print(f"❌ Folder missing: {expected_folder}")
            return
        
        if expected_markdown.exists():
            print(f"✅ Markdown file exists: {expected_markdown}")
            with open(expected_markdown, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✅ Markdown content length: {len(content)}")
        else:
            print(f"❌ Markdown file missing: {expected_markdown}")
            return
        
        # Check for other files
        other_files = list(expected_folder.glob("*"))
        print(f"\nFiles in folder:")
        for file in other_files:
            if file.name != "Aditya_Agashe - cl.md":
                print(f"  - {file.name}")
        
        # Check for files outside the folder (should be none)
        files_outside = list(output_dir.glob("*.md"))
        if files_outside:
            print(f"\n❌ Files found outside folder:")
            for file in files_outside:
                print(f"  - {file}")
        else:
            print(f"\n✅ No files outside folder")
        
        print(f"\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_output_structure()
