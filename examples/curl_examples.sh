#!/bin/bash

# Chatbot Platform API Examples
# This script demonstrates all the main API endpoints using cURL

# Configuration
API_BASE="http://localhost:8000/api/v1"
API_KEY="your_api_key_here"  # Replace with your actual API key

# Helper function for API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -X $method "$API_BASE$endpoint" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json"
    else
        curl -X $method "$API_BASE$endpoint" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

echo "🤖 Chatbot Platform API Examples"
echo "=================================="

# 1. Create Organization (Admin endpoint)
echo "1. Creating organization..."
ORG_RESPONSE=$(api_call POST "/organizations" '{
  "name": "My Test Organization"
}')
echo "Response: $ORG_RESPONSE"
echo ""

# Extract API key from response (you would normally save this)
# API_KEY=$(echo $ORG_RESPONSE | jq -r '.api_key')

# 2. Create a Bot
echo "2. Creating bot..."
BOT_RESPONSE=$(api_call POST "/bots" '{
  "name": "Customer Support Bot",
  "description": "Handles customer inquiries and support requests",
  "organization_id": 1,
  "confidence_threshold": 0.7,
  "language": "en"
}')
echo "Response: $BOT_RESPONSE"
BOT_ID=$(echo $BOT_RESPONSE | jq -r '.id')
echo "Bot ID: $BOT_ID"
echo ""

# 3. Create Intents
echo "3. Creating intents..."

# Greeting intent
GREETING_INTENT=$(api_call POST "/bots/$BOT_ID/intents" '{
  "name": "greeting",
  "description": "User greetings and hellos",
  "bot_id": '$BOT_ID',
  "priority": 1
}')
GREETING_INTENT_ID=$(echo $GREETING_INTENT | jq -r '.id')
echo "Created greeting intent: $GREETING_INTENT_ID"

# Order status intent
ORDER_INTENT=$(api_call POST "/bots/$BOT_ID/intents" '{
  "name": "order_status",
  "description": "Check order status inquiries",
  "bot_id": '$BOT_ID',
  "priority": 2
}')
ORDER_INTENT_ID=$(echo $ORDER_INTENT | jq -r '.id')
echo "Created order status intent: $ORDER_INTENT_ID"

# Product info intent
PRODUCT_INTENT=$(api_call POST "/bots/$BOT_ID/intents" '{
  "name": "product_info",
  "description": "Product information requests",
  "bot_id": '$BOT_ID',
  "priority": 3
}')
PRODUCT_INTENT_ID=$(echo $PRODUCT_INTENT | jq -r '.id')
echo "Created product info intent: $PRODUCT_INTENT_ID"
echo ""

# 4. Add Training Phrases
echo "4. Adding training phrases..."

# Greeting training phrases
greeting_phrases=(
  "hello"
  "hi"
  "hey"
  "good morning"
  "good afternoon"
  "greetings"
  "what's up"
)

for phrase in "${greeting_phrases[@]}"; do
  api_call POST "/bots/$BOT_ID/intents/$GREETING_INTENT_ID/training-phrases" '{
    "text": "'$phrase'",
    "intent_id": '$GREETING_INTENT_ID'
  }' > /dev/null
done
echo "Added ${#greeting_phrases[@]} greeting training phrases"

# Order status training phrases
order_phrases=(
  "where is my order"
  "order status"
  "track my order"
  "when will my order arrive"
  "order tracking"
  "shipping status"
  "delivery update"
)

for phrase in "${order_phrases[@]}"; do
  api_call POST "/bots/$BOT_ID/intents/$ORDER_INTENT_ID/training-phrases" '{
    "text": "'$phrase'",
    "intent_id": '$ORDER_INTENT_ID'
  }' > /dev/null
done
echo "Added ${#order_phrases[@]} order status training phrases"

# Product info training phrases
product_phrases=(
  "tell me about this product"
  "product details"
  "product information"
  "what does this product do"
  "product specs"
  "product features"
  "more info about product"
)

for phrase in "${product_phrases[@]}"; do
  api_call POST "/bots/$BOT_ID/intents/$PRODUCT_INTENT_ID/training-phrases" '{
    "text": "'$phrase'",
    "intent_id": '$PRODUCT_INTENT_ID'
  }' > /dev/null
done
echo "Added ${#product_phrases[@]} product info training phrases"
echo ""

# 5. Add Responses
echo "5. Adding responses..."

