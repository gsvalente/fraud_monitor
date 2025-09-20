"""
Keyword Management System for Fraud Detection

This module provides a clean interface for managing fraud detection keywords
and their associated scores, following Clean Code principles.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import logging
from pathlib import Path

from colorama import Fore, Style


class FraudCategory(Enum):
    """Enumeration of fraud categories for better organization"""
    SCAM = "scam"
    INVESTMENT = "investment"
    PHISHING = "phishing"
    CRYPTOCURRENCY = "cryptocurrency"
    ROMANCE = "romance"
    TECH_SUPPORT = "tech_support"
    LOTTERY = "lottery"
    EMPLOYMENT = "employment"
    GENERAL = "general"


@dataclass
class FraudKeyword:
    """Data class representing a fraud detection keyword"""
    keyword: str
    category: FraudCategory
    score: float
    description: str = ""
    
    def __post_init__(self):
        """Validate keyword data after initialization"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Fraud score must be between 0.0 and 1.0, got {self.score}")
        if not self.keyword.strip():
            raise ValueError("Keyword cannot be empty")


class KeywordManager:
    """
    Manages fraud detection keywords with CRUD operations
    
    Follows Clean Code principles:
    - Single Responsibility: Only manages keywords
    - Open/Closed: Easy to extend with new categories
    - Dependency Inversion: Uses abstractions
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = Path(config_file) if config_file else Path("fraud_keywords.json")
        self._keywords: Dict[str, FraudKeyword] = {}
        self._load_default_keywords()
        
    def _load_default_keywords(self) -> None:
        """Load default fraud detection keywords"""
        default_keywords = [
            # High-risk scam keywords
            FraudKeyword("scam", FraudCategory.SCAM, 0.9, "Direct scam reference"),
            FraudKeyword("fraud", FraudCategory.SCAM, 0.9, "Direct fraud reference"),
            FraudKeyword("fake", FraudCategory.SCAM, 0.7, "Potentially fake content"),
            FraudKeyword("phishing", FraudCategory.PHISHING, 0.9, "Phishing attempt"),
            
            # Investment scams
            FraudKeyword("guaranteed profit", FraudCategory.INVESTMENT, 0.9, "Unrealistic profit claims"),
            FraudKeyword("investment opportunity", FraudCategory.INVESTMENT, 0.6, "Investment solicitation"),
            FraudKeyword("double your money", FraudCategory.INVESTMENT, 0.8, "Unrealistic returns"),
            FraudKeyword("risk-free investment", FraudCategory.INVESTMENT, 0.8, "False risk claims"),
            
            # Cryptocurrency scams
            FraudKeyword("crypto giveaway", FraudCategory.CRYPTOCURRENCY, 0.8, "Fake crypto giveaways"),
            FraudKeyword("send bitcoin", FraudCategory.CRYPTOCURRENCY, 0.7, "Bitcoin solicitation"),
            FraudKeyword("mining pool", FraudCategory.CRYPTOCURRENCY, 0.5, "Potential mining scam"),
            
            # Romance scams
            FraudKeyword("lonely", FraudCategory.ROMANCE, 0.4, "Romance scam indicator"),
            FraudKeyword("send money", FraudCategory.ROMANCE, 0.8, "Money solicitation"),
            FraudKeyword("emergency funds", FraudCategory.ROMANCE, 0.7, "Emergency money request"),
            
            # Tech support scams
            FraudKeyword("tech support", FraudCategory.TECH_SUPPORT, 0.6, "Fake tech support"),
            FraudKeyword("virus detected", FraudCategory.TECH_SUPPORT, 0.7, "Fake virus warning"),
            FraudKeyword("computer infected", FraudCategory.TECH_SUPPORT, 0.7, "Fake infection claim"),
            
            # Lottery/Prize scams
            FraudKeyword("congratulations winner", FraudCategory.LOTTERY, 0.8, "Fake lottery win"),
            FraudKeyword("claim your prize", FraudCategory.LOTTERY, 0.7, "Prize claim scam"),
            FraudKeyword("lottery winner", FraudCategory.LOTTERY, 0.8, "Fake lottery notification"),
            
            # Employment scams
            FraudKeyword("work from home", FraudCategory.EMPLOYMENT, 0.4, "Potential job scam"),
            FraudKeyword("easy money", FraudCategory.EMPLOYMENT, 0.6, "Unrealistic earning claims"),
            FraudKeyword("no experience required", FraudCategory.EMPLOYMENT, 0.3, "Suspicious job offer"),
        ]
        
        for keyword in default_keywords:
            self._keywords[keyword.keyword.lower()] = keyword
            
        self.logger.info(f"{Fore.GREEN}✅ Loaded {len(default_keywords)} default keywords")
    
    def add_keyword(self, keyword: str, category: FraudCategory, score: float, description: str = "") -> bool:
        """
        Add a new fraud keyword
        
        Args:
            keyword: The keyword to detect
            category: Category of fraud
            score: Fraud score (0.0 to 1.0)
            description: Optional description
            
        Returns:
            bool: True if added successfully, False if already exists
        """
        try:
            fraud_keyword = FraudKeyword(keyword.strip().lower(), category, score, description)
            
            if fraud_keyword.keyword in self._keywords:
                self.logger.warning(f"{Fore.YELLOW}⚠️  Keyword '{keyword}' already exists")
                return False
                
            self._keywords[fraud_keyword.keyword] = fraud_keyword
            self.logger.info(f"{Fore.GREEN}✅ Added keyword: '{keyword}' (score: {score})")
            return True
            
        except ValueError as e:
            self.logger.error(f"{Fore.RED}❌ Invalid keyword data: {e}")
            return False
    
    def remove_keyword(self, keyword: str) -> bool:
        """
        Remove a fraud keyword
        
        Args:
            keyword: The keyword to remove
            
        Returns:
            bool: True if removed successfully, False if not found
        """
        keyword_lower = keyword.strip().lower()
        
        if keyword_lower in self._keywords:
            del self._keywords[keyword_lower]
            self.logger.info(f"{Fore.GREEN}✅ Removed keyword: '{keyword}'")
            return True
        else:
            self.logger.warning(f"{Fore.YELLOW}⚠️  Keyword '{keyword}' not found")
            return False
    
    def update_keyword_score(self, keyword: str, new_score: float) -> bool:
        """
        Update the fraud score of an existing keyword
        
        Args:
            keyword: The keyword to update
            new_score: New fraud score (0.0 to 1.0)
            
        Returns:
            bool: True if updated successfully, False if not found or invalid score
        """
        if not 0.0 <= new_score <= 1.0:
            self.logger.error(f"{Fore.RED}❌ Invalid score: {new_score}. Must be between 0.0 and 1.0")
            return False
            
        keyword_lower = keyword.strip().lower()
        
        if keyword_lower in self._keywords:
            old_score = self._keywords[keyword_lower].score
            self._keywords[keyword_lower].score = new_score
            self.logger.info(f"{Fore.GREEN}✅ Updated '{keyword}' score: {old_score} → {new_score}")
            return True
        else:
            self.logger.warning(f"{Fore.YELLOW}⚠️  Keyword '{keyword}' not found")
            return False
    
    def get_keyword(self, keyword: str) -> Optional[FraudKeyword]:
        """Get a specific keyword"""
        return self._keywords.get(keyword.strip().lower())
    
    def get_all_keywords(self) -> List[FraudKeyword]:
        """Get all keywords as a list"""
        return list(self._keywords.values())
    
    def get_keywords_by_category(self, category: FraudCategory) -> List[FraudKeyword]:
        """Get all keywords in a specific category"""
        return [kw for kw in self._keywords.values() if kw.category == category]
    
    def get_high_risk_keywords(self, threshold: float = 0.7) -> List[FraudKeyword]:
        """Get keywords with fraud score above threshold"""
        return [kw for kw in self._keywords.values() if kw.score >= threshold]
    
    def search_keywords(self, search_term: str) -> List[FraudKeyword]:
        """Search keywords by partial match"""
        search_lower = search_term.lower()
        return [kw for kw in self._keywords.values() if search_lower in kw.keyword]
    
    def export_to_json(self, file_path: Optional[str] = None) -> bool:
        """Export keywords to JSON file"""
        try:
            export_path = Path(file_path) if file_path else self.config_file
            
            data = {
                "keywords": [
                    {
                        "keyword": kw.keyword,
                        "category": kw.category.value,
                        "score": kw.score,
                        "description": kw.description
                    }
                    for kw in self._keywords.values()
                ]
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"{Fore.GREEN}✅ Exported {len(self._keywords)} keywords to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}❌ Export failed: {e}")
            return False
    
    def import_from_json(self, file_path: str) -> bool:
        """Import keywords from JSON file"""
        try:
            import_path = Path(file_path)
            
            if not import_path.exists():
                self.logger.error(f"{Fore.RED}❌ File not found: {file_path}")
                return False
                
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            imported_count = 0
            for kw_data in data.get("keywords", []):
                try:
                    category = FraudCategory(kw_data["category"])
                    if self.add_keyword(
                        kw_data["keyword"],
                        category,
                        kw_data["score"],
                        kw_data.get("description", "")
                    ):
                        imported_count += 1
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"{Fore.YELLOW}⚠️  Skipped invalid keyword: {e}")
                    
            self.logger.info(f"{Fore.GREEN}✅ Imported {imported_count} keywords from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}❌ Import failed: {e}")
            return False
    
    def print_summary(self) -> None:
        """Print a summary of all keywords organized by category"""
        print(f"\n{Fore.CYAN}📊 Fraud Keywords Summary{Style.RESET_ALL}")
        print("=" * 50)
        
        for category in FraudCategory:
            keywords = self.get_keywords_by_category(category)
            if keywords:
                print(f"\n{Fore.YELLOW}{category.value.upper().replace('_', ' ')} ({len(keywords)} keywords):{Style.RESET_ALL}")
                for kw in sorted(keywords, key=lambda x: x.score, reverse=True):
                    score_color = Fore.RED if kw.score >= 0.8 else Fore.YELLOW if kw.score >= 0.6 else Fore.GREEN
                    print(f"  • {kw.keyword:<25} {score_color}[{kw.score:.1f}]{Style.RESET_ALL} {kw.description}")
        
        total_keywords = len(self._keywords)
        high_risk = len(self.get_high_risk_keywords())
        print(f"\n{Fore.BLUE}📈 Statistics:{Style.RESET_ALL}")
        print(f"  • Total keywords: {total_keywords}")
        print(f"  • High-risk (≥0.7): {high_risk}")
        print(f"  • Categories: {len([cat for cat in FraudCategory if self.get_keywords_by_category(cat)])}")