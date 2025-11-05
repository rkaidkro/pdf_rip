#!/usr/bin/env python3
"""
Test script for vision validation functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from src.vision_validator import VisionValidator
from src.models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints

def test_vision_validation():
    """Test vision validation with a sample document."""
    
    # API key from environment
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable not set")
        print("   Please set one of these in your .env file or environment")
        return
    
    # Test document (update path to your test document)
    test_doc = Path("examples/test_document.pdf")
    
    # Sample extracted markdown (using anonymized example data)
    sample_markdown = """[Date]
[Company]
[Location]
Re: Application for the position of Senior Software Developer
Dear Sir/Madam,
I am interested in applying for the position of Senior Software Developer. I am certain that my qualification and experience is at par with the job requirement. Hereby I am providing you with a brief overview of my skill set.
I finished my Masters in Information Technology from [University] with distinction average. I have more than 15 years' experience working with Agile, Scrum and Kanban methodologies in various organizations.
I have built both the front-end and back-end of applications. The front end was written in React/Typescript running on NodeJS server. Moreover, I have developed CI pipelines using GitHub actions. The backend RESTful APIs were written in Java 17 / Spring boot 3. I have used multiple AWS services such as S3, AWS Lambda, API Gateway, DynamoDB etc which were provisioned using AWS CDK. I have also written IaC code using Terraform and am familiar with Python programming language.
I have excellent communication skills developed through my work experience. I am a dedicated team player who enjoys the company and support of my peers while being able to manage my priorities and work with minimal supervision.
I look forward to discussing with you in person how my abilities can best serve your needs. Please contact me for further information.
Thank you for your consideration and I look forward to hearing from you soon.
Yours sincerely,
[Name]"""
    
    print("🧪 Testing Vision Validation...")
    print(f"📄 Test document: {test_doc}")
    print(f"📝 Sample markdown length: {len(sample_markdown)} characters")
    print("=" * 60)
    
    try:
        # Initialize vision validator
        validator = VisionValidator(api_key)
        print("✅ Vision validator initialized")
        
        # Perform validation
        print("🔍 Performing vision validation...")
        result = validator.validate_extraction(test_doc, sample_markdown, "cl")
        
        # Display results
        print("=" * 60)
        print("📊 VISION VALIDATION RESULTS:")
        print(f"🎯 Confidence Score: {result.confidence_score:.2f}")
        print(f"📋 Content Completeness: {result.content_completeness:.2f}")
        print(f"🎨 Formatting Accuracy: {result.formatting_accuracy:.2f}")
        print(f"📊 Table Accuracy: {result.table_accuracy:.2f}")
        print(f"🖼️  Image Caption Accuracy: {result.image_caption_accuracy:.2f}")
        print(f"⏱️  Validation Time: {result.validation_time:.2f}s")
        
        if result.defects:
            print("\n⚠️  DEFECTS FOUND:")
            for defect in result.defects:
                print(f"  - [{defect.severity.upper()}] {defect.description}")
        
        if result.suggestions:
            print("\n💡 SUGGESTIONS:")
            for suggestion in result.suggestions:
                print(f"  - {suggestion}")
        
        print("=" * 60)
        print("✅ Vision validation test completed!")
        
    except Exception as e:
        print(f"❌ Vision validation test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vision_validation()
