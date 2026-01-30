"""
PII Detection Module - Safe PII Detection Without Storing PII

This module detects personally identifiable information (PII) without
storing, logging, or transmitting any PII. It only returns a boolean
result: True (PII detected) or False (safe to post).

Design Principles:
1. PII patterns are stored in-memory during runtime only
2. No PII is ever written to disk, logs, or network
3. Detection is performed locally - no external API calls
4. Returns boolean only - no matched data returned
"""

import re
from typing import Set, Optional

# ============================================================================
# PII PATTERNS - Static, no PII stored
# ============================================================================

# Common PII patterns (static, no actual PII values)
PII_PATTERNS = {
    # Email pattern
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    
    # Phone patterns (US formats)
    "phone": re.compile(r'(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'),
    
    # SSN pattern
    "ssn": re.compile(r'\d{3}-\d{2}-\d{4}'),
    
    # Credit card pattern
    "credit_card": re.compile(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}'),
    
    # IP address pattern
    "ip_address": re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'),
    
    # Date patterns (potential DOB)
    "date": re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'),
}

# ============================================================================
# PII DETECTOR CLASS - Runtime memory only
# ============================================================================

class PIIDetector:
    """
    PII Detection that never stores PII.
    
    Usage:
        detector = PIIDetector()
        detector.add_creator_name("CREATOR_NAME")
        
        if detector.contains_pii("Hello from CREATOR_NAME"):
            print("PII detected - would be blocked")
        else:
            print("Safe to post")
    
    All PII is stored in-memory only and lost when the process ends.
    """
    
    def __init__(self):
        # In-memory only - never persisted
        self._creator_names: Set[str] = set()
        self._creator_handles: Set[str] = set()
        self._creator_locations: Set[str] = set()
        self._creator_employers: Set[str] = set()
        self._creator_family: Set[str] = set()
        self._creator_phone: Set[str] = set()
        self._creator_email: Set[str] = set()
        self._creator_addresses: Set[str] = set()
        self._custom_patterns: Set[re.Pattern] = set()
    
    def add_creator_name(self, name: str) -> None:
        """Add creator's name to detection (in-memory only)."""
        # Normalize for detection
        normalized = name.lower().strip()
        self._creator_names.add(normalized)
    
    def add_creator_handle(self, handle: str) -> None:
        """Add creator's social handles (in-memory only)."""
        normalized = handle.lower().strip().lstrip('@')
        self._creator_handles.add(normalized)
    
    def add_creator_location(self, location: str) -> None:
        """Add creator's location (in-memory only)."""
        normalized = location.lower().strip()
        self._creator_locations.add(normalized)
    
    def add_creator_employer(self, employer: str) -> None:
        """Add creator's employer (in-memory only)."""
        normalized = employer.lower().strip()
        self._creator_employers.add(normalized)
    
    def add_creator_family(self, name: str) -> None:
        """Add family member names (in-memory only)."""
        normalized = name.lower().strip()
        self._creator_family.add(normalized)
    
    def add_creator_phone(self, phone: str) -> None:
        """Add creator's phone number (in-memory only)."""
        # Store normalized version
        normalized = re.sub(r'[^\d]', '', phone)
        self._creator_phone.add(normalized)
    
    def add_creator_email(self, email: str) -> None:
        """Add creator's email (in-memory only)."""
        normalized = email.lower().strip()
        self._creator_email.add(normalized)
    
    def add_creator_address(self, address: str) -> None:
        """Add creator's address (in-memory only)."""
        normalized = address.lower().strip()
        self._creator_addresses.add(normalized)
    
    def add_custom_pattern(self, pattern: str) -> None:
        """Add a custom regex pattern (in-memory only)."""
        try:
            self._custom_patterns.add(re.compile(pattern, re.IGNORECASE))
        except re.error:
            pass  # Invalid pattern - ignore
    
    def _check_patterns(self, text: str) -> bool:
        """Check text against static PII patterns."""
        for name, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                return True
        return False
    
    def _check_creator_pii(self, text: str) -> bool:
        """Check text against creator-specific PII."""
        text_lower = text.lower()
        
        # Check each category
        for name in self._creator_names:
            if name in text_lower:
                return True
        
        for handle in self._creator_handles:
            if handle in text_lower:
                return True
        
        for location in self._creator_locations:
            if location in text_lower:
                return True
        
        for employer in self._creator_employers:
            if employer in text_lower:
                return True
        
        for family in self._creator_family:
            if family in text_lower:
                return True
        
        # Check phone numbers (normalized)
        text_nums = re.sub(r'[^\d]', '', text)
        for phone in self._creator_phone:
            if phone in text_nums:
                return True
        
        for email in self._creator_email:
            if email in text_lower:
                return True
        
        for address in self._creator_addresses:
            if address in text_lower:
                return True
        
        return False
    
    def _check_custom_patterns(self, text: str) -> bool:
        """Check against custom patterns."""
        for pattern in self._custom_patterns:
            if pattern.search(text):
                return True
        return False
    
    def contains_pii(self, text: str) -> bool:
        """
        Check if text contains PII.
        
        Args:
            text: Text to check
            
        Returns:
            True if PII is detected, False if safe
        """
        # Check static patterns first
        if self._check_patterns(text):
            return True
        
        # Check creator-specific PII
        if self._check_creator_pii(text):
            return True
        
        # Check custom patterns
        if self._check_custom_patterns(text):
            return True
        
        return False
    
    def check_and_sanitize(self, text: str, placeholder: str = "[REDACTED]") -> tuple:
        """
        Check for PII and return sanitized version.
        
        Args:
            text: Text to check
            placeholder: What to replace detected PII with
            
        Returns:
            Tuple of (contains_pii: bool, sanitized_text: str)
        """
        if not self.contains_pii(text):
            return False, text
        
        # Sanitize by removing patterns
        sanitized = text
        
        # Remove static pattern matches
        for name, pattern in PII_PATTERNS.items():
            sanitized = pattern.sub(placeholder, sanitized)
        
        # Remove creator-specific PII
        for name in self._creator_names:
            sanitized = sanitized.replace(name, placeholder)
        
        for handle in self._creator_handles:
            sanitized = sanitized.replace(handle, placeholder)
        
        return True, sanitized
    
    def clear_all(self) -> None:
        """Clear all PII data from memory."""
        self._creator_names.clear()
        self._creator_handles.clear()
        self._creator_locations.clear()
        self._creator_employers.clear()
        self._creator_family.clear()
        self._creator_phone.clear()
        self._creator_email.clear()
        self._creator_addresses.clear()
        self._custom_patterns.clear()
    
    def get_stats(self) -> dict:
        """Get detection stats (no PII values returned)."""
        return {
            "creator_names_count": len(self._creator_names),
            "creator_handles_count": len(self._creator_handles),
            "creator_locations_count": len(self._creator_locations),
            "creator_employers_count": len(self._creator_employers),
            "creator_family_count": len(self._creator_family),
            "creator_phone_count": len(self._creator_phone),
            "creator_email_count": len(self._creator_email),
            "creator_address_count": len(self._creator_addresses),
            "custom_patterns_count": len(self._custom_patterns),
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_detector() -> PIIDetector:
    """Create a new PII detector with default configuration."""
    return PIIDetector()


def create_detector_with_creator(
    name: str,
    handle: Optional[str] = None,
    location: Optional[str] = None,
    employer: Optional[str] = None
) -> PIIDetector:
    """
    Create a PII detector configured for a specific creator.
    
    Args:
        name: Creator's name
        handle: Creator's social handle
        location: Creator's location
        employer: Creator's employer
        
    Returns:
        Configured PIIDetector
    """
    detector = PIIDetector()
    detector.add_creator_name(name)
    
    if handle:
        detector.add_creator_handle(handle)
    if location:
        detector.add_creator_location(location)
    if employer:
        detector.add_creator_employer(employer)
    
    return detector


if __name__ == "__main__":
    # Demo - no actual PII stored
    detector = create_detector_with_creator(
        name="CREATOR_NAME",
        handle="CREATOR_HANDLE",
        location="LOCATION"
    )
    
    test_texts = [
        "Hello from CREATOR_NAME in LOCATION!",
        "Contact me at seth@example.com",
        "My phone is 555-123-4567",
        "This post is about automation",
    ]
    
    for text in test_texts:
        has_pii = detector.contains_pii(text)
        print(f"PII Detected: {has_pii} | Text: {text}")
