"""
Encoding utilities for handling API responses with various character encodings.
"""

import json
import logging

logger = logging.getLogger(__name__)

def safe_decode_json(content: bytes) -> dict:
    """
    Safely decode bytes content to JSON with fallback encoding handling.
    
    Args:
        content: Raw bytes content from API response
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        json.JSONDecodeError: If content cannot be parsed as JSON
        UnicodeDecodeError: If content cannot be decoded with any encoding
    """
    # Try UTF-8 first (most common for modern APIs)
    try:
        text = content.decode('utf-8')
        return json.loads(text)
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed, trying with error replacement")
        try:
            # Try UTF-8 with error replacement
            text = content.decode('utf-8', errors='replace')
            return json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("UTF-8 with replacement failed, trying latin-1")
            try:
                # Fallback to latin-1 (handles most byte sequences)
                text = content.decode('latin-1')
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("latin-1 decode failed, trying cp1252")
                try:
                    # Windows encoding fallback
                    text = content.decode('cp1252', errors='replace')
                    return json.loads(text)
                except json.JSONDecodeError:
                    logger.error("All encoding attempts failed")
                    raise

def safe_decode_text(content: bytes) -> str:
    """
    Safely decode bytes content to text with fallback encoding handling.
    
    Args:
        content: Raw bytes content
        
    Returns:
        Decoded text string
    """
    # Try UTF-8 first
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed, trying with error replacement")
        try:
            return content.decode('utf-8', errors='replace')
        except UnicodeDecodeError:
            logger.warning("UTF-8 with replacement failed, trying latin-1")
            try:
                return content.decode('latin-1')
            except UnicodeDecodeError:
                logger.warning("latin-1 decode failed, trying cp1252")
                return content.decode('cp1252', errors='replace')
