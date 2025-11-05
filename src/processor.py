"""
Main PDF processing engine with intelligent routing and quality assurance.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from .models import (
    ProcessingRequest, ConversionResult, RunReport, QualityMetrics,
    ProcessingDefect, ProvenanceRecord, RunMode
)
from .utils import (
    setup_logging, generate_run_id, get_memory_usage, Timer,
    detect_document_characteristics, validate_document_file, ensure_directory,
    save_jsonl, calculate_cer, calculate_wer
)
from .extractors import (
    TextExtractor, TableExtractor, ImageExtractor, MathExtractor
)
from .quality import QualityAssurance
from .compliance import ComplianceGuard
from .vision_validator import VisionValidator


class DocumentProcessor:
    """Main document processing engine with intelligent routing for PDF and Word documents."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        ensure_directory(self.output_dir)
        
        # Initialize PDF extractors
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.math_extractor = MathExtractor()
        
        # Initialize Word extractors
        try:
            from .word_extractors import WordTextExtractor, WordTableExtractor, WordImageExtractor
            self.word_text_extractor = WordTextExtractor()
            self.word_table_extractor = WordTableExtractor()
            self.word_image_extractor = WordImageExtractor()
        except ImportError:
            logger.warning("Word processing libraries not available")
            self.word_text_extractor = None
            self.word_table_extractor = None
            self.word_image_extractor = None
        
        # Initialize quality assurance
        self.qa = QualityAssurance()
        
        # Initialize compliance guard
        self.compliance = ComplianceGuard()
        
        # Initialize vision validator (will be set up per request)
        self.vision_validator = None
        
        # Track processing state
        self.current_run_id = None
        self.start_time = None
        self.peak_memory = 0.0
        
    def process(self, request: ProcessingRequest) -> ConversionResult:
        """Process a document (PDF or Word) according to the request specifications."""
        self.current_run_id = generate_run_id()
        self.start_time = time.time()
        
        # Determine document type
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        if document_path:
            document_type = self._get_document_type(document_path)
            logger.info(f"Starting {document_type} processing run {self.current_run_id}")
            logger.info(f"Mode: {request.run_mode}, Input: {document_path}")
        else:
            document_type = "PDF"  # Default for bytes input
            logger.info(f"Starting PDF processing run {self.current_run_id}")
            logger.info(f"Mode: {request.run_mode}, Input: bytes")
        
        try:
            # Validate input
            if document_path:
                is_valid, message = validate_document_file(document_path)
                if not is_valid:
                    raise ValueError(f"Invalid document: {message}")
            
            # Detect document characteristics
            with Timer("Document analysis"):
                characteristics = self._analyze_document(request, document_type)
            
            # Route to appropriate processing pipeline
            with Timer("Content extraction"):
                extraction_result = self._route_and_extract(request, characteristics, document_type)
            
            # Apply final LLM verification pass to fix any missing text
            api_key = request.openai_api_key or request.anthropic_api_key
            if api_key and extraction_result.get("text_content"):
                with Timer("Final LLM verification"):
                    logger.info("Running final LLM verification pass to ensure complete text extraction")
                    verified_text = self._final_llm_verification(request, extraction_result["text_content"], api_key)
                    if verified_text:
                        extraction_result["text_content"] = verified_text
                        logger.info("Final LLM verification completed and fixes applied")
            
            # Apply quality assurance
            with Timer("Quality assurance"):
                qa_result = self._apply_quality_assurance(
                    extraction_result, request.run_mode
                )
            
            # Apply vision validation if enabled (only for PDFs, not Word docs)
            document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
            is_pdf = document_path and document_path.suffix.lower() == '.pdf'
            
            if request.enable_vision_validation and (request.openai_api_key or request.anthropic_api_key) and is_pdf:
                with Timer("Vision validation"):
                    vision_result = self._apply_vision_validation(
                        request, extraction_result, qa_result
                    )
                    # Enhance quality metrics with vision validation
                    qa_result["qa_metrics"] = self._enhance_metrics_with_vision(
                        qa_result["qa_metrics"], vision_result
                    )
            elif is_pdf == False:
                logger.info("Skipping vision validation for Word documents (not supported)")
            
            # Apply compliance checks
            with Timer("Compliance checks"):
                compliance_result = self._apply_compliance(
                    qa_result, request.compliance
                )
            
            # Generate final output
            with Timer("Output generation"):
                result = self._generate_output(compliance_result, request)
            
            # Update memory tracking
            self.peak_memory = max(self.peak_memory, get_memory_usage())
            
            logger.info(f"Processing completed successfully in {time.time() - self.start_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            return self._create_error_result(request, str(e))
    
    def _get_document_type(self, document_path: Path) -> str:
        """Determine the type of document based on file extension."""
        suffix = document_path.suffix.lower()
        if suffix == '.pdf':
            return "PDF"
        elif suffix in ['.docx', '.doc']:
            return "Word"
        else:
            return "Unknown"
    
    def _analyze_document(self, request: ProcessingRequest, document_type: str) -> Dict[str, Any]:
        """Analyze document characteristics to guide processing."""
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        
        if document_path:
            if document_type == "PDF":
                characteristics = detect_document_characteristics(document_path)
            elif document_type == "Word":
                from .word_extractors import detect_word_document_characteristics
                characteristics = detect_word_document_characteristics(document_path)
            else:
                # Fallback for unknown types
                characteristics = {
                    "is_scanned": False,
                    "has_text_layer": True,
                    "page_count": 1,
                    "table_density": 0.0,
                    "math_signals": 0,
                    "languages": ["en"],
                    "estimated_domain": "general"
                }
        else:
            # For bytes input, use basic analysis
            characteristics = {
                "is_scanned": False,
                "has_text_layer": True,
                "page_count": 1,  # Will be updated during processing
                "table_density": 0.0,
                "math_signals": 0,
                "languages": ["en"],
                "estimated_domain": "general"
            }
        
        # Override with user hints if provided
        if request.doc_hints.is_scanned is not None:
            characteristics["is_scanned"] = request.doc_hints.is_scanned
        if request.doc_hints.contains_tables is not None:
            characteristics["table_density"] = 1.0 if request.doc_hints.contains_tables else 0.0
        if request.doc_hints.contains_math is not None:
            characteristics["math_signals"] = 10 if request.doc_hints.contains_math else 0
        if request.doc_hints.languages:
            characteristics["languages"] = request.doc_hints.languages
        if request.doc_hints.domain:
            characteristics["estimated_domain"] = request.doc_hints.domain
        
        logger.info(f"Document characteristics: {characteristics}")
        return characteristics
    
    def _route_and_extract(self, request: ProcessingRequest, characteristics: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """Route document to appropriate extraction tools and extract content."""
        extraction_result = {
            "text_content": "",
            "tables": [],
            "images": [],
            "math_equations": [],
            "provenance": [],
            "defects": []
        }
        
        # Route based on document type and characteristics
        if document_type == "Word":
            logger.info("Routing to Word document extraction")
            extraction_result.update(self._extract_word_document(request, characteristics))
        elif document_type == "PDF":
            # Route based on document characteristics
            if characteristics["is_scanned"]:
                logger.info("Routing to OCR-based extraction")
                extraction_result.update(self._extract_with_ocr(request, characteristics))
            elif characteristics["math_signals"] > 5:
                logger.info("Routing to math-aware extraction")
                extraction_result.update(self._extract_with_math(request, characteristics))
            elif characteristics["table_density"] > 0.5:
                logger.info("Routing to table-aware extraction")
                extraction_result.update(self._extract_with_tables(request, characteristics))
            else:
                logger.info("Routing to standard text extraction")
                extraction_result.update(self._extract_standard(request, characteristics))
        else:
            logger.warning(f"Unknown document type: {document_type}, using standard extraction")
            extraction_result.update(self._extract_standard(request, characteristics))
        
        return extraction_result
    
    def _extract_word_document(self, request: ProcessingRequest, characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from Word documents."""
        result = {"text_content": "", "tables": [], "images": [], "provenance": [], "defects": []}
        
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        
        if not self.word_text_extractor:
            defect = ProcessingDefect(
                page=0,
                element_type="text",
                description="Word processing libraries not available",
                severity="high",
                tool_used="word_extractor"
            )
            result["defects"].append(defect)
            return result
        
        try:
            # Extract text
            if document_path:
                text_result = self.word_text_extractor.extract_text(document_path)
            else:
                # Handle bytes input if needed
                defect = ProcessingDefect(
                    page=0,
                    element_type="text",
                    description="Word document bytes processing not implemented",
                    severity="medium",
                    tool_used="word_extractor"
                )
                result["defects"].append(defect)
                return result
            
            result["text_content"] = text_result["content"]
            result["provenance"].extend(text_result["provenance"])
            
            # Extract tables if present
            if characteristics.get("has_tables", False) and self.word_table_extractor:
                try:
                    table_result = self.word_table_extractor.extract_tables(document_path)
                    result["tables"] = table_result["tables"]
                    result["provenance"].extend(table_result["provenance"])
                except Exception as e:
                    defect = ProcessingDefect(
                        page=0,
                        element_type="table",
                        description=f"Word table extraction failed: {str(e)}",
                        severity="medium",
                        tool_used="word_table_extractor"
                    )
                    result["defects"].append(defect)
            
            # Extract images if present
            if characteristics.get("has_images", False) and self.word_image_extractor:
                try:
                    image_result = self.word_image_extractor.extract_images(document_path, self.output_dir)
                    result["images"] = image_result["images"]
                    result["provenance"].extend(image_result["provenance"])
                except Exception as e:
                    defect = ProcessingDefect(
                        page=0,
                        element_type="image",
                        description=f"Word image extraction failed: {str(e)}",
                        severity="low",
                        tool_used="word_image_extractor"
                    )
                    result["defects"].append(defect)
            
        except Exception as e:
            defect = ProcessingDefect(
                page=0,
                element_type="text",
                description=f"Word document extraction failed: {str(e)}",
                severity="high",
                tool_used="word_extractor"
            )
            result["defects"].append(defect)
            logger.error(f"Word document extraction failed: {e}")
        
        return result
    
    def _extract_standard(self, request: ProcessingRequest, characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Standard text extraction for born-digital PDFs. Uses LLM vision if available."""
        result = {"text_content": "", "provenance": [], "defects": []}
        
        try:
            # Get document path (support both old and new field names)
            document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
            
            # Get API key for LLM vision extraction (preferred for all PDFs)
            api_key = request.openai_api_key or request.anthropic_api_key
            
            if document_path:
                text_result = self.text_extractor.extract_text(document_path, api_key=api_key, use_llm=True)
            elif request.pdf_bytes:
                text_result = self.text_extractor.extract_text_from_bytes(request.pdf_bytes, api_key=api_key, use_llm=True)
            else:
                raise ValueError("No document path or bytes provided")
            
            result["text_content"] = text_result["content"]
            result["provenance"].extend(text_result["provenance"])
            
        except Exception as e:
            defect = ProcessingDefect(
                page=0,
                element_type="text",
                description=f"Text extraction failed: {str(e)}",
                severity="high",
                tool_used="text_extractor"
            )
            result["defects"].append(defect)
            logger.error(f"Text extraction failed: {e}")
        
        return result
    
    def _extract_with_ocr(self, request: ProcessingRequest, characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """OCR-based extraction for scanned documents. Uses LLM vision if API key available."""
        result = {"text_content": "", "provenance": [], "defects": []}
        
        try:
            # Get document path (support both old and new field names)
            document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
            
            # Get API key for LLM vision extraction (preferred for scanned PDFs)
            api_key = request.openai_api_key or request.anthropic_api_key
            
            if document_path:
                # Use LLM vision if API key available, otherwise fall back to Tesseract OCR
                ocr_result = self.text_extractor.extract_with_ocr(document_path, api_key=api_key, use_llm=True)
            elif request.pdf_bytes:
                ocr_result = self.text_extractor.extract_with_ocr_from_bytes(request.pdf_bytes, api_key=api_key, use_llm=True)
            else:
                raise ValueError("No document path or bytes provided")
            
            result["text_content"] = ocr_result["content"]
            result["provenance"].extend(ocr_result["provenance"])
            
        except Exception as e:
            defect = ProcessingDefect(
                page=0,
                element_type="text",
                description=f"OCR extraction failed: {str(e)}",
                severity="high",
                tool_used="ocr_extractor"
            )
            result["defects"].append(defect)
            logger.error(f"OCR extraction failed: {e}")
        
        return result
    
    def _extract_with_math(self, request: ProcessingRequest, characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Math-aware extraction for documents with equations."""
        result = {"text_content": "", "math_equations": [], "provenance": [], "defects": []}
        
        try:
            # Get document path (support both old and new field names)
            document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
            
            # Extract text first
            if document_path:
                text_result = self.text_extractor.extract_text(document_path)
                math_result = self.math_extractor.extract_equations(document_path)
            elif request.pdf_bytes:
                text_result = self.text_extractor.extract_text_from_bytes(request.pdf_bytes)
                math_result = self.math_extractor.extract_equations_from_bytes(request.pdf_bytes)
            else:
                raise ValueError("No document path or bytes provided")
            
            result["text_content"] = text_result["content"]
            result["math_equations"] = math_result["equations"]
            result["provenance"].extend(text_result["provenance"])
            result["provenance"].extend(math_result["provenance"])
            
        except Exception as e:
            defect = ProcessingDefect(
                page=0,
                element_type="math",
                description=f"Math extraction failed: {str(e)}",
                severity="medium",
                tool_used="math_extractor"
            )
            result["defects"].append(defect)
            logger.error(f"Math extraction failed: {e}")
        
        return result
    
    def _extract_with_tables(self, request: ProcessingRequest, characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Table-aware extraction for documents with dense tables."""
        result = {"text_content": "", "tables": [], "provenance": [], "defects": []}
        
        try:
            # Extract text and tables
            if request.pdf_path:
                text_result = self.text_extractor.extract_text(request.pdf_path)
                table_result = self.table_extractor.extract_tables(request.pdf_path)
            else:
                text_result = self.text_extractor.extract_text_from_bytes(request.pdf_bytes)
                table_result = self.table_extractor.extract_tables_from_bytes(request.pdf_bytes)
            
            result["text_content"] = text_result["content"]
            result["tables"] = table_result["tables"]
            result["provenance"].extend(text_result["provenance"])
            result["provenance"].extend(table_result["provenance"])
            
        except Exception as e:
            defect = ProcessingDefect(
                page=0,
                element_type="table",
                description=f"Table extraction failed: {str(e)}",
                severity="medium",
                tool_used="table_extractor"
            )
            result["defects"].append(defect)
            logger.error(f"Table extraction failed: {e}")
        
        return result
    
    def _apply_quality_assurance(self, extraction_result: Dict[str, Any], run_mode: RunMode) -> Dict[str, Any]:
        """Apply quality assurance checks to extraction results."""
        qa_result = extraction_result.copy()
        
        # Apply QA checks based on run mode
        if run_mode in [RunMode.EVALUATION, RunMode.BEDDING]:
            # Full QA checks
            qa_checks = self.qa.run_full_checks(extraction_result)
        else:
            # Basic QA checks
            qa_checks = self.qa.run_basic_checks(extraction_result)
        
        qa_result["qa_metrics"] = qa_checks["metrics"]
        qa_result["defects"].extend(qa_checks["defects"])
        
        return qa_result
    
    def _apply_compliance(self, qa_result: Dict[str, Any], compliance_config) -> Dict[str, Any]:
        """Apply compliance checks and redaction."""
        compliance_result = qa_result.copy()
        
        # Apply compliance guard
        compliance_checks = self.compliance.apply_checks(
            qa_result["text_content"], compliance_config
        )
        
        compliance_result["text_content"] = compliance_checks["processed_content"]
        compliance_result["compliance_log"] = compliance_checks["log"]
        
        return compliance_result
    
    def _generate_output(self, compliance_result: Dict[str, Any], request: ProcessingRequest) -> ConversionResult:
        """Generate final output files and reports."""
        # Get document path and create folder structure
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        
        if getattr(request, 'original_filename', None):
            # Use the original filename for the markdown file
            doc_id = request.original_filename
            markdown_filename = f"{doc_id}.md"
            doc_output_dir = self.output_dir / doc_id
        elif document_path:
            # Use the current filename for the markdown file
            markdown_filename = f"{document_path.stem}.md"
            # Create a folder with the document name
            doc_id = document_path.stem
            doc_output_dir = self.output_dir / doc_id
        else:
            # Fallback for bytes input
            markdown_filename = "document.md"
            doc_id = "document"
            doc_output_dir = self.output_dir / doc_id
        
        ensure_directory(doc_output_dir)
        
        # Generate markdown content
        markdown_content = self._generate_markdown(compliance_result)
        
        # Save markdown file with original filename inside the document folder
        markdown_path = doc_output_dir / markdown_filename
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Save provenance in the same folder
        provenance_path = doc_output_dir / "provenance.jsonl"
        save_jsonl([p.model_dump() for p in compliance_result["provenance"]], provenance_path)
        
        # Generate run report in the same folder
        run_report = self._generate_run_report(request, compliance_result, doc_output_dir)
        report_path = doc_output_dir / "run_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            # Convert datetime to ISO format for JSON serialization
            report_dict = run_report.model_dump()
            report_dict['timestamp'] = report_dict['timestamp'].isoformat()
            import json
            f.write(json.dumps(report_dict, indent=2))
        
        # Create result
        result = ConversionResult(
            markdown_content=markdown_content,
            assets_dir=doc_output_dir / "assets",
            provenance_records=compliance_result["provenance"],
            run_report=run_report,
            output_files={
                "markdown": markdown_path,
                "provenance": provenance_path,
                "report": report_path
            }
        )
        
        return result
    
    def _final_llm_verification(self, request: ProcessingRequest, extracted_text: str, api_key: str) -> Optional[str]:
        """Final LLM pass to verify and fix any missing text in the extracted content."""
        import base64
        import requests
        import os
        import fitz
        
        # Get document path
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        if not document_path or not document_path.exists():
            return None
        
        # Only process PDFs for now
        if document_path.suffix.lower() != '.pdf':
            return None
        
        try:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
            base_url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            doc = fitz.open(str(document_path))
            verified_pages = []
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Render page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                image_b64 = base64.b64encode(img_bytes).decode('utf-8')
                
                # Extract page content from extracted text (approximate)
                page_start_idx = extracted_text.find(f"--- Page {page_num + 1} ---")
                page_end_idx = extracted_text.find(f"--- Page {page_num + 2} ---")
                if page_start_idx == -1:
                    page_start_idx = 0
                if page_end_idx == -1:
                    page_end_idx = len(extracted_text)
                
                page_text = extracted_text[page_start_idx:page_end_idx]
                
                # Create verification prompt
                prompt = f"""Review the extracted text below and compare it with this document page image.

Extracted text for this page:
{page_text[:2000] if len(page_text) > 2000 else page_text}

Your task:
1. Verify ALL text from the image is present in the extracted text
2. Identify any missing text, headings, or content
3. Fix any extraction errors or omissions
4. Ensure complete accuracy and completeness
5. Preserve structure, formatting, and layout
6. Output the complete, verified text in clean markdown format

Extract ALL text visible in the image, including any text that may have been missed.
Return only the complete, verified text for this page in markdown format, no explanations."""
                
                payload = {
                    "model": model,
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
                                        "url": f"data:image/png;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ]
                }
                
                try:
                    response = requests.post(base_url, headers=headers, json=payload, timeout=60)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        verified_text = response_data['choices'][0]['message']['content']
                        verified_pages.append(f"\n\n--- Page {page_num + 1} ---\n\n{verified_text}")
                        logger.info(f"Final LLM verification completed for page {page_num + 1}")
                    else:
                        logger.warning(f"Final LLM verification failed for page {page_num + 1}, using original extraction")
                        verified_pages.append(page_text)
                except Exception as e:
                    logger.warning(f"Final LLM verification error for page {page_num + 1}: {e}, using original extraction")
                    verified_pages.append(page_text)
            
            doc.close()
            
            if verified_pages:
                return "".join(verified_pages)
            return None
            
        except Exception as e:
            logger.warning(f"Final LLM verification failed: {e}")
            return None
    
    def _apply_vision_validation(self, 
                                request: ProcessingRequest, 
                                extraction_result: Dict[str, Any],
                                qa_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply vision-based validation using OpenAI Vision API."""
        
        # Initialize vision validator if not already done
        if self.vision_validator is None:
            # Use openai_api_key if available, otherwise fall back to anthropic_api_key for backward compatibility
            api_key = request.openai_api_key or request.anthropic_api_key
            if not api_key:
                logger.warning("No API key provided for vision validation")
                return {}
            self.vision_validator = VisionValidator(api_key)
        
        # Get document path
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        if not document_path:
            logger.warning("No document path available for vision validation")
            return {}
        
        # Get extracted markdown content
        markdown_content = self._generate_markdown(extraction_result)
        
        # Determine document type from filename
        document_type = "document"
        if request.original_filename:
            if "cv" in request.original_filename.lower():
                document_type = "cv"
            elif "cl" in request.original_filename.lower():
                document_type = "cl"
        
        try:
            # Perform vision validation
            vision_result = self.vision_validator.validate_extraction(
                document_path, markdown_content, document_type
            )
            
            logger.info(f"Vision validation completed with confidence: {vision_result.confidence_score:.2f}")
            
            # Add vision defects to QA result
            if vision_result.defects:
                qa_result.setdefault("defects", []).extend(vision_result.defects)
            
            return {
                "vision_result": vision_result,
                "confidence_score": vision_result.confidence_score,
                "defects": vision_result.defects,
                "suggestions": vision_result.suggestions
            }
            
        except Exception as e:
            logger.error(f"Vision validation failed: {str(e)}")
            return {
                "vision_result": None,
                "confidence_score": 0.0,
                "defects": [],
                "suggestions": []
            }
    
    def _enhance_metrics_with_vision(self, 
                                   base_metrics: Dict[str, Any], 
                                   vision_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance base quality metrics with vision validation results."""
        
        if not vision_result or "vision_result" not in vision_result:
            return base_metrics
        
        vision_data = vision_result["vision_result"]
        
        # Add vision-specific metrics
        enhanced_metrics = base_metrics.copy()
        enhanced_metrics.update({
            "vision_confidence": vision_data.confidence_score,
            "content_completeness": vision_data.content_completeness,
            "image_caption_accuracy": vision_data.image_caption_accuracy,
            "formatting_accuracy": vision_data.formatting_accuracy,
            "table_accuracy": max(base_metrics.get("table_grits", 0.0), vision_data.table_accuracy)
        })
        
        return enhanced_metrics
    
    def _generate_markdown(self, compliance_result: Dict[str, Any]) -> str:
        """Generate markdown content from extracted elements."""
        markdown_parts = []
        
        # Add text content
        if compliance_result.get("text_content"):
            markdown_parts.append(compliance_result["text_content"])
        
        # Add tables
        for table in compliance_result.get("tables", []):
            if isinstance(table, dict) and "markdown" in table:
                markdown_parts.append(table["markdown"])
            elif isinstance(table, dict) and "data" in table:
                # Convert table data to markdown
                table_md = self._table_to_markdown(table["data"])
                markdown_parts.append(table_md)
        
        # Add math equations
        for equation in compliance_result.get("math_equations", []):
            if isinstance(equation, dict) and "latex" in equation:
                markdown_parts.append(f"$${equation['latex']}$$")
        
        return "\n\n".join(markdown_parts)
    
    def _table_to_markdown(self, table_data: List[List[str]]) -> str:
        """Convert table data to markdown format."""
        if not table_data:
            return ""
        
        markdown_lines = []
        
        # Add header
        markdown_lines.append("| " + " | ".join(table_data[0]) + " |")
        markdown_lines.append("| " + " | ".join(["---"] * len(table_data[0])) + " |")
        
        # Add data rows
        for row in table_data[1:]:
            markdown_lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(markdown_lines)
    
    def _generate_run_report(self, request: ProcessingRequest, compliance_result: Dict[str, Any], output_dir: Path) -> RunReport:
        """Generate comprehensive run report."""
        processing_time = time.time() - self.start_time
        
        # Get document path
        document_path = getattr(request, 'document_path', None) or getattr(request, 'pdf_path', None)
        
        # Calculate quality metrics
        qa_metrics = compliance_result.get("qa_metrics", {})
        quality_metrics = QualityMetrics(
            cer=qa_metrics.get("cer", 0.0),
            wer=qa_metrics.get("wer", 0.0),
            table_grits=qa_metrics.get("table_grits", 0.0),
            math_token_match=qa_metrics.get("math_token_match", 0.0),
            structure_accuracy=qa_metrics.get("structure_accuracy", 0.0),
            provenance_coverage=qa_metrics.get("provenance_coverage", 0.0)
        )
        
        # Get tool versions
        tool_versions = {
            "text_extractor": self.text_extractor.get_version(),
            "table_extractor": self.table_extractor.get_version(),
            "image_extractor": self.image_extractor.get_version(),
            "math_extractor": self.math_extractor.get_version(),
        }
        
        # Add Word extractor versions if available
        if hasattr(self, 'word_text_extractor') and self.word_text_extractor:
            tool_versions["word_text_extractor"] = self.word_text_extractor.get_version()
        if hasattr(self, 'word_table_extractor') and self.word_table_extractor:
            tool_versions["word_table_extractor"] = self.word_table_extractor.get_version()
        if hasattr(self, 'word_image_extractor') and self.word_image_extractor:
            tool_versions["word_image_extractor"] = self.word_image_extractor.get_version()
        
        # Determine success based on defects and content
        defects = compliance_result.get("defects", [])
        text_content = compliance_result.get("text_content", "")
        
        # Check for critical defects
        critical_defects = [d for d in defects if d.severity == "high" or d.severity == "critical"]
        has_empty_content = not text_content.strip()
        
        # Success criteria: no critical defects and has content
        is_successful = len(critical_defects) == 0 and not has_empty_content
        
        return RunReport(
            run_id=self.current_run_id,
            input_file=str(document_path) if document_path else "bytes",
            output_dir=str(output_dir),
            run_mode=request.run_mode,
            tools_used=list(tool_versions.keys()),
            tool_versions=tool_versions,
            quality_metrics=quality_metrics,
            defects=defects,
            processing_time_s=processing_time,
            memory_peak_mb=self.peak_memory,
            router_decisions={},  # TODO: Add router decisions
            compliance_applied=request.compliance,
            success=is_successful
        )
    
    def _create_error_result(self, request: ProcessingRequest, error_message: str) -> ConversionResult:
        """Create error result when processing fails."""
        doc_id = request.pdf_path.stem if request.pdf_path else "document"
        doc_output_dir = self.output_dir / doc_id
        ensure_directory(doc_output_dir)
        
        # Create error report
        run_report = RunReport(
            run_id=self.current_run_id,
            input_file=str(request.pdf_path) if request.pdf_path else "bytes",
            output_dir=str(doc_output_dir),
            run_mode=request.run_mode,
            tools_used=[],
            tool_versions={},
            quality_metrics=QualityMetrics(),
            defects=[],
            processing_time_s=time.time() - self.start_time if self.start_time else 0.0,
            memory_peak_mb=self.peak_memory,
            router_decisions={},
            compliance_applied=request.compliance,
            success=False,
            error_message=error_message
        )
        
        # Save error report
        report_path = doc_output_dir / "run_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            # Convert datetime to ISO format for JSON serialization
            report_dict = run_report.model_dump()
            report_dict['timestamp'] = report_dict['timestamp'].isoformat()
            import json
            f.write(json.dumps(report_dict, indent=2))
        
        return ConversionResult(
            markdown_content=f"# Processing Error\n\n{error_message}",
            assets_dir=doc_output_dir / "assets",
            provenance_records=[],
            run_report=run_report,
            output_files={"report": report_path}
        )
