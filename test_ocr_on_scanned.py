#!/usr/bin/env python3
"""Test script to verify OCR extraction works on scanned PDFs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors import TextExtractor
import fitz

def test_pdf_for_scanning(pdf_path: Path):
    """Test if a PDF is scanned and verify OCR extraction."""
    print(f"\n{'='*60}")
    print(f"Testing PDF: {pdf_path.name}")
    print(f"{'='*60}")
    
    # Open PDF and check for text layer
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    text = page.get_text()
    
    has_text = len(text.strip()) > 0
    is_scanned = len(text.strip()) < 50
    
    print(f"Has text layer: {has_text}")
    print(f"Text length: {len(text)}")
    print(f"Is scanned (needs OCR): {is_scanned}")
    
    if text.strip():
        print(f"\nFirst 200 chars from text layer:")
        print(text[:200])
    
    # Test OCR extraction
    print(f"\n{'='*60}")
    print("Testing OCR Extraction")
    print(f"{'='*60}")
    
    extractor = TextExtractor()
    try:
        result = extractor.extract_with_ocr(pdf_path)
        print(f"OCR extracted {len(result['content'])} characters")
        print(f"Provenance records: {len(result['provenance'])}")
        
        if result['content']:
            print(f"\nFirst 300 chars from OCR:")
            print(result['content'][:300])
        else:
            print("WARNING: OCR extraction returned no content!")
            
    except Exception as e:
        print(f"ERROR: OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()
    
    doc.close()

if __name__ == "__main__":
    # Test with provided PDF or find Felicity PDF
    test_pdfs = []
    
    # Check for Felicity PDF
    felicity_paths = [
        Path("input") / "Felicitys.pdf",
        Path("input") / "felicitys.pdf",
        Path("processed/success") / "Felicitys.pdf",
        Path("processed/failed") / "Felicitys.pdf",
    ]
    
    for path in felicity_paths:
        if path.exists():
            test_pdfs.append(path)
            break
    
    # If no Felicity PDF, use a test PDF
    if not test_pdfs:
        test_pdf = Path("processed/success/Joseph Hollinshead - cl_1756545586.pdf")
        if test_pdf.exists():
            test_pdfs.append(test_pdf)
    
    if not test_pdfs:
        print("No PDFs found to test!")
        sys.exit(1)
    
    for pdf_path in test_pdfs:
        test_pdf_for_scanning(pdf_path)

