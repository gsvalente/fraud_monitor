"""
Fraud Detection Engine

This module provides the core fraud detection functionality,
following Clean Code principles and SOLID design patterns.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math

from colorama import Fore, Style

from src.fraud_detection.keyword_manager import KeywordManager, FraudKeyword, FraudCategory
from config.fraud_config import fraud_config


@dataclass
class DetectionResult:
    """Result of fraud detection analysis"""
    is_suspicious: bool
    fraud_score: float
    detected_keywords: List[str]
    detection_method: str
    confidence_level: str
    analysis_details: Dict[str, any]
    
    @property
    def risk_level(self) -> str:
        """Get human-readable risk level"""
        if self.fraud_score >= 0.9:
            return "CRITICAL"
        elif self.fraud_score >= 0.75:
            return "HIGH"
        elif self.fraud_score >= 0.5:
            return "MEDIUM"
        elif self.fraud_score >= 0.25:
            return "LOW"
        else:
            return "MINIMAL"


@dataclass
class ContextualFactors:
    """Contextual information that affects fraud scoring"""
    sender_username: Optional[str] = None
    group_name: Optional[str] = None
    message_length: int = 0
    has_media: bool = False
    timestamp: Optional[datetime] = None
    urgency_indicators: List[str] = None
    financial_terms: List[str] = None
    contact_requests: List[str] = None


class TextPreprocessor:
    """
    Handles text preprocessing for fraud detection
    
    Follows Single Responsibility Principle
    """
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text for analysis"""
        if not text:
            return ""
            
        # Convert to lowercase
        cleaned = text.lower()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove special characters but keep basic punctuation
        cleaned = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', cleaned)
        
        return cleaned.strip()
    
    @staticmethod
    def extract_words(text: str) -> Set[str]:
        """Extract individual words from text"""
        cleaned_text = TextPreprocessor.clean_text(text)
        words = set(re.findall(r'\b\w+\b', cleaned_text))
        return words
    
    @staticmethod
    def extract_phrases(text: str, max_phrase_length: int = 4) -> Set[str]:
        """Extract phrases of different lengths"""
        cleaned_text = TextPreprocessor.clean_text(text)
        words = cleaned_text.split()
        phrases = set()
        
        # Add individual words
        phrases.update(words)
        
        # Add multi-word phrases
        for length in range(2, min(max_phrase_length + 1, len(words) + 1)):
            for i in range(len(words) - length + 1):
                phrase = ' '.join(words[i:i + length])
                phrases.add(phrase)
                
        return phrases


class ContextualAnalyzer:
    """
    Analyzes contextual factors that influence fraud probability
    """
    
    # Urgency indicators that increase fraud likelihood
    URGENCY_PATTERNS = [
        r'\b(urgent|asap|immediately|now|quick|fast|hurry)\b',
        r'\b(limited time|expires|deadline|act now)\b',
        r'\b(last chance|final|ending soon)\b'
    ]
    
    # Financial terms that indicate monetary scams
    FINANCIAL_PATTERNS = [
        r'\b(money|cash|payment|transfer|send|wire)\b',
        r'\b(bitcoin|crypto|investment|profit|earn)\b',
        r'\b(bank|account|card|paypal|venmo)\b',
        r'\b(\$\d+|usd|dollars|euros|pounds)\b'
    ]
    
    # Contact request patterns
    CONTACT_PATTERNS = [
        r'\b(call me|text me|dm me|contact me)\b',
        r'\b(whatsapp|telegram|signal|discord)\b',
        r'\b(phone|number|email|address)\b'
    ]
    
    @staticmethod
    def analyze_context(text: str, context: Optional[Dict] = None) -> ContextualFactors:
        """Analyze contextual factors in the text and metadata"""
        factors = ContextualFactors()
        
        if context:
            factors.sender_username = context.get('sender_username')
            factors.group_name = context.get('group_name')
            factors.has_media = context.get('has_media', False)
            factors.timestamp = context.get('timestamp')
        
        factors.message_length = len(text)
        
        # Analyze text patterns
        factors.urgency_indicators = ContextualAnalyzer._find_patterns(text, ContextualAnalyzer.URGENCY_PATTERNS)
        factors.financial_terms = ContextualAnalyzer._find_patterns(text, ContextualAnalyzer.FINANCIAL_PATTERNS)
        factors.contact_requests = ContextualAnalyzer._find_patterns(text, ContextualAnalyzer.CONTACT_PATTERNS)
        
        return factors
    
    @staticmethod
    def _find_patterns(text: str, patterns: List[str]) -> List[str]:
        """Find matching patterns in text"""
        matches = []
        text_lower = text.lower()
        
        for pattern in patterns:
            found = re.findall(pattern, text_lower)
            matches.extend(found)
        
        return list(set(matches))  # Remove duplicates


