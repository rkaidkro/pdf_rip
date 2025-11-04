#!/usr/bin/env python3
"""
Basic usage example for PDF Rip.

This script demonstrates how to use the PDF processing pipeline programmatically.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.processor import PDFProcessor
from src.models import ProcessingRequest, RunMode, ComplianceConfig, DocumentHints


def main():
    """Demonstrate basic PDF processing."""
    
    # Check if a PDF file was provided
    if len(sys.argv) < 2:
        print("Usage: python basic_usage.py <path_to_pdf>")
        print("Example: python basic_usage.py sample.pdf")
        return
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"Error: PDF file '{pdf_path}' does not exist.")
        return
    
    print(f"Processing PDF: {pdf_path}")
    
    # Create output directory
    output_dir = Path("example_output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize processor
    processor = PDFProcessor(output_dir)
    
    # Create processing request
    request = ProcessingRequest(
        pdf_path=pdf_path,
        run_mode=RunMode.PRODUCTION,
        compliance=ComplianceConfig(
            classification_tag="UNCLASSIFIED",
            pii_redaction=False
        ),
        doc_hints=DocumentHints(
            contains_math=False,
            contains_tables=True,
            is_scanned=False
        )
    )
    
    print("Starting PDF processing...")
    
    try:
        # Process the PDF
        result = processor.process(request)
        
        if result.run_report.success:
            print("\n✅ Processing completed successfully!")
            print(f"📄 Markdown saved to: {result.output_files['markdown']}")
            print(f"📊 Report saved to: {result.output_files['report']}")
            print(f"🔍 Provenance saved to: {result.output_files['provenance']}")
            
            # Display quality metrics
            metrics = result.run_report.quality_metrics
            print(f"\n📈 Quality Metrics:")
            print(f"   Structure Accuracy: {metrics.structure_accuracy:.3f}")
            print(f"   Provenance Coverage: {metrics.provenance_coverage:.3f}")
            print(f"   Table GriTS Score: {metrics.table_grits:.3f}")
            
            # Display processing stats
            print(f"\n⏱️  Processing Statistics:")
            print(f"   Processing Time: {result.run_report.processing_time_s:.2f}s")
            print(f"   Peak Memory: {result.run_report.memory_peak_mb:.1f} MB")
            print(f"   Tools Used: {', '.join(result.run_report.tools_used)}")
            
            # Show first few lines of markdown
            print(f"\n📝 Markdown Preview (first 200 characters):")
            preview = result.markdown_content[:200]
            if len(result.markdown_content) > 200:
                preview += "..."
            print(f"   {preview}")
            
        else:
            print(f"\n❌ Processing failed: {result.run_report.error_message}")
            
    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")


if __name__ == "__main__":
    main()
