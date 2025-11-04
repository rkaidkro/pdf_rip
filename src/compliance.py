"""
Compliance and governance module for data handling.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from .models import ComplianceConfig


class ComplianceGuard:
    """Compliance and governance controls for PDF processing."""
    
    def __init__(self):
        # PII patterns for detection
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "url": r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
        }
        
        # Classification tags
        self.classification_tags = {
            "UNCLASSIFIED": "Public information",
            "INTERNAL": "Internal use only",
            "CONFIDENTIAL": "Confidential information",
            "RESTRICTED": "Restricted access"
        }
        
        # Audit log
        self.audit_log = []
    
    def apply_checks(self, content: str, compliance_config: ComplianceConfig) -> Dict[str, Any]:
        """Apply compliance checks and redaction to content."""
        result = {
            "processed_content": content,
            "log": [],
            "redactions": [],
            "classification_applied": compliance_config.classification_tag
        }
        
        # Apply classification tag
        if compliance_config.classification_tag:
            result["processed_content"] = self._apply_classification_tag(
                result["processed_content"], 
                compliance_config.classification_tag
            )
            result["log"].append({
                "timestamp": datetime.now().isoformat(),
                "action": "classification_applied",
                "tag": compliance_config.classification_tag
            })
        
        # Apply PII redaction if enabled
        if compliance_config.pii_redaction:
            redaction_result = self._redact_pii(result["processed_content"])
            result["processed_content"] = redaction_result["content"]
            result["redactions"] = redaction_result["redactions"]
            result["log"].extend(redaction_result["log"])
        
        # Log compliance actions
        self._log_compliance_action(compliance_config, result)
        
        return result
    
    def _apply_classification_tag(self, content: str, classification: str) -> str:
        """Apply classification tag to content."""
        if not classification or classification == "UNCLASSIFIED":
            return content
        
        # Add classification header
        header = f"# {classification}\n\n"
        return header + content
    
    def _redact_pii(self, content: str) -> Dict[str, Any]:
        """Redact personally identifiable information from content."""
        result = {
            "content": content,
            "redactions": [],
            "log": []
        }
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                original_text = match.group(0)
                redacted_text = self._generate_redaction_text(pii_type, original_text)
                
                # Replace in content
                result["content"] = result["content"].replace(original_text, redacted_text)
                
                # Record redaction
                redaction = {
                    "type": pii_type,
                    "original": original_text,
                    "redacted": redacted_text,
                    "position": match.span()
                }
                result["redactions"].append(redaction)
                
                # Log redaction
                result["log"].append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "pii_redacted",
                    "type": pii_type,
                    "position": match.span()
                })
        
        return result
    
    def _generate_redaction_text(self, pii_type: str, original: str) -> str:
        """Generate redaction text for PII."""
        if pii_type == "email":
            # Redact email: user@domain.com -> [REDACTED_EMAIL]
            return "[REDACTED_EMAIL]"
        elif pii_type == "phone":
            # Redact phone: (123) 456-7890 -> [REDACTED_PHONE]
            return "[REDACTED_PHONE]"
        elif pii_type == "ssn":
            # Redact SSN: 123-45-6789 -> [REDACTED_SSN]
            return "[REDACTED_SSN]"
        elif pii_type == "credit_card":
            # Redact credit card: 1234-5678-9012-3456 -> [REDACTED_CC]
            return "[REDACTED_CC]"
        elif pii_type == "ip_address":
            # Redact IP: 192.168.1.1 -> [REDACTED_IP]
            return "[REDACTED_IP]"
        elif pii_type == "url":
            # Redact URL: https://example.com -> [REDACTED_URL]
            return "[REDACTED_URL]"
        else:
            # Generic redaction
            return "[REDACTED]"
    
    def _log_compliance_action(self, compliance_config: ComplianceConfig, result: Dict[str, Any]) -> None:
        """Log compliance actions for audit trail."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "classification": compliance_config.classification_tag,
            "pii_redaction": compliance_config.pii_redaction,
            "export_assets": compliance_config.export_assets,
            "redactions_count": len(result.get("redactions", [])),
            "actions": result.get("log", [])
        }
        
        self.audit_log.append(audit_entry)
        
        # Log to system log
        logger.info(f"Compliance actions applied: {audit_entry}")
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the audit log."""
        return self.audit_log.copy()
    
    def export_audit_log(self, filepath: str) -> None:
        """Export audit log to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.audit_log, f, indent=2, ensure_ascii=False)
            logger.info(f"Audit log exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
    
    def validate_classification(self, classification: str) -> bool:
        """Validate that a classification tag is recognized."""
        return classification in self.classification_tags
    
    def get_classification_description(self, classification: str) -> Optional[str]:
        """Get description for a classification tag."""
        return self.classification_tags.get(classification)
    
    def list_classifications(self) -> Dict[str, str]:
        """List all available classification tags."""
        return self.classification_tags.copy()
    
    def add_custom_pii_pattern(self, name: str, pattern: str) -> None:
        """Add a custom PII detection pattern."""
        try:
            re.compile(pattern)  # Validate regex
            self.pii_patterns[name] = pattern
            logger.info(f"Added custom PII pattern: {name}")
        except re.error as e:
            logger.error(f"Invalid regex pattern for {name}: {e}")
    
    def remove_pii_pattern(self, name: str) -> bool:
        """Remove a PII detection pattern."""
        if name in self.pii_patterns:
            del self.pii_patterns[name]
            logger.info(f"Removed PII pattern: {name}")
            return True
        return False
    
    def scan_for_pii(self, content: str) -> Dict[str, List[str]]:
        """Scan content for PII without redacting."""
        findings = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                findings[pii_type] = list(set(matches))  # Remove duplicates
        
        return findings
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get a summary of compliance activities."""
        total_actions = len(self.audit_log)
        total_redactions = sum(entry.get("redactions_count", 0) for entry in self.audit_log)
        
        classification_counts = {}
        for entry in self.audit_log:
            classification = entry.get("classification", "UNKNOWN")
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
        
        return {
            "total_actions": total_actions,
            "total_redactions": total_redactions,
            "classification_distribution": classification_counts,
            "pii_patterns_configured": len(self.pii_patterns),
            "last_action": self.audit_log[-1] if self.audit_log else None
        }