class AdvancedFraudScoreCalculator:
    """
    Advanced fraud score calculator with contextual analysis
    """
    
    @staticmethod
    def calculate_base_score(detected_keywords: List[FraudKeyword]) -> float:
        """Calculate base fraud score from detected keywords"""
        if not detected_keywords:
            return 0.0
            
        # Use maximum score approach with diminishing returns
        scores = sorted([kw.score for kw in detected_keywords], reverse=True)
        
        if len(scores) == 1:
            return scores[0]
        
        # Primary score + diminishing additional scores
        total_score = scores[0]
        for i, score in enumerate(scores[1:], 1):
            # Each additional keyword contributes less
            weight = 1.0 / (i + 1)
            total_score += score * weight * 0.3  # 30% weight for additional keywords
            
        return min(total_score, 1.0)  # Cap at 1.0
    
    @staticmethod
    def calculate_contextual_multiplier(factors: ContextualFactors) -> float:
        """Calculate contextual multiplier based on various factors"""
        multiplier = 1.0
        
        # Urgency indicators increase risk
        if factors.urgency_indicators:
            urgency_boost = min(len(factors.urgency_indicators) * 0.15, 0.3)
            multiplier += urgency_boost
        
        # Financial terms increase risk
        if factors.financial_terms:
            financial_boost = min(len(factors.financial_terms) * 0.1, 0.25)
            multiplier += financial_boost
        
        # Contact requests increase risk
        if factors.contact_requests:
            contact_boost = min(len(factors.contact_requests) * 0.1, 0.2)
            multiplier += contact_boost
        
        # Message length factor (very short or very long messages can be suspicious)
        if factors.message_length > 0:
            if factors.message_length < 20:  # Very short messages
                multiplier += 0.1
            elif factors.message_length > 500:  # Very long messages
                multiplier += 0.05
        
        # Media presence can indicate sophisticated scams
        if factors.has_media:
            multiplier += 0.1
        
        return min(multiplier, 2.0)  # Cap at 2.0x
    
    @staticmethod
    def calculate_category_diversity_bonus(detected_keywords: List[FraudKeyword]) -> float:
        """Calculate bonus for detecting keywords from multiple categories"""
        if not detected_keywords:
            return 0.0
            
        categories = set(kw.category for kw in detected_keywords)
        
        # Bonus for multiple categories (indicates sophisticated scam)
        if len(categories) >= 4:
            return 0.2
        elif len(categories) == 3:
            return 0.15
        elif len(categories) == 2:
            return 0.08
        else:
            return 0.0
    
    @staticmethod
    def calculate_advanced_score(detected_keywords: List[FraudKeyword], 
                               factors: ContextualFactors) -> Dict[str, float]:
        """Calculate advanced fraud score with all factors"""
        base_score = AdvancedFraudScoreCalculator.calculate_base_score(detected_keywords)
        contextual_multiplier = AdvancedFraudScoreCalculator.calculate_contextual_multiplier(factors)
        category_bonus = AdvancedFraudScoreCalculator.calculate_category_diversity_bonus(detected_keywords)
        
        # Apply contextual multiplier to base score
        contextual_score = base_score * contextual_multiplier
        
        # Add category bonus
        final_score = min(contextual_score + category_bonus, 1.0)
        
        return {
            'base_score': base_score,
            'contextual_multiplier': contextual_multiplier,
            'category_bonus': category_bonus,
            'contextual_score': contextual_score,
            'final_score': final_score
        }


class FraudScoreCalculator:
    """
    Calculates fraud scores using different algorithms
    
    Follows Open/Closed Principle - easy to add new scoring methods
    """
    
    @staticmethod
    def calculate_weighted_score(detected_keywords: List[FraudKeyword]) -> float:
        """Calculate weighted fraud score based on detected keywords"""
        return AdvancedFraudScoreCalculator.calculate_base_score(detected_keywords)
    
    @staticmethod
    def calculate_category_diversity_bonus(detected_keywords: List[FraudKeyword]) -> float:
        """Calculate bonus for detecting keywords from multiple categories"""
        return AdvancedFraudScoreCalculator.calculate_category_diversity_bonus(detected_keywords)


