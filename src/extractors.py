"""
Content extractors for different PDF elements.
"""

import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from .models import ProvenanceRecord
from .utils import calculate_element_hash


class TextExtractor:
    """Extract text content from PDFs."""
    
    def __init__(self):
        self.version = "1.0.0"
    
    def get_version(self) -> str:
        return self.version
    
    def extract_text(self, pdf_path: Path, api_key: Optional[str] = None, use_llm: bool = True) -> Dict[str, Any]:
        """Extract text from PDF file. Uses LLM vision if available for better quality."""
        result = {
            "content": "",
            "provenance": []
        }
        
        # Try LLM vision first if available (better quality for all PDFs)
        if use_llm and api_key:
            logger.info("Using LLM vision for text extraction (preferred method)")
            try:
                doc = fitz.open(str(pdf_path))
                llm_result = self._extract_with_llm_vision(pdf_path, api_key, doc)
                doc.close()
                return llm_result
            except Exception as e:
                error_str = str(e)
                # Check if it's a quota/billing error - fall back to standard extraction
                if "quota" in error_str.lower() or "billing" in error_str.lower() or "insufficient_quota" in error_str:
                    logger.warning(f"LLM vision API quota exceeded, falling back to standard extraction: {e}")
                else:
                    logger.warning(f"LLM vision extraction failed, falling back to standard extraction: {e}")
                # Continue to standard extraction below
        
        # Fallback to standard extraction
        try:
            doc = fitz.open(str(pdf_path))
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get text blocks with positioning
                text_dict = page.get_text("dict")
                
                page_content = []
                for block in text_dict["blocks"]:
                    if "lines" in block:  # Text block
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"]
                                bbox = span["bbox"]
                                
                                page_content.append(text)
                                
                                # Create provenance record
                                provenance = ProvenanceRecord(
                                    page=page_num + 1,
                                    bbox=bbox,
                                    tool="pymupdf",
                                    confidence=1.0,
                                    element_hash=calculate_element_hash(text, bbox, page_num + 1),
                                    element_type="text",
                                    content_preview=text[:50]
                                )
                                result["provenance"].append(provenance)
                
                result["content"] += "\n".join(page_content) + "\n\n"
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
        
        return result
    
    def extract_text_from_bytes(self, pdf_bytes: bytes, api_key: Optional[str] = None, use_llm: bool = True) -> Dict[str, Any]:
        """Extract text from PDF bytes. Uses LLM vision if available."""
        import tempfile
        import os
        
        # Write bytes to temporary file and process
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = self.extract_text(tmp_path, api_key=api_key, use_llm=use_llm)
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                os.unlink(tmp_path)
        
        return result
    
    def extract_with_ocr(self, pdf_path: Path, api_key: Optional[str] = None, use_llm: bool = True) -> Dict[str, Any]:
        """Extract text using OCR or LLM vision for scanned documents.
        
        Args:
            pdf_path: Path to PDF file
            api_key: OpenAI API key for LLM vision extraction (if None, falls back to Tesseract OCR)
            use_llm: If True and api_key provided, use LLM vision for extraction (better quality)
        """
        result = {
            "content": "",
            "provenance": []
        }
        
        try:
            doc = fitz.open(str(pdf_path))
            
            # Try LLM vision extraction first if available (better quality for complex layouts)
            if use_llm and api_key:
                logger.info("Using LLM vision for text extraction from scanned PDF")
                try:
                    return self._extract_with_llm_vision(pdf_path, api_key, doc)
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a quota/billing error - fall back to OCR
                    if "quota" in error_str.lower() or "billing" in error_str.lower() or "insufficient_quota" in error_str:
                        logger.warning(f"LLM vision API quota exceeded, falling back to Tesseract OCR: {e}")
                        # Continue to OCR extraction below
                    else:
                        logger.warning(f"LLM vision extraction failed, falling back to OCR: {e}")
                        # Continue to OCR extraction below
            
            # Fallback to traditional OCR
            logger.info("Using Tesseract OCR for text extraction")
            ocr_content_by_page = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Try to get text first (in case PDF has some text layer)
                text = page.get_text()
                
                # If no text or very little text, use OCR
                if len(text.strip()) < 50:  # Threshold for considering it scanned
                    logger.info(f"Page {page_num + 1} appears to be scanned, using OCR")
                    try:
                        # Render page to image for OCR
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                        img_bytes = pix.tobytes("png")
                        
                        # Use pytesseract for OCR
                        try:
                            import pytesseract
                            from PIL import Image
                            import io
                            
                            img = Image.open(io.BytesIO(img_bytes))
                            text = pytesseract.image_to_string(img, lang='eng')
                            logger.info(f"OCR extracted {len(text)} characters from page {page_num + 1}")
                        except ImportError:
                            logger.warning("pytesseract not available, trying alternative OCR methods")
                            # Fallback: try pdf2image + tesseract via subprocess
                            try:
                                from pdf2image import convert_from_path
                                import subprocess
                                import tempfile
                                
                                # Save page as temporary image
                                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                                    tmp_img.write(img_bytes)
                                    tmp_img_path = tmp_img.name
                                
                                # Use tesseract command line
                                result = subprocess.run(
                                    ['tesseract', tmp_img_path, 'stdout', '-l', 'eng'],
                                    capture_output=True,
                                    text=True
                                )
                                
                                if result.returncode == 0:
                                    text = result.stdout
                                    logger.info(f"OCR (via tesseract CLI) extracted {len(text)} characters from page {page_num + 1}")
                                else:
                                    raise Exception(f"Tesseract CLI failed: {result.stderr}")
                                
                                # Clean up temp file
                                import os
                                os.unlink(tmp_img_path)
                            except Exception as e:
                                logger.error(f"OCR extraction failed on page {page_num + 1}: {e}")
                                text = f"[OCR extraction failed for page {page_num + 1}: {str(e)}]"
                    except Exception as ocr_error:
                        logger.error(f"OCR extraction error on page {page_num + 1}: {ocr_error}")
                        text = f"[OCR extraction failed: {str(ocr_error)}]"
                
                if text.strip():
                    ocr_content_by_page.append((page_num + 1, text))
                    
                    # Create provenance record for OCR extraction
                    provenance = ProvenanceRecord(
                        page=page_num + 1,
                        bbox=[0, 0, page.rect.width, page.rect.height],
                        tool="ocr_extractor",
                        confidence=0.85 if len(text.strip()) > 100 else 0.5,  # Lower confidence for short text
                        element_hash=calculate_element_hash(text[:100], [0, 0, 0, 0], page_num + 1),
                        element_type="text",
                        content_preview=text[:100] if len(text) > 100 else text  # Limit to 100 chars for ProvenanceRecord
                    )
                    result["provenance"].append(provenance)
            
            # If OCR was used and API key available, verify and fix with LLM
            if ocr_content_by_page and api_key and use_llm:
                logger.info("Verifying OCR results with LLM vision to fix missing text")
                try:
                    verified_content = self._verify_ocr_with_llm(pdf_path, api_key, doc, ocr_content_by_page)
                    if verified_content:
                        result["content"] = verified_content
                        # Update provenance to indicate LLM verification
                        for prov in result["provenance"]:
                            if prov.tool == "ocr_extractor":
                                prov.tool = "ocr_extractor+llm_verification"
                                prov.confidence = min(prov.confidence + 0.1, 0.95)
                    else:
                        # If verification failed, use OCR results as-is
                        result["content"] = "".join([f"\n\n--- Page {p} ---\n\n{t}" for p, t in ocr_content_by_page])
                except Exception as e:
                    logger.warning(f"LLM OCR verification failed, using OCR results as-is: {e}")
                    result["content"] = "".join([f"\n\n--- Page {p} ---\n\n{t}" for p, t in ocr_content_by_page])
            else:
                # Use OCR results directly
                result["content"] = "".join([f"\n\n--- Page {p} ---\n\n{t}" for p, t in ocr_content_by_page])
            
            doc.close()
            
            if not result["content"].strip():
                logger.warning("OCR extraction produced no text content")
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
        
        return result
    
    def _extract_with_llm_vision(self, pdf_path: Path, api_key: str, doc: fitz.Document) -> Dict[str, Any]:
        """Extract text from scanned PDF using LLM vision models."""
        import base64
        import requests
        import os
        
        result = {
            "content": "",
            "provenance": []
        }
        
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        base_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        full_content = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to high-quality image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            img_bytes = pix.tobytes("png")
            image_b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Create extraction prompt
            prompt = f"""Extract all text content from this scanned document page. 
Preserve the structure, formatting, and layout as much as possible.
- Include all headings, paragraphs, lists, and tables
- Maintain original line breaks and spacing where meaningful
- Extract text from both columns if present
- Include all contact information, qualifications, and details
- Output in clean markdown format

Return only the extracted text in markdown format, no explanations."""
            
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
                    page_text = response_data['choices'][0]['message']['content']
                    full_content.append(f"\n\n--- Page {page_num + 1} ---\n\n{page_text}")
                    logger.info(f"LLM vision extracted {len(page_text)} characters from page {page_num + 1}")
                    
                    # Create provenance record
                    provenance = ProvenanceRecord(
                        page=page_num + 1,
                        bbox=[0, 0, page.rect.width, page.rect.height],
                        tool="llm_vision_extractor",
                        confidence=0.95,  # High confidence for LLM vision
                        element_hash=calculate_element_hash(page_text[:100], [0, 0, 0, 0], page_num + 1),
                        element_type="text",
                        content_preview=page_text[:100] if len(page_text) > 100 else page_text
                    )
                    result["provenance"].append(provenance)
                else:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get('error', {}).get('message', response.text)
                    error_code = error_data.get('error', {}).get('code', 'unknown')
                    
                    # Check for quota errors - fall back to OCR
                    if error_code == 'insufficient_quota':
                        logger.warning(f"OpenAI API quota exceeded on page {page_num + 1}, falling back to OCR")
                        # Fall through to OCR extraction below
                        raise Exception(f"API quota exceeded: {error_msg}")
                    else:
                        logger.error(f"LLM vision API error on page {page_num + 1}: {error_msg}")
                        full_content.append(f"\n\n--- Page {page_num + 1} ---\n\n[LLM vision extraction failed: {error_msg}]")
            except Exception as e:
                error_str = str(e)
                # Check for quota errors - re-raise to trigger OCR fallback
                if "quota" in error_str.lower() or "billing" in error_str.lower() or "insufficient_quota" in error_str:
                    logger.warning(f"OpenAI API quota exceeded, will fall back to OCR")
                    raise Exception(f"API quota exceeded: {error_str}")  # Re-raise to trigger OCR fallback
                else:
                    logger.error(f"LLM vision extraction failed on page {page_num + 1}: {e}")
                    full_content.append(f"\n\n--- Page {page_num + 1} ---\n\n[LLM vision extraction failed: {str(e)}]")
        
        result["content"] = "".join(full_content)
        return result
    
    def _verify_ocr_with_llm(self, pdf_path: Path, api_key: str, doc: fitz.Document, ocr_content_by_page: List[tuple[int, str]]) -> Optional[str]:
        """Verify OCR results with LLM vision and fix any missing text."""
        import base64
        import requests
        import os
        
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        base_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        verified_content = []
        
        for page_num, ocr_text in ocr_content_by_page:
            page = doc[page_num - 1]  # Convert to 0-based index
            
            # Render page to high-quality image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            image_b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Create verification prompt
            prompt = f"""Review the OCR-extracted text below and compare it with this document page image.
Your task:
1. Check if any text is missing from the OCR extraction
2. Verify the accuracy of the extracted text
3. Fix any OCR errors or missing content
4. Preserve structure, formatting, and layout
5. Output the complete, corrected text in markdown format

OCR-extracted text for reference:
{ocr_text[:1000]}...

Extract ALL text from the image, including any text that the OCR may have missed.
Return only the complete, corrected text in markdown format, no explanations."""
            
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
                    verified_content.append(f"\n\n--- Page {page_num} ---\n\n{verified_text}")
                    logger.info(f"LLM verified and fixed OCR for page {page_num} ({len(verified_text)} chars)")
                else:
                    logger.warning(f"LLM verification failed for page {page_num}, using OCR result")
                    verified_content.append(f"\n\n--- Page {page_num} ---\n\n{ocr_text}")
            except Exception as e:
                logger.warning(f"LLM verification error for page {page_num}: {e}, using OCR result")
                verified_content.append(f"\n\n--- Page {page_num} ---\n\n{ocr_text}")
        
        return "".join(verified_content) if verified_content else None
    
    def extract_with_ocr_from_bytes(self, pdf_bytes: bytes, api_key: Optional[str] = None, use_llm: bool = True) -> Dict[str, Any]:
        """Extract text using OCR from PDF bytes."""
        import tempfile
        import os
        
        # Write bytes to temporary file and process
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = self.extract_with_ocr(tmp_path, api_key=api_key, use_llm=use_llm)
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                os.unlink(tmp_path)
        
        return result