# Greeting responses
greeting_responses=(
  "Hello! How can I help you today?"
  "Hi there! What can I do for you?"
  "Greetings! How may I assist you?"
)

for response in "${greeting_responses[@]}"; do
  api_call POST "/bots/$BOT_ID/intents/$GREETING_INTENT_ID/responses" '{
    "text": "'$response'",
    "intent_id": '$GREETING_INTENT_ID',
    "response_type": "text"
  }' > /dev/null
done
echo "Added ${#greeting_responses[@]} greeting responses"

# Order status responses
order_responses=(
  "I can help you track your order. Could you please provide your order number?"
  "To check your order status, I'll need your order number. Can you share it?"
  "Sure! Please share your order number and I'll look up the status for you."
)

for response in "${order_responses[@]}"; do
  api_call POST "/bots/$BOT_ID/intents/$ORDER_INTENT_ID/responses" '{
    "text": "'$response'",
    "intent_id": '$ORDER_INTENT_ID',
    "response_type": "text"
  }' > /dev/null
done
echo "Added ${#order_responses[@]} order status responses"

# Product info responses
product_responses=(
  "I'd be happy to provide product information. Which product are you interested in?"
  "Sure! Could you specify which product you'd like to know more about?"
  "I can help with product details. What product would you like information about?"
)

for response in "${product_responses[@]}"; do
  api_call POST "/bots/$BOT_ID/intents/$PRODUCT_INTENT_ID/responses" '{
    "text": "'$response'",
    "intent_id": '$PRODUCT_INTENT_ID',
    "response_type": "text"
  }' > /dev/null
done
echo "Added ${#product_responses[@]} product info responses"
echo ""

# 6. Train the Bot
echo "6. Training bot..."
TRAINING_RESPONSE=$(api_call POST "/bots/$BOT_ID/train")
echo "Training response: $TRAINING_RESPONSE"
echo ""

# 7. Check Bot Status
echo "7. Checking bot status..."
STATUS_RESPONSE=$(api_call GET "/bots/$BOT_ID/status")
echo "Bot status: $STATUS_RESPONSE"
echo ""

# 8. Test Chat Functionality
echo "8. Testing chat functionality..."

# Test messages
test_messages=(
  "Hello"
  "Hi there"
  "Where is my order?"
  "I need product information"
  "Good morning"
  "Track my order please"
)

session_id="test_session_$(date +%s)"
echo "Using session ID: $session_id"

for message in "${test_messages[@]}"; do
  echo ""
  echo "User: $message"
  
  CHAT_RESPONSE=$(api_call POST "/bots/$BOT_ID/chat" '{
    "message": "'$message'",
    "session_id": "'$session_id'",
    "user_id": "test_user"
  }')
  
  # Extract response text and intent
  bot_text=$(echo $CHAT_RESPONSE | jq -r '.text')
  intent=$(echo $CHAT_RESPONSE | jq -r '.intent // "None"')
  confidence=$(echo $CHAT_RESPONSE | jq -r '.confidence')
  
  echo "Bot: $bot_text"
  echo "Intent: $intent (confidence: $confidence)"
done
echo ""

# 9. Get Conversation History
echo "9. Getting conversation history..."
HISTORY_RESPONSE=$(api_call GET "/bots/$BOT_ID/conversations/$session_id/history")
echo "Conversation history: $HISTORY_RESPONSE"
echo ""

# 10. List All Resources
echo "10. Listing resources..."

echo "All bots:"
api_call GET "/bots"
echo ""

echo "Bot intents:"
api_call GET "/bots/$BOT_ID/intents"
echo ""

echo "Greeting intent training phrases:"
api_call GET "/bots/$BOT_ID/intents/$GREETING_INTENT_ID/training-phrases"
echo ""

echo "Greeting intent responses:"
api_call GET "/bots/$BOT_ID/intents/$GREETING_INTENT_ID/responses"
echo ""

# 11. End Conversation
echo "11. Ending conversation..."
END_RESPONSE=$(api_call POST "/bots/$BOT_ID/conversations/$session_id/end")
echo "End conversation response: $END_RESPONSE"
echo ""

echo "✅ API examples completed!"
echo ""
echo "Summary:"
echo "- Created organization and bot"
echo "- Added 3 intents with training phrases and responses"
echo "- Trained the bot"
echo "- Tested chat functionality"
echo "- Retrieved conversation history"
echo ""
echo "Your bot is ready to use!"
echo "Bot ID: $BOT_ID"
echo "API Key: $API_KEY"