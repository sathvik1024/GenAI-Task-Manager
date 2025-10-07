"""
Translation Service for multilingual task parsing.
Handles language detection, translation, and NLP processing.
"""

import os
import re
from typing import Dict, Optional, Tuple
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
import nltk
from datetime import datetime, timedelta

# Set seed for consistent language detection
DetectorFactory.seed = 0

class TranslationService:
    def __init__(self):
        self._download_nltk_data()
        
        self.language_names = {
            'en': 'English',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'te': 'Telugu',
            'ta': 'Tamil',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'bn': 'Bengali',
            'gu': 'Gujarati',
            'mr': 'Marathi',
            'pa': 'Punjabi'
        }
        
        self.priority_keywords = {
            'urgent': {
                'en': ['urgent', 'asap', 'immediately', 'critical', 'emergency'],
                'es': ['urgente', 'inmediatamente', 'crítico', 'emergencia'],
                'fr': ['urgent', 'immédiatement', 'critique', 'urgence'],
                'de': ['dringend', 'sofort', 'kritisch', 'notfall'],
                'hi': ['तुरंत', 'जरूरी', 'आपातकाल'],
                'te': ['తక్షణం', 'అత్యవసరం'],
                'ta': ['உடனடி', 'அவசரம்'],
                'zh': ['紧急', '立即', '马上'],
                'ja': ['緊急', 'すぐに', '至急'],
                'ar': ['عاجل', 'فوري', 'طارئ']
            },
            'high': {
                'en': ['high priority', 'important', 'high'],
                'es': ['alta prioridad', 'importante', 'alto'],
                'fr': ['haute priorité', 'important', 'élevé'],
                'de': ['hohe priorität', 'wichtig', 'hoch'],
                'hi': ['उच्च प्राथमिकता', 'महत्वपूर्ण'],
                'te': ['అధిక ప్రాధాన్యత', 'ముఖ్యమైన'],
                'ta': ['உயர் முன்னுரிமை', 'முக்கியமான'],
                'zh': ['高优先级', '重要'],
                'ja': ['高優先度', '重要'],
                'ar': ['أولوية عالية', 'مهم']
            },
            'low': {
                'en': ['low priority', 'when possible', 'eventually', 'low'],
                'es': ['baja prioridad', 'cuando sea posible', 'bajo'],
                'fr': ['basse priorité', 'quand possible', 'bas'],
                'de': ['niedrige priorität', 'wenn möglich', 'niedrig'],
                'hi': ['कम प्राथमिकता', 'जब संभव हो'],
                'te': ['తక్కువ ప్రాధాన్యత'],
                'ta': ['குறைந்த முன்னுரிமை'],
                'zh': ['低优先级'],
                'ja': ['低優先度'],
                'ar': ['أولوية منخفضة']
            }
        }
        
        # Category
        self.category_keywords = {
            'work': {
                'en': ['work', 'office', 'job', 'meeting', 'report', 'project', 'business'],
                'es': ['trabajo', 'oficina', 'reunión', 'informe', 'proyecto', 'negocio'],
                'fr': ['travail', 'bureau', 'réunion', 'rapport', 'projet', 'affaires'],
                'de': ['arbeit', 'büro', 'besprechung', 'bericht', 'projekt', 'geschäft'],
                'hi': ['काम', 'कार्यालय', 'नौकरी', 'बैठक', 'रिपोर्ट'],
                'te': ['పని', 'కార్యాలయం', 'ఉద్యోగం', 'సమావేశం'],
                'ta': ['வேலை', 'அலுவலகம்', 'கூட்டம்'],
                'zh': ['工作', '办公室', '会议', '报告', '项目'],
                'ja': ['仕事', 'オフィス', '会議', 'レポート'],
                'ar': ['عمل', 'مكتب', 'اجتماع', 'تقرير']
            },
            'health': {
                'en': ['doctor', 'appointment', 'medical', 'health', 'hospital', 'clinic'],
                'es': ['doctor', 'cita', 'médico', 'salud', 'hospital'],
                'fr': ['docteur', 'rendez-vous', 'médical', 'santé', 'hôpital'],
                'de': ['arzt', 'termin', 'medizinisch', 'gesundheit', 'krankenhaus'],
                'hi': ['डॉक्टर', 'अपॉइंटमेंट', 'स्वास्थ्य', 'अस्पताल'],
                'te': ['డాక్టర్', 'అపాయింట్మెంట్', 'ఆరోగ్యం'],
                'ta': ['மருத்துவர்', 'சுகாதாரம்'],
                'zh': ['医生', '预约', '医疗', '健康', '医院'],
                'ja': ['医者', '予約', '医療', '健康', '病院'],
                'ar': ['طبيب', 'موعد', 'طبي', 'صحة', 'مستشفى']
            },
            'education': {
                'en': ['study', 'homework', 'assignment', 'exam', 'school', 'university', 'college'],
                'es': ['estudiar', 'tarea', 'examen', 'escuela', 'universidad'],
                'fr': ['étudier', 'devoirs', 'examen', 'école', 'université'],
                'de': ['studieren', 'hausaufgaben', 'prüfung', 'schule', 'universität'],
                'hi': ['पढ़ाई', 'होमवर्क', 'परीक्षा', 'स्कूल', 'विश्वविद्यालय'],
                'te': ['చదువు', 'హోంవర్క్', 'పరీక్ష', 'పాఠశాల'],
                'ta': ['படிப்பு', 'பாடம்', 'தேர்வு', 'பள்ளி'],
                'zh': ['学习', '作业', '考试', '学校', '大学'],
                'ja': ['勉強', '宿題', '試験', '学校', '大学'],
                'ar': ['دراسة', 'واجب', 'امتحان', 'مدرسة', 'جامعة']
            },
            'personal': {
                'en': ['personal', 'home', 'family', 'friend', 'birthday', 'anniversary'],
                'es': ['personal', 'casa', 'familia', 'amigo', 'cumpleaños'],
                'fr': ['personnel', 'maison', 'famille', 'ami', 'anniversaire'],
                'de': ['persönlich', 'zuhause', 'familie', 'freund', 'geburtstag'],
                'hi': ['व्यक्तिगत', 'घर', 'परिवार', 'दोस्त'],
                'te': ['వ్యక్తిగత', 'ఇల్లు', 'కుటుంబం', 'స్నేహితుడు'],
                'ta': ['தனிப்பட்ட', 'வீடு', 'குடும்பம்', 'நண்பர்'],
                'zh': ['个人', '家', '家庭', '朋友', '生日'],
                'ja': ['個人', '家', '家族', '友達', '誕生日'],
                'ar': ['شخصي', 'منزل', 'عائلة', 'صديق']
            },
            'shopping': {
                'en': ['buy', 'purchase', 'shop', 'store', 'groceries', 'market'],
                'es': ['comprar', 'tienda', 'mercado', 'comestibles'],
                'fr': ['acheter', 'magasin', 'marché', 'épicerie'],
                'de': ['kaufen', 'geschäft', 'markt', 'lebensmittel'],
                'hi': ['खरीदना', 'दुकान', 'बाजार', 'किराना'],
                'te': ['కొనుగోలు', 'దుకాణం', 'మార్కెట్'],
                'ta': ['வாங்க', 'கடை', 'சந்தை'],
                'zh': ['买', '购买', '商店', '市场', '杂货'],
                'ja': ['買う', '購入', '店', '市場', '食料品'],
                'ar': ['شراء', 'متجر', 'سوق', 'بقالة']
            }
        }

    def _download_nltk_data(self):
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect the language of the input text.
        Returns (language_code, confidence)
        """
        try:
            detected_lang = detect(text)
            confidence = 0.9  # langdetect doesn't provide confidence, so we estimate
            
            print(f" Detected language: {detected_lang} ({self.language_names.get(detected_lang, 'Unknown')})")
            return detected_lang, confidence
        except Exception as e:
            print(f" Language detection failed: {e}")
            return 'en', 0.5  # Default to English

    def translate_to_english(self, text: str, source_lang: str = None) -> Dict:
        """
        Translate text to English if it's not already in English.
        Returns dict with original_text, translated_text, source_language
        """
        try:
            # Detect language if not provided
            if not source_lang:
                source_lang, confidence = self.detect_language(text)
            
            # If already English, no translation needed
            if source_lang == 'en':
                return {
                    'original_text': text,
                    'translated_text': text,
                    'source_language': 'en',
                    'translation_needed': False
                }
            
            # Translate to English using deep-translator
            print(f" Translating from {self.language_names.get(source_lang, source_lang)} to English...")
            translated_text = GoogleTranslator(source=source_lang, target='en').translate(text)
            print(f" Translation: '{text}' → '{translated_text}'")
            
            return {
                'original_text': text,
                'translated_text': translated_text,
                'source_language': source_lang,
                'translation_needed': True
            }
            
        except Exception as e:
            print(f" Translation failed: {e}")
            # Return original text if translation fails
            return {
                'original_text': text,
                'translated_text': text,
                'source_language': source_lang or 'unknown',
                'translation_needed': False,
                'error': str(e)
            }

    def extract_multilingual_features(self, original_text: str, source_lang: str) -> Dict:
        """
        Extract priority and category from original text using multilingual keywords.
        This works even if translation fails.
        """
        text_lower = original_text.lower()
        
        # Extract priority
        priority = 'medium'  # default
        for priority_level, lang_keywords in self.priority_keywords.items():
            if source_lang in lang_keywords:
                keywords = lang_keywords[source_lang]
                if any(keyword in text_lower for keyword in keywords):
                    priority = priority_level
                    break
        
        # Extract category
        category = 'general'  # default
        for cat, lang_keywords in self.category_keywords.items():
            if source_lang in lang_keywords:
                keywords = lang_keywords[source_lang]
                if any(keyword in text_lower for keyword in keywords):
                    category = cat
                    break
        
        return {
            'priority': priority,
            'category': category
        }

# Global instance
translation_service = TranslationService()