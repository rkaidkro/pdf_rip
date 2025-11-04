"""
Vision-based document validation using OpenAI Vision API.
Provides enhanced quality checking by comparing original documents with extracted content.
"""

import base64
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
import requests
from pydantic import BaseModel, Field

from .models import QualityMetrics, ProcessingDefect


class VisionValidationResult(BaseModel):
    """Result of vision-based validation."""
    confidence_score: float = Field(description="Overall confidence in extraction quality (0-1)")
    content_completeness: float = Field(description="Percentage of content successfully extracted")
    formatting_accuracy: float = Field(description="Accuracy of formatting preservation")
    table_accuracy: float = Field(description="Table structure and data accuracy")
    image_caption_accuracy: float = Field(description="Image caption extraction accuracy")
    defects: List[ProcessingDefect] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    validation_time: float = Field(description="Time taken for validation in seconds")


class VisionValidator:
    """Vision-based document validation using OpenAI Vision API."""
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize the vision validator.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use for validation (defaults to gpt-4o)
        """
        self.api_key = api_key
        # Use environment variable or default to a known working model
        import os
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def _convert_document_to_image(self, document_path: Path) -> Optional[bytes]:
        """Convert document to image for OpenAI Vision processing."""
        try:
            file_extension = document_path.suffix.lower()
            
            if file_extension == '.pdf':
                # Convert PDF to image using pdf2image
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(document_path, first_page=1, last_page=1)
                    if images:
                        # Convert PIL image to bytes
                        import io
                        img_byte_arr = io.BytesIO()
                        images[0].save(img_byte_arr, format='PNG')
                        return img_byte_arr.getvalue()
                except ImportError:
                    logger.warning("pdf2image not available, skipping PDF conversion")
                    return None
                except Exception as e:
                    logger.error(f"Failed to convert PDF to image: {str(e)}")
                    return None
            
            elif file_extension in ['.docx', '.doc']:
                # For Word documents, we'll need a different approach
                # For now, return None to indicate we can't process Word docs
                logger.warning("Word document conversion to image not implemented yet")
                return None
            
            else:
                logger.warning(f"Unsupported file type for vision validation: {file_extension}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting document to image: {str(e)}")
            return None
    
    def validate_extraction(self, 
                          original_doc_path: Path, 
                          extracted_markdown: str,
                          document_type: str = "document") -> VisionValidationResult:
        """
        Validate document extraction using OpenAI Vision.
        
        Args:
            original_doc_path: Path to original document
            extracted_markdown: Extracted markdown content
            document_type: Type of document (cv, cl, etc.)
            
        Returns:
            VisionValidationResult with validation scores and feedback
        """
        start_time = time.time()
        
        try:
            # Convert document to image for OpenAI Vision
            image_bytes = self._convert_document_to_image(original_doc_path)
            if not image_bytes:
                raise Exception("Failed to convert document to image for vision validation")
            
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            media_type = "image/png"  # We convert to PNG format
            
            # Create validation prompt
            prompt = self._create_validation_prompt(extracted_markdown, document_type)
            
            # Prepare the API request for OpenAI
            payload = {
                "model": self.model,
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Make API call
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {})
                error_type = error_msg.get('type', 'unknown_error')
                error_message = error_msg.get('message', response.text)
                
                # Handle model not found errors specifically
                if response.status_code == 404:
                    logger.warning(f"Model '{self.model}' not found. Available models may have changed.")
                    logger.warning(f"Try setting OPENAI_MODEL environment variable to a valid model name.")
                    logger.warning(f"Common models: gpt-4o, gpt-4-turbo, gpt-4-vision-preview")
                    raise Exception(f"Model not found: {self.model}. Error: {error_message}")
                
                logger.error(f"API Error {response.status_code}: {response.text}")
                raise Exception(f"API Error {response.status_code}: {error_message or response.text}")
            
            response.raise_for_status()
            
            # Parse response (OpenAI format)
            result_data = response.json()
            content = result_data['choices'][0]['message']['content']
            
            # Parse the structured response
            validation_result = self._parse_validation_response(content)
            validation_result.validation_time = time.time() - start_time
            
            logger.info(f"Vision validation completed in {validation_result.validation_time:.2f}s")
            logger.info(f"Confidence score: {validation_result.confidence_score:.2f}")
            
            return validation_result
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Vision validation failed: {error_str}")
            
            # Determine severity based on error type
            # API errors (model not found, etc.) are less critical than content extraction errors
            if "Model not found" in error_str or "404" in error_str or "API Error" in error_str:
                severity = "medium"  # Don't block processing for API issues
                logger.warning("Vision validation API error - this won't block document processing")
            else:
                severity = "high"  # Content-related validation failures are more serious
            
            # Return a default result on failure
            return VisionValidationResult(
                confidence_score=0.0,
                content_completeness=0.0,
                formatting_accuracy=0.0,
                table_accuracy=0.0,
                image_caption_accuracy=0.0,
                defects=[
                    ProcessingDefect(
                        page=1,
                        element_type="vision_validation",
                        description=f"Vision validation failed: {error_str}",
                        severity=severity,
                        tool_used="claude_vision"
                    )
                ],
                validation_time=time.time() - start_time
            )
    
    def _create_validation_prompt(self, extracted_markdown: str, document_type: str) -> str:
        """Create the validation prompt for OpenAI Vision."""
        
        return f"""You are an expert document analysis system. I need you to validate the quality of document extraction by comparing the original document (image) with the extracted markdown text.

