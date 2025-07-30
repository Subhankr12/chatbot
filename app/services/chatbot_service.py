import time
import uuid
import random
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from app.models.models import (
    Bot, Intent, Entity, Conversation, Message, Response, 
    ConversationStatus, BotStatus
)
from app.nlp.intent_classifier import IntentClassifier
from app.nlp.entity_extractor import EntityExtractor
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class ChatbotResponse:
    """Structured chatbot response"""
    
    def __init__(
        self,
        text: str,
        intent: Optional[str] = None,
        confidence: float = 0.0,
        entities: List[Dict] = None,
        context: Dict = None,
        response_time_ms: int = 0,
        session_id: str = None,
        suggestions: List[str] = None,
        metadata: Dict = None
    ):
        self.text = text
        self.intent = intent
        self.confidence = confidence
        self.entities = entities or []
        self.context = context or {}
        self.response_time_ms = response_time_ms
        self.session_id = session_id
        self.suggestions = suggestions or []
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'intent': self.intent,
            'confidence': self.confidence,
            'entities': self.entities,
            'context': self.context,
            'response_time_ms': self.response_time_ms,
            'session_id': self.session_id,
            'suggestions': self.suggestions,
            'metadata': self.metadata
        }


class ConversationContext:
    """Manages conversation context and variables"""
    
    def __init__(self, context_data: Dict = None):
        self.data = context_data or {}
        self.variables = self.data.get('variables', {})
        self.history = self.data.get('history', [])
        self.current_flow = self.data.get('current_flow', None)
        
    def set_variable(self, key: str, value: Any):
        """Set a context variable"""
        self.variables[key] = value
        self.data['variables'] = self.variables
        
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable"""
        return self.variables.get(key, default)
        
    def add_to_history(self, item: Dict):
        """Add item to conversation history"""
        self.history.append(item)
        # Keep only last 10 items to prevent context from growing too large
        self.history = self.history[-10:]
        self.data['history'] = self.history
        
    def clear(self):
        """Clear conversation context"""
        self.data = {'variables': {}, 'history': [], 'current_flow': None}
        self.variables = {}
        self.history = []
        self.current_flow = None
        
    def to_dict(self) -> Dict:
        return self.data


class ChatbotService:
    """Main chatbot service orchestrating all components"""
    
    def __init__(self, bot_id: int, db: Session):
        self.bot_id = bot_id
        self.db = db
        self.bot = None
        self.intent_classifier = None
        self.entity_extractor = None
        self._load_bot()
        
    def _load_bot(self):
        """Load bot configuration and initialize components"""
        self.bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
        
        if not self.bot:
            raise ValueError(f"Bot with ID {self.bot_id} not found")
            
        if self.bot.status != BotStatus.ACTIVE:
            raise ValueError(f"Bot {self.bot_id} is not active")
            
        # Initialize NLP components
        self.intent_classifier = IntentClassifier(self.bot_id)
        self.entity_extractor = EntityExtractor(self.bot_id)
        
        # Load trained models if available
        if not self.intent_classifier.load_model():
            logger.warning(f"No trained model found for bot {self.bot_id}. Training may be required.")
            
        # Load entities
        entities = self.db.query(Entity).filter(
            Entity.bot_id == self.bot_id,
            Entity.is_active == True
        ).all()
        self.entity_extractor.load_entities(entities)
        
        logger.info(f"Chatbot service initialized for bot {self.bot_id}")
        
    def process_message(
        self,
        message: str,
        session_id: str,
        user_id: str = None,
        context_override: Dict = None
    ) -> ChatbotResponse:
        """Process a user message and generate response"""
        start_time = time.time()
        
        try:
            # Get or create conversation
            conversation = self._get_or_create_conversation(session_id, user_id)
            
            # Load conversation context
            context = ConversationContext(context_override or conversation.context)
            
            # Extract entities
            entities = self.entity_extractor.extract(message)
            
            # Classify intent
            intent_name, confidence = self.intent_classifier.predict(
                message, 
                threshold=self.bot.confidence_threshold
            )
            
            # Generate response
            response_text = self._generate_response(
                intent_name, entities, context, message
            )
            
            # Update context with extracted information
            if entities:
                for entity in entities:
                    context.set_variable(entity['entity'], entity['value'])
                    
            # Add to conversation history
            context.add_to_history({
                'user_message': message,
                'intent': intent_name,
                'entities': entities,
                'timestamp': time.time()
            })
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Save message to database
            self._save_message(
                conversation, message, response_text, intent_name, 
                confidence, entities, response_time_ms
            )
            
            # Update conversation context
            conversation.context = context.to_dict()
            self.db.commit()
            
            # Generate suggestions for unclear intents
            suggestions = []
            if not intent_name or confidence < 0.8:
                suggestions = self._get_intent_suggestions(message)
                
            return ChatbotResponse(
                text=response_text,
                intent=intent_name,
                confidence=confidence,
                entities=entities,
                context=context.to_dict(),
                response_time_ms=response_time_ms,
                session_id=session_id,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error processing message for bot {self.bot_id}: {e}")
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return ChatbotResponse(
                text="I'm sorry, I encountered an error processing your request. Please try again.",
                response_time_ms=response_time_ms,
                session_id=session_id
            )
    
    def _get_or_create_conversation(self, session_id: str, user_id: str = None) -> Conversation:
        """Get existing conversation or create new one"""
        conversation = self.db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.bot_id == self.bot_id,
            Conversation.status == ConversationStatus.ACTIVE
        ).first()
        
        if not conversation:
            conversation = Conversation(
                session_id=session_id,
                bot_id=self.bot_id,
                user_id=user_id,
                context={}
            )
            self.db.add(conversation)
            self.db.flush()  # Get the ID
            
        return conversation
    
    def _generate_response(
        self, 
        intent_name: str, 
        entities: List[Dict], 
        context: ConversationContext,
        original_message: str
    ) -> str:
        """Generate response based on intent and context"""
        
        if not intent_name:
            return self.bot.default_response
            
        # Get intent and its responses
        intent = self.db.query(Intent).filter(
            Intent.name == intent_name,
            Intent.bot_id == self.bot_id,
            Intent.is_active == True
        ).first()
        
        if not intent or not intent.responses:
            return self.bot.default_response
            
        # Select response (random for now, could be more sophisticated)
        responses = [r for r in intent.responses if r.response_type == 'text']
        if not responses:
            return self.bot.default_response
            
        selected_response = random.choice(responses)
        response_text = selected_response.text
        
        # Process response template with entities and context
        response_text = self._process_response_template(
            response_text, entities, context
        )
        
        return response_text
    
    def _process_response_template(
        self, 
        template: str, 
        entities: List[Dict], 
        context: ConversationContext
    ) -> str:
        """Process response template with entity and context substitutions"""
        
        # Create entity lookup
        entity_values = {}
        for entity in entities:
            entity_values[entity['entity']] = entity['value']
            
        # Replace entity placeholders
        for entity_name, value in entity_values.items():
            template = template.replace(f"{{{entity_name}}}", str(value))
            template = template.replace(f"{{@{entity_name}}}", str(value))
            
        # Replace context variable placeholders
        for var_name, value in context.variables.items():
            template = template.replace(f"{{{var_name}}}", str(value))
            template = template.replace(f"{{${var_name}}}", str(value))
            
        return template
    
    def _save_message(
        self,
        conversation: Conversation,
        user_message: str,
        bot_response: str,
        intent_detected: str,
        confidence_score: float,
        entities_extracted: List[Dict],
        response_time_ms: int
    ):
        """Save message to database"""
        message = Message(
            conversation_id=conversation.id,
            user_message=user_message,
            bot_response=bot_response,
            intent_detected=intent_detected,
            confidence_score=confidence_score,
            entities_extracted=entities_extracted,
            response_time_ms=response_time_ms
        )
        self.db.add(message)
        
    def _get_intent_suggestions(self, message: str, top_k: int = 3) -> List[str]:
        """Get intent suggestions for unclear messages"""
        if not self.intent_classifier.intent_embeddings:
            return []
            
        suggestions = self.intent_classifier.get_intent_suggestions(message, top_k)
        return [intent for intent, score in suggestions if score > 0.3]
    
    def end_conversation(self, session_id: str):
        """End a conversation"""
        conversation = self.db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.bot_id == self.bot_id,
            Conversation.status == ConversationStatus.ACTIVE
        ).first()
        
        if conversation:
            conversation.status = ConversationStatus.ENDED
            conversation.ended_at = time.time()
            self.db.commit()
            
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history"""
        conversation = self.db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.bot_id == self.bot_id
        ).first()
        
        if not conversation:
            return []
            
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        return [
            {
                'user_message': msg.user_message,
                'bot_response': msg.bot_response,
                'intent': msg.intent_detected,
                'confidence': msg.confidence_score,
                'entities': msg.entities_extracted,
                'timestamp': msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]
    
    def train_bot(self) -> Dict:
        """Train or retrain the bot"""
        logger.info(f"Starting training for bot {self.bot_id}")
        
        # Get all active intents with training phrases
        intents = self.db.query(Intent).filter(
            Intent.bot_id == self.bot_id,
            Intent.is_active == True
        ).all()
        
        # Filter intents that have training phrases
        intents_with_data = [
            intent for intent in intents 
            if intent.training_phrases and len(intent.training_phrases) > 0
        ]
        
        if not intents_with_data:
            raise ValueError("No training data available")
            
        # Train the intent classifier
        metrics = self.intent_classifier.train(intents_with_data)
        
        # Update bot status
        self.bot.status = BotStatus.ACTIVE
        self.db.commit()
        
        logger.info(f"Training completed for bot {self.bot_id}")
        return metrics