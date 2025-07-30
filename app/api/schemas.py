from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


# Enums
class BotStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRAINING = "training"


class EntityTypeEnum(str, Enum):
    CUSTOM = "custom"
    SYSTEM = "system"
    REGEX = "regex"


class ResponseTypeEnum(str, Enum):
    TEXT = "text"
    RICH = "rich"
    CUSTOM = "custom"


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


# Organization schemas
class OrganizationBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class Organization(OrganizationBase):
    id: int
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


# Bot schemas
class BotBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    default_response: Optional[str] = "I'm sorry, I didn't understand that. Could you please rephrase?"
    confidence_threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0)
    language: Optional[str] = Field("en", min_length=2, max_length=10)
    settings: Optional[Dict[str, Any]] = {}


class BotCreate(BotBase):
    organization_id: int


class BotUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[BotStatusEnum] = None
    default_response: Optional[str] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    settings: Optional[Dict[str, Any]] = None


class Bot(BotBase):
    id: int
    organization_id: int
    status: BotStatusEnum
    created_at: datetime
    updated_at: Optional[datetime]


# Intent schemas
class IntentBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[int] = 0


class IntentCreate(IntentBase):
    bot_id: int


class IntentUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class Intent(IntentBase):
    id: int
    bot_id: int
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: Optional[datetime]


# Training Phrase schemas
class TrainingPhraseBase(BaseSchema):
    text: str = Field(..., min_length=1)
    entities_data: Optional[List[Dict[str, Any]]] = []


class TrainingPhraseCreate(TrainingPhraseBase):
    intent_id: int


class TrainingPhraseUpdate(BaseSchema):
    text: Optional[str] = Field(None, min_length=1)
    entities_data: Optional[List[Dict[str, Any]]] = None


class TrainingPhrase(TrainingPhraseBase):
    id: int
    intent_id: int
    created_at: datetime


# Response schemas
class ResponseBase(BaseSchema):
    text: str = Field(..., min_length=1)
    response_type: Optional[ResponseTypeEnum] = ResponseTypeEnum.TEXT
    metadata: Optional[Dict[str, Any]] = {}
    priority: Optional[int] = 0


class ResponseCreate(ResponseBase):
    intent_id: int


class ResponseUpdate(BaseSchema):
    text: Optional[str] = Field(None, min_length=1)
    response_type: Optional[ResponseTypeEnum] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None


class Response(ResponseBase):
    id: int
    intent_id: int
    created_at: datetime


# Entity schemas
class EntityBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    entity_type: Optional[EntityTypeEnum] = EntityTypeEnum.CUSTOM
    values: Optional[List[Union[str, Dict[str, Any]]]] = []
    regex_pattern: Optional[str] = Field(None, max_length=500)


class EntityCreate(EntityBase):
    bot_id: int


class EntityUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    entity_type: Optional[EntityTypeEnum] = None
    values: Optional[List[Union[str, Dict[str, Any]]]] = None
    regex_pattern: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class Entity(EntityBase):
    id: int
    bot_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


# Chat schemas
class ChatRequest(BaseSchema):
    message: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class EntityExtracted(BaseSchema):
    entity: str
    value: Any
    start: int
    end: int
    confidence: float
    method: str
    raw_value: Optional[str] = None


class ChatResponse(BaseSchema):
    text: str
    intent: Optional[str] = None
    confidence: float
    entities: List[EntityExtracted] = []
    context: Dict[str, Any] = {}
    response_time_ms: int
    session_id: str
    suggestions: List[str] = []
    metadata: Dict[str, Any] = {}


# Training schemas
class TrainingRequest(BaseSchema):
    bot_id: int


class TrainingResponse(BaseSchema):
    status: str
    metrics: Dict[str, Any]
    message: str


# Analytics schemas
class ConversationHistory(BaseSchema):
    user_message: Optional[str]
    bot_response: Optional[str]
    intent: Optional[str]
    confidence: Optional[float]
    entities: List[Dict[str, Any]] = []
    timestamp: str


class BotAnalytics(BaseSchema):
    total_conversations: int
    total_messages: int
    avg_confidence_score: float
    unresolved_queries: int
    avg_response_time_ms: float
    user_satisfaction: float
    top_intents: List[Dict[str, Any]]
    date_range: Dict[str, str]


# Bulk operations
class BulkIntentCreate(BaseSchema):
    intents: List[Dict[str, Any]]
    bot_id: int


class BulkTrainingData(BaseSchema):
    training_data: List[Dict[str, Any]]
    bot_id: int


# API Response wrappers
class SuccessResponse(BaseSchema):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None


class ErrorResponse(BaseSchema):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# Pagination
class PaginationParams(BaseSchema):
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=100)


class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int