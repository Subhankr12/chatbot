from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import enum
from datetime import datetime
from typing import Dict, Any


class BotStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRAINING = "training"


class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    ESCALATED = "escalated"


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bots = relationship("Bot", back_populates="organization")


class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    status = Column(Enum(BotStatus), default=BotStatus.ACTIVE)
    default_response = Column(Text, default="I'm sorry, I didn't understand that. Could you please rephrase?")
    confidence_threshold = Column(Float, default=0.7)
    language = Column(String(10), default="en")
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="bots")
    intents = relationship("Intent", back_populates="bot")
    entities = relationship("Entity", back_populates="bot")
    conversations = relationship("Conversation", back_populates="bot")


class Intent(Base):
    __tablename__ = "intents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="intents")
    training_phrases = relationship("TrainingPhrase", back_populates="intent")
    responses = relationship("Response", back_populates="intent")


class TrainingPhrase(Base):
    __tablename__ = "training_phrases"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    intent_id = Column(Integer, ForeignKey("intents.id"))
    entities_data = Column(JSON, default=[])  # Store entity annotations
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    intent = relationship("Intent", back_populates="training_phrases")


class Response(Base):
    __tablename__ = "responses"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    intent_id = Column(Integer, ForeignKey("intents.id"))
    response_type = Column(String(50), default="text")  # text, rich, custom
    metadata = Column(JSON, default={})  # For rich responses, buttons, etc.
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    intent = relationship("Intent", back_populates="responses")


class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    entity_type = Column(String(50), default="custom")  # custom, system, regex
    values = Column(JSON, default=[])  # Entity values and synonyms
    regex_pattern = Column(String(500))  # For regex entities
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="entities")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    user_id = Column(String(255))  # External user identifier
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    context = Column(JSON, default={})  # Conversation context and variables
    metadata = Column(JSON, default={})  # Additional metadata
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    
    # Relationships
    bot = relationship("Bot", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_message = Column(Text)
    bot_response = Column(Text)
    intent_detected = Column(String(255))
    confidence_score = Column(Float)
    entities_extracted = Column(JSON, default=[])
    response_time_ms = Column(Integer)
    feedback_rating = Column(Integer)  # 1-5 rating
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    model_version = Column(String(50))
    training_data_hash = Column(String(255))
    metrics = Column(JSON, default={})  # Training metrics
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    bot = relationship("Bot")


class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    date = Column(DateTime(timezone=True))
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    avg_confidence_score = Column(Float, default=0.0)
    unresolved_queries = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, default=0.0)
    user_satisfaction = Column(Float, default=0.0)
    top_intents = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("Bot")