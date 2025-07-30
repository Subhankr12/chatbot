# Chatbot Platform - Universal Chatbot Utility

A comprehensive, self-hosted chatbot platform that provides full control over your conversational AI infrastructure. Built as an alternative to Dialogflow CX, this platform offers multi-tenant support, advanced NLP capabilities, and complete customization for organizations and products.

## 🚀 Features

### Core Capabilities
- **Multi-tenant Architecture** - Support multiple organizations and products
- **Advanced NLP Engine** - Intent recognition with ensemble machine learning
- **Entity Extraction** - Custom entities, regex patterns, and system entities
- **Conversation Management** - Context-aware conversations with session handling
- **Training System** - Custom model training with your own datasets
- **RESTful API** - Complete API for integration with any application
- **Real-time Analytics** - Track performance and user interactions

### Enterprise Features
- **API Key Authentication** - Secure multi-tenant access control
- **Scalable Architecture** - Built for high-volume production use
- **Data Sovereignty** - Complete control over your data and models
- **Custom Entities** - Define domain-specific entities and patterns
- **Response Templates** - Dynamic responses with variable substitution
- **Bulk Operations** - Import/export training data and configurations

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Admin Panel   │    │   Web UI        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   FastAPI       │
                    │   REST API      │
                    └─────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   NLP       │    │ Conversation│    │  Training   │
    │   Engine    │    │   Manager   │    │   System    │
    └─────────────┘    └─────────────┘    └─────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │     Redis       │
                    └─────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (for containerized deployment)

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd chatbot-platform
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services:
```bash
docker-compose up -d
```

4. Create your first organization:
```bash
curl -X POST "http://localhost:8000/api/v1/organizations" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Organization"}'
```

### Option 2: Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

2. Set up database:
```bash
# Start PostgreSQL and Redis
# Update DATABASE_URL and REDIS_URL in .env
```

3. Run the application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 API Usage

### Authentication

All API requests require an API key in the Authorization header:

```bash
Authorization: Bearer cb_your_api_key_here
```

### Creating a Bot

1. **Create a bot:**
```bash
curl -X POST "http://localhost:8000/api/v1/bots" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Bot",
    "description": "Handles customer inquiries",
    "organization_id": 1,
    "confidence_threshold": 0.7
  }'
```

2. **Add intents:**
```bash
curl -X POST "http://localhost:8000/api/v1/bots/1/intents" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "greeting",
    "description": "User greetings",
    "bot_id": 1
  }'
```

3. **Add training phrases:**
```bash
curl -X POST "http://localhost:8000/api/v1/bots/1/intents/1/training-phrases" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello there",
    "intent_id": 1
  }'
```

4. **Add responses:**
```bash
curl -X POST "http://localhost:8000/api/v1/bots/1/intents/1/responses" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello! How can I help you today?",
    "intent_id": 1
  }'
```

5. **Train the bot:**
```bash
curl -X POST "http://localhost:8000/api/v1/bots/1/train" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

6. **Chat with the bot:**
```bash
curl -X POST "http://localhost:8000/api/v1/bots/1/chat" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "session_id": "user123-session456"
  }'
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Application
DEBUG=false
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/chatbot

# NLP Models
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm

# Training
MIN_CONFIDENCE_THRESHOLD=0.7
MAX_TRAINING_EXAMPLES=10000
```

### Advanced Configuration

- **Custom NLP Models**: Configure different sentence transformers
- **Multi-language Support**: Set language-specific models per bot
- **Custom Entities**: Define domain-specific entity types
- **Response Templates**: Use variables and context in responses

## 🎯 Use Cases

### E-commerce Support
```python
# Customer inquiry handling
intents = [
    "order_status", "return_request", "product_info",
    "shipping_query", "payment_issue"
]
```

### HR Assistant
```python
# Employee support
intents = [
    "leave_request", "policy_question", "payroll_query",
    "benefits_info", "office_hours"
]
```

### Technical Support
```python
# IT helpdesk
intents = [
    "password_reset", "software_issue", "hardware_problem",
    "account_access", "feature_request"
]
```

## 🔄 Migration from Dialogflow CX

### Data Export
1. Export intents and entities from Dialogflow CX
2. Convert to platform format using provided scripts
3. Bulk import using the API

### Training Data Migration
```python
# Example conversion script
dialogflow_data = load_dialogflow_export()
platform_data = convert_to_platform_format(dialogflow_data)
bulk_import_to_platform(platform_data)
```

### API Integration
Replace Dialogflow CX endpoints:
```python
# Before (Dialogflow CX)
response = dialogflow_client.detect_intent(session, query_input)

# After (Chatbot Platform)
response = requests.post(
    f"{CHATBOT_API}/bots/{bot_id}/chat",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"message": user_message, "session_id": session_id}
)
```

## 📊 Monitoring & Analytics

### Built-in Metrics
- Conversation volume and patterns
- Intent recognition accuracy
- Response time monitoring
- User satisfaction tracking

### Custom Analytics
- Export conversation data
- Integration with external analytics tools
- Custom reporting dashboards

## 🛡️ Security

### Authentication & Authorization
- API key-based authentication
- Organization-level isolation
- Role-based access control

### Data Protection
- Encrypted data at rest
- Secure API communications
- GDPR compliance features

## 🚀 Deployment

### Production Deployment

1. **Docker Compose (Simple)**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. **Kubernetes (Scalable)**:
```bash
kubectl apply -f k8s/
```

3. **Manual Deployment**:
- Set up PostgreSQL and Redis clusters
- Deploy API servers with load balancing
- Configure monitoring and logging

### Scaling Considerations
- Database connection pooling
- Redis clustering for session management
- Horizontal API server scaling
- Model caching strategies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Full API documentation at `/docs`
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Community discussions on GitHub Discussions
- **Enterprise Support**: Contact for enterprise support options

## 🔮 Roadmap

- [ ] Visual flow builder
- [ ] Advanced analytics dashboard
- [ ] Multi-language model support
- [ ] Voice interface capabilities
- [ ] Integration marketplace
- [ ] A/B testing framework

---

**Replace Dialogflow CX. Own Your Conversations. Scale Without Limits.**