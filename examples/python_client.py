"""
Chatbot Platform Python Client Example

This example demonstrates how to integrate with the Chatbot Platform API
using Python. Perfect for building custom applications on top of the platform.
"""

import requests
import json
from typing import Optional, Dict, List
import time


class ChatbotClient:
    """Python client for the Chatbot Platform API"""
    
    def __init__(self, api_base_url: str, api_key: str):
        """
        Initialize the client
        
        Args:
            api_base_url: Base URL of the API (e.g., 'http://localhost:8000')
            api_key: Your organization's API key
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def create_bot(self, name: str, description: str = None, **kwargs) -> Dict:
        """Create a new bot"""
        data = {
            'name': name,
            'description': description,
            **kwargs
        }
        response = self.session.post(
            f'{self.api_base_url}/api/v1/bots',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def create_intent(self, bot_id: int, name: str, description: str = None) -> Dict:
        """Create a new intent for a bot"""
        data = {
            'name': name,
            'description': description,
            'bot_id': bot_id
        }
        response = self.session.post(
            f'{self.api_base_url}/api/v1/bots/{bot_id}/intents',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def add_training_phrase(self, bot_id: int, intent_id: int, text: str) -> Dict:
        """Add a training phrase to an intent"""
        data = {
            'text': text,
            'intent_id': intent_id
        }
        response = self.session.post(
            f'{self.api_base_url}/api/v1/bots/{bot_id}/intents/{intent_id}/training-phrases',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def add_response(self, bot_id: int, intent_id: int, text: str) -> Dict:
        """Add a response to an intent"""
        data = {
            'text': text,
            'intent_id': intent_id
        }
        response = self.session.post(
            f'{self.api_base_url}/api/v1/bots/{bot_id}/intents/{intent_id}/responses',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def train_bot(self, bot_id: int) -> Dict:
        """Train a bot with its current data"""
        response = self.session.post(
            f'{self.api_base_url}/api/v1/bots/{bot_id}/train'
        )
        response.raise_for_status()
        return response.json()
    
    def chat(self, bot_id: int, message: str, session_id: str, 
             user_id: str = None, context: Dict = None) -> Dict:
        """Send a message to the bot and get response"""
        data = {
            'message': message,
            'session_id': session_id,
            'user_id': user_id,
            'context': context
        }
        response = self.session.post(
            f'{self.api_base_url}/api/v1/bots/{bot_id}/chat',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_conversation_history(self, bot_id: int, session_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history for a session"""
        response = self.session.get(
            f'{self.api_base_url}/api/v1/bots/{bot_id}/conversations/{session_id}/history',
            params={'limit': limit}
        )
        response.raise_for_status()
        return response.json()


def main():
    """Example usage of the ChatbotClient"""
    
    # Initialize client
    client = ChatbotClient(
        api_base_url='http://localhost:8000',
        api_key='your_api_key_here'  # Replace with your actual API key
    )
    
    try:
        # Create a bot
        print("Creating bot...")
        bot = client.create_bot(
            name="Customer Support Bot",
            description="Handles customer inquiries",
            organization_id=1,  # Replace with your organization ID
            confidence_threshold=0.7
        )
        bot_id = bot['id']
        print(f"Created bot: {bot['name']} (ID: {bot_id})")
        
        # Create intents with training data
        intents_data = [
            {
                'name': 'greeting',
                'description': 'User greetings',
                'training_phrases': [
                    'hello', 'hi', 'hey', 'good morning', 'good afternoon'
                ],
                'responses': [
                    'Hello! How can I help you today?',
                    'Hi there! What can I do for you?',
                    'Greetings! How may I assist you?'
                ]
            },
            {
                'name': 'order_status',
                'description': 'Check order status',
                'training_phrases': [
                    'where is my order', 'order status', 'track my order',
                    'when will my order arrive', 'order tracking'
                ],
                'responses': [
                    'I can help you track your order. Could you please provide your order number?',
                    'To check your order status, I\'ll need your order number. Can you share it?'
                ]
            },
            {
                'name': 'product_info',
                'description': 'Product information requests',
                'training_phrases': [
                    'tell me about this product', 'product details', 'product information',
                    'what does this product do', 'product specs'
                ],
                'responses': [
                    'I\'d be happy to provide product information. Which product are you interested in?',
                    'Sure! Could you specify which product you\'d like to know more about?'
                ]
            }
        ]
        
        # Create intents and add training data
        for intent_data in intents_data:
            print(f"Creating intent: {intent_data['name']}")
            intent = client.create_intent(
                bot_id=bot_id,
                name=intent_data['name'],
                description=intent_data['description']
            )
            intent_id = intent['id']
            
            # Add training phrases
            for phrase in intent_data['training_phrases']:
                client.add_training_phrase(bot_id, intent_id, phrase)
            
            # Add responses
            for response_text in intent_data['responses']:
                client.add_response(bot_id, intent_id, response_text)
        
        # Train the bot
        print("Training bot...")
        training_result = client.train_bot(bot_id)
        print(f"Training completed: {training_result['message']}")
        print(f"Training metrics: {training_result['metrics']}")
        
        # Test the bot with some messages
        print("\nTesting bot...")
        test_messages = [
            "Hello",
            "Hi there",
            "Where is my order?",
            "I need product information",
            "Tell me about your products"
        ]
        
        session_id = f"test_session_{int(time.time())}"
        
        for message in test_messages:
            print(f"\nUser: {message}")
            response = client.chat(
                bot_id=bot_id,
                message=message,
                session_id=session_id,
                user_id="test_user"
            )
            
            print(f"Bot: {response['text']}")
            print(f"Intent: {response.get('intent', 'None')} (confidence: {response['confidence']:.2f})")
            if response['entities']:
                print(f"Entities: {response['entities']}")
        
        # Get conversation history
        print(f"\nConversation history for session {session_id}:")
        history = client.get_conversation_history(bot_id, session_id)
        for msg in history:
            print(f"User: {msg['user_message']}")
            print(f"Bot: {msg['bot_response']}")
            print("---")
            
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()