**Document Type**: {document_type.upper()}

**Extracted Markdown**:
```
{extracted_markdown}
```

**Your Task**: Analyze the original document and compare it with the extracted markdown to assess extraction quality.

**Please provide a structured analysis in JSON format with the following fields**:

{{
    "confidence_score": <float 0-1, overall confidence in extraction quality>,
    "content_completeness": <float 0-1, percentage of content successfully extracted>,
    "formatting_accuracy": <float 0-1, accuracy of formatting preservation>,
    "table_accuracy": <float 0-1, table structure and data accuracy>,
    "image_caption_accuracy": <float 0-1, image caption extraction accuracy>,
    "defects": [
        {{
            "page": <int>,
            "element_type": <string>,
            "description": <string>,
            "severity": <"low"|"medium"|"high"|"critical">,
            "tool_used": "openai_vision"
        }}
    ],
    "suggestions": [
        <string, improvement suggestions>
    ]
}}

**Assessment Criteria**:
1. **Content Completeness**: Are all text elements, headings, and content captured?
2. **Formatting Accuracy**: Are headings, lists, bold/italic text preserved correctly?
3. **Table Accuracy**: Are tables extracted with proper structure and data?
4. **Image Captions**: Are any images properly captioned or described?
5. **Layout Preservation**: Is the logical flow and structure maintained?

**Defect Severity Levels**:
- **low**: Minor formatting issues, cosmetic problems
- **medium**: Some content missing or incorrectly formatted
- **high**: Significant content missing or major formatting errors
- **critical**: Critical information lost or completely incorrect extraction

Please provide only the JSON response, no additional text."""
    
    def _parse_validation_response(self, response_text: str) -> VisionValidationResult:
        """Parse the structured response from OpenAI Vision."""
        
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Convert defects to ProcessingDefect objects
            defects = []
            for defect_data in data.get('defects', []):
                defect = ProcessingDefect(
                    page=defect_data.get('page', 1),
                    element_type=defect_data.get('element_type', 'unknown'),
                    description=defect_data.get('description', ''),
                    severity=defect_data.get('severity', 'medium'),
                    tool_used=defect_data.get('tool_used', 'claude_vision')
                )
                defects.append(defect)
            
            return VisionValidationResult(
                confidence_score=data.get('confidence_score', 0.0),
                content_completeness=data.get('content_completeness', 0.0),
                formatting_accuracy=data.get('formatting_accuracy', 0.0),
                table_accuracy=data.get('table_accuracy', 0.0),
                image_caption_accuracy=data.get('image_caption_accuracy', 0.0),
                defects=defects,
                suggestions=data.get('suggestions', []),
                validation_time=0.0  # Will be set by the calling method
            )
            
        except Exception as e:
            logger.error(f"Failed to parse vision validation response: {str(e)}")
            logger.error(f"Response text: {response_text}")
            
            # Return a default result
            return VisionValidationResult(
                confidence_score=0.0,
                content_completeness=0.0,
                formatting_accuracy=0.0,
                table_accuracy=0.0,
                image_caption_accuracy=0.0,
                defects=[
                    ProcessingDefect(
                        page=1,
                        element_type="vision_validation",
                        description=f"Failed to parse vision validation response: {str(e)}",
                        severity="high",
                        tool_used="claude_vision"
                    )
                ]
            )
    
    def enhance_quality_metrics(self, 
                              base_metrics: QualityMetrics, 
                              vision_result: VisionValidationResult) -> QualityMetrics:
        """Enhance base quality metrics with vision validation results."""
        
        # Combine vision validation scores with existing metrics
        enhanced_metrics = QualityMetrics(
            cer=base_metrics.cer,
            wer=base_metrics.wer,
            table_grits=max(base_metrics.table_grits, vision_result.table_accuracy),
            math_token_match=base_metrics.math_token_match,
            structure_accuracy=max(base_metrics.structure_accuracy, vision_result.formatting_accuracy),
            provenance_coverage=base_metrics.provenance_coverage
        )
        
        # Add vision-specific metrics
        enhanced_metrics.vision_confidence = vision_result.confidence_score
        enhanced_metrics.content_completeness = vision_result.content_completeness
        enhanced_metrics.image_caption_accuracy = vision_result.image_caption_accuracy
        
        return enhanced_metrics