class FraudDetector:
    """
    Main fraud detection engine
    
    Follows Clean Code principles:
    - Single Responsibility: Only detects fraud
    - Dependency Injection: Uses KeywordManager
    - Open/Closed: Easy to extend with new detection methods
    """
    
    def __init__(self, keyword_manager: KeywordManager):
        self.keyword_manager = keyword_manager
        self.preprocessor = TextPreprocessor()
        self.score_calculator = FraudScoreCalculator()
        self.advanced_calculator = AdvancedFraudScoreCalculator()
        self.contextual_analyzer = ContextualAnalyzer()
        self.logger = logging.getLogger(__name__)
        
        # Detection thresholds
        self.suspicious_threshold = 0.3
        self.high_risk_threshold = 0.7
        
    def detect_fraud(self, text: str, context: Optional[Dict] = None) -> DetectionResult:
        """
        Main fraud detection method with advanced contextual analysis
        
        Args:
            text: Text to analyze
            context: Optional context information (sender, group, etc.)
            
        Returns:
            DetectionResult: Comprehensive detection results
        """
        if not text or not text.strip():
            return self._create_empty_result()
            
        # Preprocess text
        phrases = self.preprocessor.extract_phrases(text)
        
        # Detect keywords
        detected_keywords = self._detect_keywords(phrases)
        
        # Analyze contextual factors
        contextual_factors = self.contextual_analyzer.analyze_context(text, context)
        
        # Calculate advanced fraud score
        score_breakdown = self.advanced_calculator.calculate_advanced_score(
            detected_keywords, contextual_factors
        )
        
        final_score = score_breakdown['final_score']
        
        # Determine if suspicious using configuration
        is_suspicious = fraud_config.is_suspicious(final_score)
        
        # Create comprehensive analysis details
        analysis_details = {
            **score_breakdown,
            "detected_categories": list(set(kw.category.value for kw in detected_keywords)),
            "keyword_count": len(detected_keywords),
            "text_length": len(text),
            "processed_phrases": len(phrases),
            "contextual_factors": {
                "urgency_indicators": contextual_factors.urgency_indicators,
                "financial_terms": contextual_factors.financial_terms,
                "contact_requests": contextual_factors.contact_requests,
                "has_media": contextual_factors.has_media,
                "message_length": contextual_factors.message_length
            }
        }
        
        # Create result
        return DetectionResult(
            is_suspicious=is_suspicious,
            fraud_score=final_score,
            detected_keywords=[kw.keyword for kw in detected_keywords],
            detection_method="advanced_contextual_analysis",
            confidence_level=self._get_advanced_confidence_level(final_score, len(detected_keywords), contextual_factors),
            analysis_details=analysis_details
        )
    
    def _detect_keywords(self, phrases: Set[str]) -> List[FraudKeyword]:
        """Detect fraud keywords in the given phrases"""
        detected = []
        all_keywords = self.keyword_manager.get_all_keywords()
        
        for keyword_obj in all_keywords:
            keyword = keyword_obj.keyword
            
            # Exact match
            if keyword in phrases:
                detected.append(keyword_obj)
                continue
                
            # Partial match for multi-word keywords
            if ' ' in keyword:
                # Check if all words of the keyword appear in the text
                keyword_words = set(keyword.split())
                if keyword_words.issubset(phrases):
                    detected.append(keyword_obj)
        
        return detected
    
    def _get_advanced_confidence_level(self, score: float, keyword_count: int, 
                                     factors: ContextualFactors) -> str:
        """Determine advanced confidence level based on multiple factors"""
        base_confidence = self._get_confidence_level(score, keyword_count)
        
        # Boost confidence if multiple contextual factors are present
        contextual_boost = 0
        if factors.urgency_indicators:
            contextual_boost += 1
        if factors.financial_terms:
            contextual_boost += 1
        if factors.contact_requests:
            contextual_boost += 1
        if factors.has_media:
            contextual_boost += 1
        
        # Upgrade confidence level based on contextual factors
        if contextual_boost >= 3 and base_confidence in ["HIGH", "MEDIUM"]:
            return "VERY_HIGH"
        elif contextual_boost >= 2 and base_confidence == "MEDIUM":
            return "HIGH"
        elif contextual_boost >= 1 and base_confidence == "LOW":
            return "MEDIUM"
        
        return base_confidence
    
    def _get_confidence_level(self, score: float, keyword_count: int) -> str:
        """Determine confidence level based on score and keyword count"""
        if score >= 0.8 and keyword_count >= 2:
            return "VERY_HIGH"
        elif score >= 0.6 and keyword_count >= 1:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score >= 0.2:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _create_empty_result(self) -> DetectionResult:
        """Create empty detection result for invalid input"""
        return DetectionResult(
            is_suspicious=False,
            fraud_score=0.0,
            detected_keywords=[],
            detection_method="none",
            confidence_level="NONE",
            analysis_details={}
        )
    
    def analyze_batch(self, texts: List[str], contexts: Optional[List[Dict]] = None) -> List[DetectionResult]:
        """Analyze multiple texts in batch with optional contexts"""
        results = []
        for i, text in enumerate(texts):
            context = contexts[i] if contexts and i < len(contexts) else None
            result = self.detect_fraud(text, context)
            results.append(result)
        return results
    
    def get_detection_stats(self) -> Dict[str, any]:
        """Get statistics about the detection system"""
        all_keywords = self.keyword_manager.get_all_keywords()
        
        return {
            "total_keywords": len(all_keywords),
            "high_risk_keywords": len([kw for kw in all_keywords if kw.score >= 0.7]),
            "categories": len(set(kw.category for kw in all_keywords)),
            "average_score": sum(kw.score for kw in all_keywords) / len(all_keywords) if all_keywords else 0,
            "thresholds": {
                "suspicious": self.suspicious_threshold,
                "high_risk": self.high_risk_threshold
            },
            "features": [
                "Advanced contextual analysis",
                "Urgency pattern detection",
                "Financial term analysis",
                "Contact request detection",
                "Multi-factor confidence scoring"
            ]
        }
    
    def print_detection_result(self, result: DetectionResult, text: str = None) -> None:
        """Print formatted detection result with enhanced details"""
        risk_colors = {
            "CRITICAL": Fore.MAGENTA,
            "HIGH": Fore.RED,
            "MEDIUM": Fore.YELLOW,
            "LOW": Fore.BLUE,
            "MINIMAL": Fore.GREEN
        }
        
        risk_color = risk_colors.get(result.risk_level, Fore.WHITE)
        
        print(f"\n{Fore.CYAN}🔍 Advanced Fraud Detection Result{Style.RESET_ALL}")
        print("=" * 50)
        
        if text:
            print(f"{Fore.WHITE}Text: {text[:100]}{'...' if len(text) > 100 else ''}{Style.RESET_ALL}")
            
        print(f"Risk Level: {risk_color}{result.risk_level}{Style.RESET_ALL}")
        print(f"Fraud Score: {risk_color}{result.fraud_score:.3f}{Style.RESET_ALL}")
        print(f"Suspicious: {'🚨 YES' if result.is_suspicious else '✅ NO'}")
        print(f"Confidence: {result.confidence_level}")
        print(f"Method: {result.detection_method}")
        
        if result.detected_keywords:
            print(f"\n{Fore.YELLOW}Detected Keywords:{Style.RESET_ALL}")
            for keyword in result.detected_keywords:
                kw_obj = self.keyword_manager.get_keyword(keyword)
                if kw_obj:
                    print(f"  • {keyword} ({kw_obj.category.value}, score: {kw_obj.score})")
        
        if result.analysis_details:
            print(f"\n{Fore.BLUE}Advanced Analysis:{Style.RESET_ALL}")
            
            # Score breakdown
            if 'base_score' in result.analysis_details:
                print(f"  • Base Score: {result.analysis_details['base_score']:.3f}")
                print(f"  • Contextual Multiplier: {result.analysis_details['contextual_multiplier']:.2f}x")
                print(f"  • Category Bonus: {result.analysis_details['category_bonus']:.3f}")
            
            # Contextual factors
            if 'contextual_factors' in result.analysis_details:
                factors = result.analysis_details['contextual_factors']
                if any(factors.values()):
                    print(f"  • Contextual Factors:")
                    if factors['urgency_indicators']:
                        print(f"    - Urgency: {factors['urgency_indicators']}")
                    if factors['financial_terms']:
                        print(f"    - Financial: {factors['financial_terms']}")
                    if factors['contact_requests']:
                        print(f"    - Contact Requests: {factors['contact_requests']}")
                    if factors['has_media']:
                        print(f"    - Has Media: Yes")