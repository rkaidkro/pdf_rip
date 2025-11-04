#!/usr/bin/env python3
"""
Create a simple test PDF for demonstration purposes.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from pathlib import Path

def create_test_pdf(output_path: str = "test_document.pdf"):
    """Create a simple test PDF with various content types."""
    
    # Create the PDF
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Page 1: Title and basic content
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1*inch, height-1.5*inch, "Sample Document")
    
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height-2*inch, "This is a sample document created for testing the PDF Rip pipeline.")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height-2.5*inch, "Introduction")
    
    c.setFont("Helvetica", 12)
    text = """This document contains various types of content to test the PDF processing capabilities:

• Text content with different formatting
• Lists and bullet points
• Tables with structured data
• Mathematical equations (simulated)
• Contact information for PII testing

The goal is to verify that the PDF Rip pipeline can accurately extract and convert all these elements to Markdown format."""
    
    y_position = height-3*inch
    for line in text.split('\n'):
        c.drawString(1*inch, y_position, line)
        y_position -= 0.2*inch
    
    # Add some contact info for PII testing
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, height-6*inch, "Contact Information")
    
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height-6.3*inch, "Email: test@example.com")
    c.drawString(1*inch, height-6.6*inch, "Phone: (555) 123-4567")
    c.drawString(1*inch, height-6.9*inch, "Address: 123 Test Street, Test City, TC 12345")
    
    c.showPage()
    
    # Page 2: Table
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height-1*inch, "Sample Table")
    
    # Draw table headers
    headers = ["Name", "Age", "Department", "Salary"]
    x_positions = [1*inch, 2.5*inch, 4*inch, 5.5*inch]
    
    c.setFont("Helvetica-Bold", 12)
    for i, header in enumerate(headers):
        c.drawString(x_positions[i], height-1.5*inch, header)
    
    # Draw table data
    data = [
        ["John Doe", "30", "Engineering", "$75,000"],
        ["Jane Smith", "28", "Marketing", "$65,000"],
        ["Bob Johnson", "35", "Sales", "$80,000"],
        ["Alice Brown", "32", "HR", "$70,000"]
    ]
    
    c.setFont("Helvetica", 12)
    for row_idx, row in enumerate(data):
        y_pos = height-(1.8 + row_idx*0.3)*inch
        for col_idx, cell in enumerate(row):
            c.drawString(x_positions[col_idx], y_pos, cell)
    
    # Add some mathematical content
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, height-4*inch, "Mathematical Content")
    
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height-4.3*inch, "Sample equation: E = mc²")
    c.drawString(1*inch, height-4.6*inch, "Another equation: ∫ f(x) dx = F(x) + C")
    c.drawString(1*inch, height-4.9*inch, "Summation: Σ(i=1 to n) i = n(n+1)/2")
    
    c.showPage()
    
    # Page 3: Code and formatting
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height-1*inch, "Code Examples")
    
    c.setFont("Courier", 10)
    code_example = """def hello_world():
    print("Hello, World!")
    
class Example:
    def __init__(self):
        self.name = "test"
    
    def get_name(self):
        return self.name"""
    
    y_pos = height-1.5*inch
    for line in code_example.split('\n'):
        c.drawString(1*inch, y_pos, line)
        y_pos -= 0.15*inch
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, height-4*inch, "Conclusion")
    
    c.setFont("Helvetica", 12)
    conclusion = """This document demonstrates various content types that the PDF Rip pipeline should be able to process:

1. Structured text with headings
2. Lists and bullet points
3. Tables with data
4. Mathematical notation
5. Code blocks
6. Contact information (for PII testing)

The pipeline should convert all of this content to clean, well-formatted Markdown while preserving the structure and relationships between elements."""
    
    y_pos = height-4.3*inch
    for line in conclusion.split('\n'):
        c.drawString(1*inch, y_pos, line)
        y_pos -= 0.2*inch
    
    c.save()
    print(f"Test PDF created: {output_path}")

if __name__ == "__main__":
    # Create the examples directory if it doesn't exist
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    
    # Create the test PDF
    create_test_pdf("examples/test_document.pdf")
    print("Test PDF created successfully!")
