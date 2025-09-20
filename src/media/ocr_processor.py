"""
OCR Processor - Phase 3 OCR Implementation
Handles text extraction from images using Tesseract OCR
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from colorama import Fore, Style

logger = logging.getLogger(__name__)

class OCRProcessor:
    """Handles OCR text extraction from images"""
    
    def __init__(self, tesseract_path: str = None):
        """
        Initialize the OCR processor
        
        Args:
            tesseract_path: Path to Tesseract executable (auto-detected if None)
        """
        self.tesseract_path = tesseract_path
        self.setup_tesseract()
        
        # OCR configuration - using PSM 3 for better text detection, removed char whitelist to allow all characters
        self.ocr_config = r'--oem 3 --psm 3'
        
        # Statistics
        self.processed_count = 0
        self.successful_extractions = 0
        self.failed_extractions = 0
        
        logger.info("OCR Processor initialized")
    
    def setup_tesseract(self):
        """Setup Tesseract OCR path"""
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        else:
            # Try common Windows paths
            common_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
                'tesseract'  # System PATH
            ]
            
            for path in common_paths:
                try:
                    if os.path.exists(path) or path == 'tesseract':
                        pytesseract.pytesseract.tesseract_cmd = path
                        # Test if it works
                        pytesseract.get_tesseract_version()
                        logger.info(f"Tesseract found at: {path}")
                        return
                except:
                    continue
            
            logger.warning("Tesseract not found in common paths. Please install Tesseract OCR or set TESSERACT_PATH in .env")
    
    def preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Preprocess image for better OCR results
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array or None if failed
        """
        try:
            # Read image with OpenCV
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not read image: {image_path}")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply threshold to get binary image
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            return None
    
    def extract_text(self, image_path: str, preprocess: bool = False) -> Dict[str, Any]:
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to the image file
            preprocess: Whether to preprocess the image
            
        Returns:
            Dictionary with extraction results
        """
        result = {
            'success': False,
            'text': '',
            'confidence': 0.0,
            'word_count': 0,
            'processing_time': 0.0,
            'error': None
        }
        
        try:
            import time
            start_time = time.time()
            
            self.processed_count += 1
            logger.info(f"{Fore.YELLOW}🔍 Processing image: {Path(image_path).name}")
            
            if preprocess:
                # Use preprocessed image
                processed_image = self.preprocess_image(image_path)
                if processed_image is None:
                    # If preprocessing fails, fall back to original image
                    logger.warning("Preprocessing failed, using original image")
                    pil_image = Image.open(image_path)
                else:
                    # Convert numpy array back to PIL Image for pytesseract
                    pil_image = Image.fromarray(processed_image)
            else:
                # Use original image
                pil_image = Image.open(image_path)
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(pil_image, config=self.ocr_config, output_type=pytesseract.Output.DICT)
            
            # Filter out low-confidence words
            words = []
            confidences = []
            
            for i in range(len(data['text'])):
                word = data['text'][i].strip()
                confidence = int(data['conf'][i])
                
                if word and confidence > 0:  # Accept all words with positive confidence to capture low-confidence fraud keywords
                    words.append(word)
                    confidences.append(confidence)
            
            # Combine results
            extracted_text = ' '.join(words)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            result.update({
                'success': True,
                'text': extracted_text,
                'confidence': round(avg_confidence, 2),
                'word_count': len(words),
                'processing_time': round(time.time() - start_time, 2)
            })
            
            if extracted_text.strip():
                self.successful_extractions += 1
                logger.info(f"{Fore.GREEN}✅ OCR Success: {len(words)} words, confidence: {avg_confidence:.1f}%")
                logger.debug(f"Extracted text: {extracted_text[:100]}...")
            else:
                self.failed_extractions += 1
                logger.warning(f"{Fore.YELLOW}⚠️  No text extracted from image")
            
        except Exception as e:
            self.failed_extractions += 1
            result['error'] = str(e)
            logger.error(f"{Fore.RED}❌ OCR Error: {e}")
        
        return result
    
    def batch_process(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple images in batch
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of extraction results
        """
        results = []
        logger.info(f"{Fore.CYAN}📦 Starting batch OCR processing: {len(image_paths)} images")
        
        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"{Fore.CYAN}Processing {i}/{len(image_paths)}: {Path(image_path).name}")
            result = self.extract_text(image_path)
            result['image_path'] = image_path
            results.append(result)
        
        successful = sum(1 for r in results if r['success'] and r['text'].strip())
        logger.info(f"{Fore.GREEN}📊 Batch processing complete: {successful}/{len(image_paths)} successful")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        success_rate = (self.successful_extractions / self.processed_count * 100) if self.processed_count > 0 else 0
        
        return {
            'total_processed': self.processed_count,
            'successful_extractions': self.successful_extractions,
            'failed_extractions': self.failed_extractions,
            'success_rate': round(success_rate, 2),
            'tesseract_version': self.get_tesseract_version()
        }
    
    def get_tesseract_version(self) -> str:
        """Get Tesseract version"""
        try:
            return pytesseract.get_tesseract_version()
        except:
            return "Unknown"
    
    def is_text_suspicious(self, text: str, fraud_keywords: List[str]) -> Dict[str, Any]:
        """
        Quick check if extracted text contains suspicious content
        
        Args:
            text: Extracted text
            fraud_keywords: List of fraud keywords to check
            
        Returns:
            Dictionary with suspicion analysis
        """
        if not text.strip():
            return {'is_suspicious': False, 'matched_keywords': [], 'confidence': 0.0}
        
        text_lower = text.lower()
        matched_keywords = []
        
        for keyword in fraud_keywords:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)
        
        is_suspicious = len(matched_keywords) > 0
        confidence = min(len(matched_keywords) * 0.3, 1.0)  # Simple confidence calculation
        
        return {
            'is_suspicious': is_suspicious,
            'matched_keywords': matched_keywords,
            'confidence': confidence,
            'text_length': len(text),
            'word_count': len(text.split())
        }