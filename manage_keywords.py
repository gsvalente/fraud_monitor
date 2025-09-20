#!/usr/bin/env python3
"""
Fraud Keywords Management Tool

Easy-to-use command-line interface for managing fraud detection keywords.
Follows Clean Code principles with clear, intuitive commands.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

import argparse
import json
from typing import List, Dict, Any
from colorama import Fore, Style, init

# Import our Clean Code fraud detection modules
from src.fraud_detection.keyword_manager import KeywordManager, FraudCategory
from src.fraud_detection.detector import FraudDetector
from src.database.simplified_database import SimplifiedDatabaseManager

# Initialize colorama for Windows
init()


class KeywordCLI:
    """Command-line interface for keyword management"""
    
    def __init__(self):
        self.db = SimplifiedDatabaseManager()
        self.keyword_manager = KeywordManager()
        self.detector = FraudDetector(self.keyword_manager)
    
    def add_keyword(self, keyword: str, category: str, score: float, description: str = ""):
        """Add a new keyword"""
        try:
            fraud_category = FraudCategory(category.lower())
            success = self.keyword_manager.add_keyword(keyword, fraud_category, score, description)
            
            if success:
                print(f"{Fore.GREEN}✅ Successfully added keyword: '{keyword}'{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}❌ Failed to add keyword (may already exist){Style.RESET_ALL}")
                return False
                
        except ValueError as e:
            print(f"{Fore.RED}❌ Invalid category '{category}'. Valid categories:{Style.RESET_ALL}")
            self._print_categories()
            return False
    
    def remove_keyword(self, keyword: str):
        """Remove a keyword"""
        success = self.keyword_manager.remove_keyword(keyword)
        if success:
            print(f"{Fore.GREEN}✅ Successfully removed keyword: '{keyword}'{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Keyword '{keyword}' not found{Style.RESET_ALL}")
        return success
    
    def update_score(self, keyword: str, new_score: float):
        """Update keyword fraud score"""
        success = self.keyword_manager.update_keyword_score(keyword, new_score)
        if success:
            print(f"{Fore.GREEN}✅ Successfully updated score for '{keyword}' to {new_score}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Failed to update keyword '{keyword}'{Style.RESET_ALL}")
        return success
    
    def list_keywords(self, category: str = None, min_score: float = None):
        """List keywords with optional filtering"""
        if category:
            try:
                fraud_category = FraudCategory(category.lower())
                keywords = self.keyword_manager.get_keywords_by_category(fraud_category)
                print(f"\n{Fore.CYAN}Keywords in category '{category.upper()}':{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}❌ Invalid category '{category}'{Style.RESET_ALL}")
                self._print_categories()
                return
        else:
            keywords = self.keyword_manager.get_all_keywords()
            print(f"\n{Fore.CYAN}All Keywords:{Style.RESET_ALL}")
        
        # Apply score filter
        if min_score is not None:
            keywords = [kw for kw in keywords if kw.score >= min_score]
            print(f"{Fore.YELLOW}(Filtered by minimum score: {min_score}){Style.RESET_ALL}")
        
        if not keywords:
            print(f"{Fore.YELLOW}No keywords found matching criteria{Style.RESET_ALL}")
            return
        
        # Sort by score (descending)
        keywords.sort(key=lambda x: x.score, reverse=True)
        
        print(f"\n{'Keyword':<25} {'Category':<15} {'Score':<8} {'Description'}")
        print("-" * 70)
        
        for kw in keywords:
            score_color = Fore.RED if kw.score >= 0.8 else Fore.YELLOW if kw.score >= 0.6 else Fore.GREEN
            print(f"{kw.keyword:<25} {kw.category.value:<15} {score_color}{kw.score:<8.2f}{Style.RESET_ALL} {kw.description}")
    
    def search_keywords(self, search_term: str):
        """Search keywords by partial match"""
        keywords = self.keyword_manager.search_keywords(search_term)
        
        if not keywords:
            print(f"{Fore.YELLOW}No keywords found containing '{search_term}'{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}Keywords containing '{search_term}':{Style.RESET_ALL}")
        print(f"\n{'Keyword':<25} {'Category':<15} {'Score':<8} {'Description'}")
        print("-" * 70)
        
        for kw in sorted(keywords, key=lambda x: x.score, reverse=True):
            score_color = Fore.RED if kw.score >= 0.8 else Fore.YELLOW if kw.score >= 0.6 else Fore.GREEN
            print(f"{kw.keyword:<25} {kw.category.value:<15} {score_color}{kw.score:<8.2f}{Style.RESET_ALL} {kw.description}")
    
    def test_detection(self, text: str):
        """Test fraud detection on sample text"""
        print(f"\n{Fore.CYAN}Testing fraud detection on text:{Style.RESET_ALL}")
        print(f"'{text}'\n")
        
        result = self.detector.detect_fraud(text)
        self.detector.print_detection_result(result)
    
    def show_summary(self):
        """Show keyword summary"""
        self.keyword_manager.print_summary()
    
    def export_keywords(self, file_path: str):
        """Export keywords to JSON file"""
        success = self.keyword_manager.export_to_json(file_path)
        if success:
            print(f"{Fore.GREEN}✅ Keywords exported to '{file_path}'{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Failed to export keywords{Style.RESET_ALL}")
    
    def import_keywords(self, file_path: str):
        """Import keywords from JSON file"""
        success = self.keyword_manager.import_from_json(file_path)
        if success:
            print(f"{Fore.GREEN}✅ Keywords imported from '{file_path}'{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Failed to import keywords{Style.RESET_ALL}")
    
    def _print_categories(self):
        """Print available categories"""
        print(f"\n{Fore.BLUE}Available categories:{Style.RESET_ALL}")
        for category in FraudCategory:
            print(f"  • {category.value}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Fraud Keywords Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_keywords.py add "bitcoin scam" scam 0.9 "Bitcoin-related scam"
  python manage_keywords.py remove "old keyword"
  python manage_keywords.py update "investment" 0.8
  python manage_keywords.py list --category scam
  python manage_keywords.py list --min-score 0.7
  python manage_keywords.py search "crypto"
  python manage_keywords.py test "Send me bitcoin for guaranteed profit"
  python manage_keywords.py summary
  python manage_keywords.py export keywords_backup.json
  python manage_keywords.py import keywords_backup.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add keyword
    add_parser = subparsers.add_parser('add', help='Add a new keyword')
    add_parser.add_argument('keyword', help='Keyword to add')
    add_parser.add_argument('category', help='Fraud category')
    add_parser.add_argument('score', type=float, help='Fraud score (0.0-1.0)')
    add_parser.add_argument('description', nargs='?', default='', help='Optional description')
    
    # Remove keyword
    remove_parser = subparsers.add_parser('remove', help='Remove a keyword')
    remove_parser.add_argument('keyword', help='Keyword to remove')
    
    # Update score
    update_parser = subparsers.add_parser('update', help='Update keyword score')
    update_parser.add_argument('keyword', help='Keyword to update')
    update_parser.add_argument('score', type=float, help='New fraud score (0.0-1.0)')
    
    # List keywords
    list_parser = subparsers.add_parser('list', help='List keywords')
    list_parser.add_argument('--category', help='Filter by category')
    list_parser.add_argument('--min-score', type=float, help='Minimum fraud score')
    
    # Search keywords
    search_parser = subparsers.add_parser('search', help='Search keywords')
    search_parser.add_argument('term', help='Search term')
    
    # Test detection
    test_parser = subparsers.add_parser('test', help='Test fraud detection')
    test_parser.add_argument('text', help='Text to analyze')
    
    # Show summary
    subparsers.add_parser('summary', help='Show keywords summary')
    
    # Export keywords
    export_parser = subparsers.add_parser('export', help='Export keywords to JSON')
    export_parser.add_argument('file', help='Output file path')
    
    # Import keywords
    import_parser = subparsers.add_parser('import', help='Import keywords from JSON')
    import_parser.add_argument('file', help='Input file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = KeywordCLI()
    
    try:
        if args.command == 'add':
            cli.add_keyword(args.keyword, args.category, args.score, args.description)
        elif args.command == 'remove':
            cli.remove_keyword(args.keyword)
        elif args.command == 'update':
            cli.update_score(args.keyword, args.score)
        elif args.command == 'list':
            cli.list_keywords(args.category, args.min_score)
        elif args.command == 'search':
            cli.search_keywords(args.term)
        elif args.command == 'test':
            cli.test_detection(args.text)
        elif args.command == 'summary':
            cli.show_summary()
        elif args.command == 'export':
            cli.export_keywords(args.file)
        elif args.command == 'import':
            cli.import_keywords(args.file)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()