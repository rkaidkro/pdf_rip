"""
Quality assurance module for PDF processing validation.
"""

import re
from typing import Dict, List, Any
from loguru import logger

from .models import ProcessingDefect, QualityMetrics
from .utils import calculate_cer, calculate_wer


class QualityAssurance:
    """Quality assurance checks for PDF processing results."""
    
    def __init__(self):
        self.cer_threshold_born_digital = 0.005  # 0.5%
        self.cer_threshold_scanned = 0.015  # 1.5%
        self.structure_accuracy_threshold = 0.95
        self.table_grits_threshold = 0.90
        self.math_token_match_threshold = 0.90
        self.provenance_coverage_threshold = 0.99
    
    def run_basic_checks(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run basic quality assurance checks."""
        checks = {
            "metrics": {},
            "defects": []
        }
        
        # Basic structure validation
        structure_defects = self._check_structure(extraction_result)
        checks["defects"].extend(structure_defects)
        
        # Basic provenance coverage
        provenance_coverage = self._calculate_provenance_coverage(extraction_result)
        checks["metrics"]["provenance_coverage"] = provenance_coverage
        
        # Basic content validation
        content_defects = self._check_content_basics(extraction_result)
        checks["defects"].extend(content_defects)
        
        return checks
    
    def run_full_checks(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive quality assurance checks."""
        checks = {
            "metrics": {},
            "defects": []
        }
        
        # All basic checks
        basic_checks = self.run_basic_checks(extraction_result)
        checks["defects"].extend(basic_checks["defects"])
        checks["metrics"].update(basic_checks["metrics"])
        
        # Advanced text quality metrics
        text_metrics = self._calculate_text_quality(extraction_result)
        checks["metrics"].update(text_metrics)
        
        # Table quality assessment
        table_metrics = self._assess_table_quality(extraction_result)
        checks["metrics"].update(table_metrics)
        
        # Math equation validation
        math_metrics = self._validate_math_equations(extraction_result)
        checks["metrics"].update(math_metrics)
        
        # Cross-validation checks
        cross_validation_defects = self._cross_validate_results(extraction_result)
        checks["defects"].extend(cross_validation_defects)
        
        return checks
    
    def _check_structure(self, extraction_result: Dict[str, Any]) -> List[ProcessingDefect]:
        """Check document structure integrity."""
        defects = []
        content = extraction_result.get("text_content", "")
        
        # Check heading structure
        heading_defects = self._validate_headings(content)
        defects.extend(heading_defects)
        
        # Check list structure
        list_defects = self._validate_lists(content)
        defects.extend(list_defects)
        
        # Check code blocks
        code_defects = self._validate_code_blocks(content)
        defects.extend(code_defects)
        
        return defects
    
    def _validate_headings(self, content: str) -> List[ProcessingDefect]:
        """Validate heading structure and hierarchy."""
        defects = []
        
        # Find all headings
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        
        if not headings:
            return defects
        
        # Check for heading level jumps (e.g., H2 -> H4)
        current_level = 0
        for level_str, title in headings:
            level = len(level_str)
            
            if level > current_level + 1:
                defect = ProcessingDefect(
                    page=0,  # Will be refined with actual page info
                    element_type="heading",
                    description=f"Heading level jump from H{current_level} to H{level}: {title}",
                    severity="medium",
                    tool_used="structure_validator"
                )
                defects.append(defect)
            
            current_level = level
        
        return defects
    
    def _validate_lists(self, content: str) -> List[ProcessingDefect]:
        """Validate list structure and formatting."""
        defects = []
        
        # Check for unbalanced list markers
        lines = content.split('\n')
        in_list = False
        list_stack = []
        
        for line_num, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for list markers
            if re.match(r'^[\-\*\+]\s+', stripped):
                if not in_list:
                    in_list = True
                    list_stack.append(('unordered', line_num))
            elif re.match(r'^\d+\.\s+', stripped):
                if not in_list:
                    in_list = True
                    list_stack.append(('ordered', line_num))
            elif stripped and in_list and not line.startswith(' '):
                # End of list
                in_list = False
                list_stack.pop()
        
        # Check for unclosed lists
        if list_stack:
            defect = ProcessingDefect(
                page=0,
                element_type="list",
                description=f"Unclosed list starting at line {list_stack[0][1]}",
                severity="low",
                tool_used="structure_validator"
            )
            defects.append(defect)
        
        return defects
    
    def _validate_code_blocks(self, content: str) -> List[ProcessingDefect]:
        """Validate code block formatting."""
        defects = []
        
        # Check for balanced code fences
        fence_pattern = r'```'
        fences = re.findall(fence_pattern, content)
        
        if len(fences) % 2 != 0:
            defect = ProcessingDefect(
                page=0,
                element_type="code_block",
                description="Unbalanced code fence markers",
                severity="medium",
                tool_used="structure_validator"
            )
            defects.append(defect)
        
        return defects
    
    def _check_content_basics(self, extraction_result: Dict[str, Any]) -> List[ProcessingDefect]:
        """Check basic content quality."""
        defects = []
        content = extraction_result.get("text_content", "")
        
        # Check for empty content
        if not content.strip():
            defect = ProcessingDefect(
                page=0,
                element_type="content",
                description="Empty or missing text content",
                severity="high",
                tool_used="content_validator"
            )
            defects.append(defect)
        
        # Check for excessive whitespace
        if re.search(r'\n\s*\n\s*\n', content):
            defect = ProcessingDefect(
                page=0,
                element_type="content",
                description="Excessive whitespace detected",
                severity="low",
                tool_used="content_validator"
            )
            defects.append(defect)
        
        # Check for common OCR artifacts
        ocr_artifacts = self._detect_ocr_artifacts(content)
        defects.extend(ocr_artifacts)
        
        return defects
    
    def _detect_ocr_artifacts(self, content: str) -> List[ProcessingDefect]:
        """Detect common OCR artifacts and errors."""
        defects = []
        
        # Check for common OCR errors
        ocr_patterns = [
            (r'[0O]{3,}', "Possible OCR confusion between 0 and O"),
            (r'[1Il]{3,}', "Possible OCR confusion between 1, I, and l"),
            (r'[5S]{3,}', "Possible OCR confusion between 5 and S"),
            (r'[8B]{3,}', "Possible OCR confusion between 8 and B"),
        ]
        
        for pattern, description in ocr_patterns:
            if re.search(pattern, content):
                defect = ProcessingDefect(
                    page=0,
                    element_type="ocr_artifact",
                    description=description,
                    severity="low",
                    tool_used="ocr_validator"
                )
                defects.append(defect)
        
        return defects
    
    def _calculate_provenance_coverage(self, extraction_result: Dict[str, Any]) -> float:
        """Calculate the percentage of elements with provenance information."""
        provenance_records = extraction_result.get("provenance", [])
        
        if not provenance_records:
            return 0.0
        
        # Count elements by type
        element_counts = {}
        for record in provenance_records:
            element_type = record.element_type
            element_counts[element_type] = element_counts.get(element_type, 0) + 1
        
        # For now, assume all elements should have provenance
        # In a more sophisticated implementation, we'd count actual elements
        total_elements = sum(element_counts.values())
        
        if total_elements == 0:
            return 0.0
        
        return min(1.0, len(provenance_records) / total_elements)
    
    def _calculate_text_quality(self, extraction_result: Dict[str, Any]) -> Dict[str, float]:
        """Calculate text quality metrics."""
        metrics = {}
        content = extraction_result.get("text_content", "")
        
        # Basic text statistics
        metrics["text_length"] = len(content)
        metrics["word_count"] = len(content.split())
        
        # Character error rate (placeholder - would need reference text)
        # In practice, this would compare against a reference or use heuristics
        metrics["cer"] = 0.0  # Placeholder
        
        # Word error rate (placeholder)
        metrics["wer"] = 0.0  # Placeholder
        
        # Structure accuracy
        structure_accuracy = self._calculate_structure_accuracy(content)
        metrics["structure_accuracy"] = structure_accuracy
        
        return metrics
    
    def _calculate_structure_accuracy(self, content: str) -> float:
        """Calculate structure accuracy score."""
        score = 1.0
        total_checks = 0
        
        # Check heading structure
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        
        if headings:
            total_checks += 1
            # Check for proper hierarchy
            current_level = 0
            hierarchy_errors = 0
            
            for level_str, _ in headings:
                level = len(level_str)
                if level > current_level + 1:
                    hierarchy_errors += 1
                current_level = level
            
            if hierarchy_errors > 0:
                score -= (hierarchy_errors / len(headings)) * 0.3
        
        # Check list structure
        list_pattern = r'^[\-\*\+]\s+'
        list_lines = re.findall(list_pattern, content, re.MULTILINE)
        
        if list_lines:
            total_checks += 1
            # Simple check for list formatting
            if len(list_lines) > 0:
                score -= 0.1  # Minor penalty for potential issues
        
        # Check code blocks
        code_pattern = r'```'
        code_blocks = re.findall(code_pattern, content)
        
        if code_blocks:
            total_checks += 1
            if len(code_blocks) % 2 != 0:
                score -= 0.2
        
        return max(0.0, score) if total_checks > 0 else 1.0
    
    def _assess_table_quality(self, extraction_result: Dict[str, Any]) -> Dict[str, float]:
        """Assess table quality and structure."""
        metrics = {}
        tables = extraction_result.get("tables", [])
        
        if not tables:
            metrics["table_grits"] = 1.0  # No tables to assess
            return metrics
        
        total_grits = 0.0
        for table in tables:
            # Calculate GriTS (Grid Table Similarity) score
            grits_score = self._calculate_table_grits(table)
            total_grits += grits_score
        
        metrics["table_grits"] = total_grits / len(tables)
        metrics["table_count"] = len(tables)
        
        return metrics
    
    def _calculate_table_grits(self, table: Dict[str, Any]) -> float:
        """Calculate GriTS score for a table."""
        # Simplified GriTS calculation
        # In practice, this would compare table structure against ground truth
        
        raw_data = table.get("raw_data", [])
        if not raw_data:
            return 0.0
        
        # Basic structure checks
        score = 1.0
        
        # Check for consistent row lengths
        row_lengths = [len(row) for row in raw_data]
        if len(set(row_lengths)) > 1:
            score -= 0.2
        
        # Check for empty cells
        empty_cells = sum(1 for row in raw_data for cell in row if not cell or cell.strip() == "")
        total_cells = sum(len(row) for row in raw_data)
        
        if total_cells > 0:
            empty_ratio = empty_cells / total_cells
            if empty_ratio > 0.5:
                score -= 0.3
        
        return max(0.0, score)
    
    def _validate_math_equations(self, extraction_result: Dict[str, Any]) -> Dict[str, float]:
        """Validate mathematical equations."""
        metrics = {}
        equations = extraction_result.get("math_equations", [])
        
        if not equations:
            metrics["math_token_match"] = 1.0  # No equations to validate
            return metrics
        
        # Placeholder for math validation
        # In practice, this would validate LaTeX syntax and compare against reference
        metrics["math_token_match"] = 0.9  # Placeholder
        metrics["equation_count"] = len(equations)
        
        return metrics
    
    def _cross_validate_results(self, extraction_result: Dict[str, Any]) -> List[ProcessingDefect]:
        """Cross-validate results using multiple approaches."""
        defects = []
        
        # This would implement dual-tool cross-validation
        # For now, return empty list as placeholder
        logger.info("Cross-validation checks not yet implemented")
        
        return defects
