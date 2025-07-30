import re
import spacy
from typing import List, Dict, Any, Optional, Tuple
from app.models.models import Entity
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Entity extraction using multiple approaches"""
    
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self.entities = {}
        self.regex_entities = {}
        self.nlp = None
        self._load_spacy_model()
        
    def _load_spacy_model(self):
        """Load spaCy model for NER"""
        try:
            self.nlp = spacy.load(settings.SPACY_MODEL)
        except OSError:
            logger.warning(f"SpaCy model {settings.SPACY_MODEL} not found. Entity extraction will be limited.")
            self.nlp = None
    
    def load_entities(self, entities: List[Entity]):
        """Load entity definitions for the bot"""
        self.entities = {}
        self.regex_entities = {}
        
        for entity in entities:
            if not entity.is_active:
                continue
                
            if entity.entity_type == "regex" and entity.regex_pattern:
                self.regex_entities[entity.name] = {
                    'pattern': re.compile(entity.regex_pattern, re.IGNORECASE),
                    'description': entity.description
                }
            elif entity.entity_type in ["custom", "system"]:
                self.entities[entity.name] = {
                    'values': entity.values or [],
                    'type': entity.entity_type,
                    'description': entity.description
                }
                
        logger.info(f"Loaded {len(self.entities)} custom entities and {len(self.regex_entities)} regex entities for bot {self.bot_id}")
    
    def extract(self, text: str, intent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract entities from text using multiple approaches"""
        entities_found = []
        text_lower = text.lower()
        
        # 1. Extract regex entities
        entities_found.extend(self._extract_regex_entities(text))
        
        # 2. Extract custom entities
        entities_found.extend(self._extract_custom_entities(text_lower))
        
        # 3. Extract system entities using spaCy
        if self.nlp:
            entities_found.extend(self._extract_system_entities(text))
            
        # 4. Extract numbers, dates, and other common patterns
        entities_found.extend(self._extract_common_patterns(text))
        
        # Remove duplicates and overlapping entities
        entities_found = self._resolve_conflicts(entities_found, text)
        
        return entities_found
    
    def _extract_regex_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using regex patterns"""
        entities = []
        
        for entity_name, entity_data in self.regex_entities.items():
            pattern = entity_data['pattern']
            matches = pattern.finditer(text)
            
            for match in matches:
                entities.append({
                    'entity': entity_name,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 1.0,
                    'method': 'regex'
                })
                
        return entities
    
    def _extract_custom_entities(self, text_lower: str) -> List[Dict[str, Any]]:
        """Extract custom entities using value matching"""
        entities = []
        
        for entity_name, entity_data in self.entities.items():
            values = entity_data['values']
            
            for value_info in values:
                if isinstance(value_info, str):
                    value = value_info
                    synonyms = []
                elif isinstance(value_info, dict):
                    value = value_info.get('value', '')
                    synonyms = value_info.get('synonyms', [])
                else:
                    continue
                    
                # Check main value and synonyms
                search_terms = [value.lower()] + [syn.lower() for syn in synonyms]
                
                for term in search_terms:
                    if term in text_lower:
                        start_idx = text_lower.find(term)
                        if start_idx != -1:
                            entities.append({
                                'entity': entity_name,
                                'value': value,  # Always return the canonical value
                                'raw_value': term,
                                'start': start_idx,
                                'end': start_idx + len(term),
                                'confidence': 0.9,
                                'method': 'custom'
                            })
                            
        return entities
    
    def _extract_system_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract system entities using spaCy NER"""
        entities = []
        
        if not self.nlp:
            return entities
            
        doc = self.nlp(text)
        
        for ent in doc.ents:
            entities.append({
                'entity': f"sys.{ent.label_.lower()}",
                'value': ent.text,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 0.8,
                'method': 'spacy',
                'label': ent.label_
            })
            
        return entities
    
    def _extract_common_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract common patterns like numbers, emails, phone numbers"""
        entities = []
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({
                'entity': 'sys.email',
                'value': match.group(),
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.95,
                'method': 'pattern'
            })
        
        # Phone number pattern (basic)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        for match in re.finditer(phone_pattern, text):
            entities.append({
                'entity': 'sys.phone',
                'value': match.group(),
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.9,
                'method': 'pattern'
            })
        
        # Number pattern
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        for match in re.finditer(number_pattern, text):
            try:
                value = float(match.group()) if '.' in match.group() else int(match.group())
                entities.append({
                    'entity': 'sys.number',
                    'value': value,
                    'raw_value': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.85,
                    'method': 'pattern'
                })
            except ValueError:
                continue
        
        # URL pattern
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        for match in re.finditer(url_pattern, text):
            entities.append({
                'entity': 'sys.url',
                'value': match.group(),
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.95,
                'method': 'pattern'
            })
            
        return entities
    
    def _resolve_conflicts(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Resolve overlapping entities by keeping the most confident ones"""
        if not entities:
            return entities
            
        # Sort by start position
        entities.sort(key=lambda x: x['start'])
        
        resolved = []
        for entity in entities:
            # Check for overlap with existing entities
            overlaps = False
            for existing in resolved:
                if (entity['start'] < existing['end'] and entity['end'] > existing['start']):
                    # There's an overlap - keep the one with higher confidence
                    if entity['confidence'] > existing['confidence']:
                        resolved.remove(existing)
                        resolved.append(entity)
                    overlaps = True
                    break
                    
            if not overlaps:
                resolved.append(entity)
                
        return sorted(resolved, key=lambda x: x['start'])
    
    def annotate_text(self, text: str, entities: List[Dict[str, Any]]) -> str:
        """Annotate text with entity markup for training data"""
        if not entities:
            return text
            
        # Sort entities by start position in reverse order
        entities_sorted = sorted(entities, key=lambda x: x['start'], reverse=True)
        
        annotated = text
        for entity in entities_sorted:
            start = entity['start']
            end = entity['end']
            entity_name = entity['entity']
            
            # Insert markup
            annotated = (annotated[:start] + 
                        f"[{annotated[start:end]}]({entity_name})" + 
                        annotated[end:])
                        
        return annotated
    
    def validate_entity_value(self, entity_name: str, value: str) -> bool:
        """Validate if a value is valid for a given entity"""
        if entity_name in self.entities:
            entity_data = self.entities[entity_name]
            values = entity_data['values']
            
            for value_info in values:
                if isinstance(value_info, str):
                    if value.lower() == value_info.lower():
                        return True
                elif isinstance(value_info, dict):
                    main_value = value_info.get('value', '')
                    synonyms = value_info.get('synonyms', [])
                    
                    if (value.lower() == main_value.lower() or 
                        value.lower() in [syn.lower() for syn in synonyms]):
                        return True
                        
        elif entity_name in self.regex_entities:
            pattern = self.regex_entities[entity_name]['pattern']
            return bool(pattern.match(value))
            
        return False