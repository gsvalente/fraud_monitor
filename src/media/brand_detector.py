"""Text-Based Brand Detection Module

This module provides functionality to detect brand names in OCR-extracted text.
It's designed to work with the existing OCR processing pipeline and fraud detection system.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

@dataclass
class BrandMatch:
    """Represents a detected brand match in text."""
    brand: str
    confidence: float
    position: int
    matched_text: str
    risk_level: str

class BrandDetector:
    """
    Text-based brand detector for OCR results.
    
    This class detects brand names in text extracted from images and provides
    easy management of brand lists with various matching strategies.
    """
    
    def __init__(self, brands_file: str = "config/brands.json"):
        """
        Initialize the brand detector.
        
        Args:
            brands_file: Path to JSON file containing brand configurations
        """
        self.brands_file = Path(brands_file)
        self.brands_config = {}
        self.load_brands()
    
    def load_brands(self):
        """Load brand configurations from JSON file."""
        if not self.brands_file.exists():
            print(f"Brands file '{self.brands_file}' not found. Creating default configuration...")
            self._create_default_brands_file()
        
        try:
            with open(self.brands_file, 'r', encoding='utf-8') as f:
                self.brands_config = json.load(f)
            print(f"Loaded {len(self.brands_config)} brand configurations")
        except Exception as e:
            print(f"Error loading brands file: {e}")
            self._create_default_brands_file()
    
    def _create_default_brands_file(self):
        """Create default brands configuration file."""
        default_brands = {
            "paypal": {
                "name": "PayPal",
                "patterns": ["paypal", "pay pal", "pay-pal"],
                "case_sensitive": False,
                "risk_weight": 0.9,
                "category": "payment"
            },
            "binance": {
                "name": "Binance",
                "patterns": ["binance", "bnb"],
                "case_sensitive": False,
                "risk_weight": 0.8,
                "category": "crypto"
            },
            "coinbase": {
                "name": "Coinbase",
                "patterns": ["coinbase", "coin base"],
                "case_sensitive": False,
                "risk_weight": 0.8,
                "category": "crypto"
            },
            "metamask": {
                "name": "MetaMask",
                "patterns": ["metamask", "meta mask"],
                "case_sensitive": False,
                "risk_weight": 0.7,
                "category": "crypto"
            },
            "apple": {
                "name": "Apple",
                "patterns": ["apple", "app store", "itunes"],
                "case_sensitive": False,
                "risk_weight": 0.6,
                "category": "tech"
            },
            "google": {
                "name": "Google",
                "patterns": ["google", "gmail", "google pay"],
                "case_sensitive": False,
                "risk_weight": 0.6,
                "category": "tech"
            },
            "amazon": {
                "name": "Amazon",
                "patterns": ["amazon", "aws"],
                "case_sensitive": False,
                "risk_weight": 0.7,
                "category": "ecommerce"
            },
            "microsoft": {
                "name": "Microsoft",
                "patterns": ["microsoft", "outlook", "xbox"],
                "case_sensitive": False,
                "risk_weight": 0.6,
                "category": "tech"
            }
        }
        
        # Ensure config directory exists
        self.brands_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.brands_file, 'w', encoding='utf-8') as f:
            json.dump(default_brands, f, indent=2, ensure_ascii=False)
        
        self.brands_config = default_brands
        print(f"Created default brands configuration with {len(default_brands)} brands")
    
    def detect_brands(self, text: str) -> List[BrandMatch]:
        """
        Detect brand names in the given text.
        
        Args:
            text: Text to analyze (usually from OCR)
            
        Returns:
            List of BrandMatch objects for detected brands
        """
        if not text or not self.brands_config:
            return []
        
        matches = []
        
        for brand_id, config in self.brands_config.items():
            brand_matches = self._find_brand_matches(text, brand_id, config)
            matches.extend(brand_matches)
        
        # Sort by position and remove duplicates
        matches = self._deduplicate_matches(matches)
        
        return matches
    
    def _find_brand_matches(self, text: str, brand_id: str, config: Dict) -> List[BrandMatch]:
        """Find all matches for a specific brand in the text."""
        matches = []
        search_text = text if config.get('case_sensitive', False) else text.lower()
        
        for pattern in config['patterns']:
            search_pattern = pattern if config.get('case_sensitive', False) else pattern.lower()
            
            # Use word boundaries for better matching
            regex_pattern = r'\b' + re.escape(search_pattern) + r'\b'
            
            for match in re.finditer(regex_pattern, search_text):
                confidence = self._calculate_confidence(match.group(), pattern, config)
                risk_level = self._assess_risk(confidence, config['risk_weight'])
                
                brand_match = BrandMatch(
                    brand=config['name'],
                    confidence=confidence,
                    position=match.start(),
                    matched_text=text[match.start():match.end()],  # Original case
                    risk_level=risk_level
                )
                matches.append(brand_match)
        
        return matches
    
    def _calculate_confidence(self, matched_text: str, pattern: str, config: Dict) -> float:
        """Calculate confidence score for a match."""
        base_confidence = 0.8
        
        # Exact match bonus
        if matched_text.lower() == pattern.lower():
            base_confidence += 0.1
        
        # Brand risk weight factor
        risk_factor = config.get('risk_weight', 0.5)
        
        return min(base_confidence * (0.5 + risk_factor), 1.0)
    
    def _assess_risk(self, confidence: float, risk_weight: float) -> str:
        """Assess risk level based on confidence and brand risk weight."""
        combined_score = confidence * risk_weight
        
        if combined_score >= 0.8:
            return "HIGH"
        elif combined_score >= 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _deduplicate_matches(self, matches: List[BrandMatch]) -> List[BrandMatch]:
        """Remove duplicate matches and sort by position."""
        if not matches:
            return []
        
        # Sort by position
        matches.sort(key=lambda x: x.position)
        
        # Remove overlapping matches (keep highest confidence)
        filtered_matches = []
        
        for match in matches:
            is_duplicate = False
            
            for existing in filtered_matches:
                # Check if positions overlap
                if abs(match.position - existing.position) < max(len(match.matched_text), len(existing.matched_text)):
                    if match.confidence <= existing.confidence:
                        is_duplicate = True
                        break
                    else:
                        # Remove the existing lower-confidence match
                        filtered_matches.remove(existing)
                        break
            
            if not is_duplicate:
                filtered_matches.append(match)
        
        return filtered_matches
    
    def get_supported_brands(self) -> List[str]:
        """Get list of currently supported brands."""
        return [config['name'] for config in self.brands_config.values()]
    
    def get_brands_by_category(self, category: str) -> List[str]:
        """Get brands filtered by category."""
        return [
            config['name'] for config in self.brands_config.values()
            if config.get('category') == category
        ]
    
    def add_brand(self, brand_id: str, name: str, patterns: List[str], 
                  risk_weight: float = 0.7, category: str = "other", 
                  case_sensitive: bool = False) -> bool:
        """
        Add a new brand to the configuration.
        
        Args:
            brand_id: Unique identifier for the brand
            name: Display name of the brand
            patterns: List of text patterns to match
            risk_weight: Risk weight factor (0.0-1.0)
            category: Brand category
            case_sensitive: Whether matching should be case sensitive
            
        Returns:
            True if brand was added successfully
        """
        try:
            self.brands_config[brand_id] = {
                "name": name,
                "patterns": patterns,
                "case_sensitive": case_sensitive,
                "risk_weight": risk_weight,
                "category": category
            }
            
            self._save_brands_config()
            print(f"Added brand: {name} with {len(patterns)} patterns")
            return True
            
        except Exception as e:
            print(f"Error adding brand {name}: {e}")
            return False
    
    def remove_brand(self, brand_id: str) -> bool:
        """
        Remove a brand from the configuration.
        
        Args:
            brand_id: Unique identifier of the brand to remove
            
        Returns:
            True if brand was removed successfully
        """
        try:
            if brand_id in self.brands_config:
                brand_name = self.brands_config[brand_id]['name']
                del self.brands_config[brand_id]
                self._save_brands_config()
                print(f"Removed brand: {brand_name}")
                return True
            else:
                print(f"Brand ID '{brand_id}' not found")
                return False
                
        except Exception as e:
            print(f"Error removing brand {brand_id}: {e}")
            return False
    
    def update_brand_patterns(self, brand_id: str, new_patterns: List[str]) -> bool:
        """
        Update patterns for an existing brand.
        
        Args:
            brand_id: Unique identifier of the brand
            new_patterns: New list of patterns to match
            
        Returns:
            True if patterns were updated successfully
        """
        try:
            if brand_id in self.brands_config:
                self.brands_config[brand_id]['patterns'] = new_patterns
                self._save_brands_config()
                print(f"Updated patterns for brand: {self.brands_config[brand_id]['name']}")
                return True
            else:
                print(f"Brand ID '{brand_id}' not found")
                return False
                
        except Exception as e:
            print(f"Error updating patterns for brand {brand_id}: {e}")
            return False
    
    def _save_brands_config(self):
        """Save current brands configuration to file."""
        try:
            with open(self.brands_file, 'w', encoding='utf-8') as f:
                json.dump(self.brands_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving brands configuration: {e}")
    
    def get_brand_info(self, brand_id: str) -> Optional[Dict]:
        """Get detailed information about a specific brand."""
        return self.brands_config.get(brand_id)
    
    def get_detection_summary(self, matches: List[BrandMatch]) -> Dict:
        """
        Generate a summary of brand detections
        
        Args:
            matches: List of BrandMatch objects
            
        Returns:
            Dictionary with detection summary
        """
        if not matches:
            return {
                'total_detections': 0,
                'brands_detected': [],
                'highest_confidence': 0.0,
                'risk_level': 'LOW'
            }
        
        brands_detected = list(set(match.brand for match in matches))
        highest_confidence = max(match.confidence for match in matches)
        
        # Determine risk level based on detections
        risk_level = 'LOW'
        if len(matches) > 0:
            if highest_confidence > 0.9:
                risk_level = 'HIGH'
            elif highest_confidence > 0.8:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
        
        return {
            'total_detections': len(matches),
            'brands_detected': brands_detected,
            'highest_confidence': highest_confidence,
            'risk_level': risk_level,
            'matches': [
                {
                    'brand': match.brand,
                    'confidence': match.confidence,
                    'position': match.position,
                    'matched_text': match.matched_text,
                    'risk_level': match.risk_level
                }
                for match in matches
            ]
        }