class TableExtractor:
    """Extract tables from PDFs."""
    
    def __init__(self):
        self.version = "1.0.0"
    
    def get_version(self) -> str:
        return self.version
    
    def extract_tables(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract tables from PDF file."""
        result = {
            "tables": [],
            "provenance": []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 0:
                            # Convert table to markdown
                            markdown_table = self._table_to_markdown(table)
                            
                            table_info = {
                                "page": page_num + 1,
                                "table_index": table_idx,
                                "markdown": markdown_table,
                                "raw_data": table
                            }
                            result["tables"].append(table_info)
                            
                            # Create provenance record
                            bbox = [0, 0, page.width, page.height]  # Approximate
                            provenance = ProvenanceRecord(
                                page=page_num + 1,
                                bbox=bbox,
                                tool="pdfplumber",
                                confidence=0.9,
                                element_hash=calculate_element_hash(str(table), bbox, page_num + 1),
                                element_type="table",
                                content_preview=f"Table with {len(table)} rows"
                            )
                            result["provenance"].append(provenance)
        
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            raise
        
        return result
    
    def extract_tables_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract tables from PDF bytes."""
        result = {
            "tables": [],
            "provenance": []
        }
        
        try:
            with pdfplumber.open(stream=pdf_bytes) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 0:
                            # Convert table to markdown
                            markdown_table = self._table_to_markdown(table)
                            
                            table_info = {
                                "page": page_num + 1,
                                "table_index": table_idx,
                                "markdown": markdown_table,
                                "raw_data": table
                            }
                            result["tables"].append(table_info)
                            
                            # Create provenance record
                            bbox = [0, 0, page.width, page.height]  # Approximate
                            provenance = ProvenanceRecord(
                                page=page_num + 1,
                                bbox=bbox,
                                tool="pdfplumber",
                                confidence=0.9,
                                element_hash=calculate_element_hash(str(table), bbox, page_num + 1),
                                element_type="table",
                                content_preview=f"Table with {len(table)} rows"
                            )
                            result["provenance"].append(provenance)
        
        except Exception as e:
            logger.error(f"Table extraction from bytes failed: {e}")
            raise
        
        return result
    
    def _table_to_markdown(self, table: List[List[str]]) -> str:
        """Convert table data to markdown format."""
        if not table or len(table) == 0:
            return ""
        
        markdown_lines = []
        
        # Add header
        header = "| " + " | ".join(str(cell) if cell else "" for cell in table[0]) + " |"
        markdown_lines.append(header)
        
        # Add separator
        separator = "| " + " | ".join("---" for _ in table[0]) + " |"
        markdown_lines.append(separator)
        
        # Add data rows
        for row in table[1:]:
            row_str = "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |"
            markdown_lines.append(row_str)
        
        return "\n".join(markdown_lines)


class ImageExtractor:
    """Extract images from PDFs."""
    
    def __init__(self):
        self.version = "1.0.0"
    
    def get_version(self) -> str:
        return self.version
    
    def extract_images(self, pdf_path: Path, output_dir: Path) -> Dict[str, Any]:
        """Extract images from PDF file."""
        result = {
            "images": [],
            "provenance": []
        }
        
        try:
            doc = fitz.open(str(pdf_path))
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get image list
                image_list = page.get_images()
                
                for img_idx, img in enumerate(image_list):
                    try:
                        # Extract image
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            # Save image
                            img_filename = f"page_{page_num + 1}_img_{img_idx}.png"
                            img_path = output_dir / img_filename
                            pix.save(str(img_path))
                            
                            # Get image bbox
                            bbox = img[2]  # Image rectangle
                            
                            image_info = {
                                "page": page_num + 1,
                                "image_index": img_idx,
                                "filename": img_filename,
                                "path": str(img_path),
                                "bbox": bbox
                            }
                            result["images"].append(image_info)
                            
                            # Create provenance record
                            provenance = ProvenanceRecord(
                                page=page_num + 1,
                                bbox=bbox,
                                tool="pymupdf",
                                confidence=1.0,
                                element_hash=calculate_element_hash(img_filename, bbox, page_num + 1),
                                element_type="image",
                                content_preview=f"Image: {img_filename}"
                            )
                            result["provenance"].append(provenance)
                        
                        pix = None  # Free memory
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract image {img_idx} from page {page_num + 1}: {e}")
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
            raise
        
        return result
    
    def extract_images_from_bytes(self, pdf_bytes: bytes, output_dir: Path) -> Dict[str, Any]:
        """Extract images from PDF bytes."""
        result = {
            "images": [],
            "provenance": []
        }
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get image list
                image_list = page.get_images()
                
                for img_idx, img in enumerate(image_list):
                    try:
                        # Extract image
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            # Save image
                            img_filename = f"page_{page_num + 1}_img_{img_idx}.png"
                            img_path = output_dir / img_filename
                            pix.save(str(img_path))
                            
                            # Get image bbox
                            bbox = img[2]  # Image rectangle
                            
                            image_info = {
                                "page": page_num + 1,
                                "image_index": img_idx,
                                "filename": img_filename,
                                "path": str(img_path),
                                "bbox": bbox
                            }
                            result["images"].append(image_info)
                            
                            # Create provenance record
                            provenance = ProvenanceRecord(
                                page=page_num + 1,
                                bbox=bbox,
                                tool="pymupdf",
                                confidence=1.0,
                                element_hash=calculate_element_hash(img_filename, bbox, page_num + 1),
                                element_type="image",
                                content_preview=f"Image: {img_filename}"
                            )
                            result["provenance"].append(provenance)
                        
                        pix = None  # Free memory
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract image {img_idx} from page {page_num + 1}: {e}")
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Image extraction from bytes failed: {e}")
            raise
        
        return result


class MathExtractor:
    """Extract mathematical equations from PDFs."""
    
    def __init__(self):
        self.version = "1.0.0"
    
    def get_version(self) -> str:
        return self.version
    
    def extract_equations(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract mathematical equations from PDF file."""
        result = {
            "equations": [],
            "provenance": []
        }
        
        # This is a placeholder implementation
        # In a full implementation, this would use Nougat or similar tools
        logger.info("Math extraction not yet fully implemented")
        
        return result
    
    def extract_equations_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract mathematical equations from PDF bytes."""
        result = {
            "equations": [],
            "provenance": []
        }
        
        # This is a placeholder implementation
        logger.info("Math extraction not yet fully implemented")
        
        return result
