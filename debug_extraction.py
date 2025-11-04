#!/usr/bin/env python3
"""
Debug script to test PDF text extraction.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from extractors import TextExtractor
    from utils import validate_pdf_file
except ImportError:
    # Fallback for direct execution
    from src.extractors import TextExtractor
    from src.utils import validate_pdf_file

def test_pdf_extraction(pdf_path: str):
    """Test PDF text extraction."""
    pdf_file = Path(pdf_path)
    
    print(f"Testing PDF: {pdf_file}")
    print("=" * 50)
    
    # Validate PDF
    is_valid, message = validate_pdf_file(pdf_file)
    print(f"Validation: {message}")
    
    if not is_valid:
        print("❌ PDF is not valid")
        return
    
    # Test extraction
    extractor = TextExtractor()
    
    try:
        result = extractor.extract_text(pdf_file)
        
        print(f"✅ Extraction successful")
        print(f"Content length: {len(result['content'])}")
        print(f"Provenance records: {len(result['provenance'])}")
        
        if result['content'].strip():
            print("✅ Content extracted successfully")
            print(f"First 200 characters: {result['content'][:200]}...")
        else:
            print("❌ No content extracted")
            
        # Check provenance
        if result['provenance']:
            print(f"✅ Provenance records created: {len(result['provenance'])}")
        else:
            print("❌ No provenance records")
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_extraction.py <pdf_file>")
        sys.exit(1)
    
    test_pdf_extraction(sys.argv[1])
