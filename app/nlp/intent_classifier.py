import numpy as np
import pickle
import hashlib
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import os
from app.core.config import settings
from app.models.models import Intent, TrainingPhrase
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Advanced intent classification using multiple approaches"""
    
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self.sentence_transformer = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
        self.rf_classifier = None
        self.tfidf_vectorizer = None
        self.intent_embeddings = {}
        self.intent_labels = []
        self.training_texts = []
        self.model_version = None
        
    def prepare_training_data(self, intents: List[Intent]) -> Tuple[List[str], List[str]]:
        """Prepare training data from intent objects"""
        texts = []
        labels = []
        
        for intent in intents:
            if not intent.is_active:
                continue
                
            for phrase in intent.training_phrases:
                texts.append(phrase.text.lower().strip())
                labels.append(intent.name)
                
        return texts, labels
    
    def train(self, intents: List[Intent]) -> Dict:
        """Train the intent classifier with multiple approaches"""
        logger.info(f"Training intent classifier for bot {self.bot_id}")
        
        texts, labels = self.prepare_training_data(intents)
        
        if not texts:
            raise ValueError("No training data available")
            
        # Create data hash for version tracking
        data_hash = hashlib.md5(str(texts + labels).encode()).hexdigest()[:10]
        self.model_version = f"bot_{self.bot_id}_{data_hash}"
        
        # Approach 1: Sentence Transformer Embeddings
        logger.info("Creating sentence embeddings...")
        embeddings = self.sentence_transformer.encode(texts)
        
        # Group embeddings by intent
        intent_groups = {}
        for text, label, embedding in zip(texts, labels, embeddings):
            if label not in intent_groups:
                intent_groups[label] = []
            intent_groups[label].append(embedding)
            
        # Calculate mean embeddings for each intent
        self.intent_embeddings = {}
        for intent_name, intent_embeddings in intent_groups.items():
            self.intent_embeddings[intent_name] = np.mean(intent_embeddings, axis=0)
            
        # Approach 2: TF-IDF + Random Forest
        logger.info("Training TF-IDF + Random Forest classifier...")
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            stop_words='english'
        )
        
        tfidf_features = self.tfidf_vectorizer.fit_transform(texts)
        
        self.rf_classifier = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight='balanced'
        )
        self.rf_classifier.fit(tfidf_features, labels)
        
        # Store training data for similarity matching
        self.training_texts = texts
        self.intent_labels = labels
        
        # Save model
        self.save_model()
        
        # Calculate training metrics
        train_accuracy = self.rf_classifier.score(tfidf_features, labels)
        
        metrics = {
            "accuracy": train_accuracy,
            "num_intents": len(set(labels)),
            "num_training_examples": len(texts),
            "model_version": self.model_version
        }
        
        logger.info(f"Training completed. Accuracy: {train_accuracy:.3f}")
        return metrics
    
    def predict(self, text: str, threshold: float = None) -> Tuple[str, float]:
        """Predict intent using ensemble of approaches"""
        if threshold is None:
            threshold = settings.MIN_CONFIDENCE_THRESHOLD
            
        text = text.lower().strip()
        
        # Approach 1: Sentence transformer similarity
        text_embedding = self.sentence_transformer.encode([text])[0]
        semantic_scores = {}
        
        for intent_name, intent_embedding in self.intent_embeddings.items():
            similarity = cosine_similarity([text_embedding], [intent_embedding])[0][0]
            semantic_scores[intent_name] = similarity
            
        # Approach 2: TF-IDF + Random Forest
        if self.tfidf_vectorizer and self.rf_classifier:
            tfidf_features = self.tfidf_vectorizer.transform([text])
            rf_probabilities = self.rf_classifier.predict_proba(tfidf_features)[0]
            rf_classes = self.rf_classifier.classes_
            
            rf_scores = dict(zip(rf_classes, rf_probabilities))
        else:
            rf_scores = {}
            
        # Approach 3: Direct similarity with training examples
        if self.training_texts:
            training_embeddings = self.sentence_transformer.encode(self.training_texts)
            similarities = cosine_similarity([text_embedding], training_embeddings)[0]
            
            # Find best matching training example
            best_idx = np.argmax(similarities)
            best_similarity = similarities[best_idx]
            best_intent = self.intent_labels[best_idx]
            
            direct_scores = {best_intent: best_similarity}
        else:
            direct_scores = {}
            
        # Ensemble: Combine scores with weights
        final_scores = {}
        all_intents = set(list(semantic_scores.keys()) + list(rf_scores.keys()) + list(direct_scores.keys()))
        
        for intent in all_intents:
            semantic_score = semantic_scores.get(intent, 0) * 0.4
            rf_score = rf_scores.get(intent, 0) * 0.4
            direct_score = direct_scores.get(intent, 0) * 0.2
            
            final_scores[intent] = semantic_score + rf_score + direct_score
            
        # Get best prediction
        if not final_scores:
            return None, 0.0
            
        best_intent = max(final_scores, key=final_scores.get)
        confidence = final_scores[best_intent]
        
        # Apply threshold
        if confidence < threshold:
            return None, confidence
            
        return best_intent, confidence
    
    def save_model(self):
        """Save the trained model to disk"""
        model_dir = os.path.join(settings.MODELS_DIR, f"bot_{self.bot_id}")
        os.makedirs(model_dir, exist_ok=True)
        
        model_data = {
            'intent_embeddings': self.intent_embeddings,
            'training_texts': self.training_texts,
            'intent_labels': self.intent_labels,
            'model_version': self.model_version
        }
        
        with open(os.path.join(model_dir, 'intent_classifier.pkl'), 'wb') as f:
            pickle.dump(model_data, f)
            
        if self.tfidf_vectorizer:
            joblib.dump(self.tfidf_vectorizer, os.path.join(model_dir, 'tfidf_vectorizer.pkl'))
            
        if self.rf_classifier:
            joblib.dump(self.rf_classifier, os.path.join(model_dir, 'rf_classifier.pkl'))
            
        logger.info(f"Model saved for bot {self.bot_id}")
    
    def load_model(self) -> bool:
        """Load a trained model from disk"""
        model_dir = os.path.join(settings.MODELS_DIR, f"bot_{self.bot_id}")
        
        try:
            with open(os.path.join(model_dir, 'intent_classifier.pkl'), 'rb') as f:
                model_data = pickle.load(f)
                
            self.intent_embeddings = model_data['intent_embeddings']
            self.training_texts = model_data['training_texts']
            self.intent_labels = model_data['intent_labels']
            self.model_version = model_data['model_version']
            
            tfidf_path = os.path.join(model_dir, 'tfidf_vectorizer.pkl')
            if os.path.exists(tfidf_path):
                self.tfidf_vectorizer = joblib.load(tfidf_path)
                
            rf_path = os.path.join(model_dir, 'rf_classifier.pkl')
            if os.path.exists(rf_path):
                self.rf_classifier = joblib.load(rf_path)
                
            logger.info(f"Model loaded for bot {self.bot_id}, version {self.model_version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model for bot {self.bot_id}: {e}")
            return False
    
    def get_intent_suggestions(self, text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Get top-k intent suggestions with confidence scores"""
        text = text.lower().strip()
        text_embedding = self.sentence_transformer.encode([text])[0]
        
        scores = []
        for intent_name, intent_embedding in self.intent_embeddings.items():
            similarity = cosine_similarity([text_embedding], [intent_embedding])[0][0]
            scores.append((intent_name, similarity))
            
        # Sort by confidence and return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]