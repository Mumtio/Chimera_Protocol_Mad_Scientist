"""
Memory service for vector-based semantic search using TF-IDF
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Tuple, Dict
from .models import Memory


class MemoryService:
    """
    Service for storing and searching memories using TF-IDF vectorization
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self._corpus = []
        self._memory_ids = []
    
    def store(self, text: str, memory_id: int) -> bool:
        """
        Store a memory text with its ID
        
        Args:
            text: The memory text content
            memory_id: Database ID of the memory
            
        Returns:
            bool: Success status
        """
        try:
            self._corpus.append(text)
            self._memory_ids.append(memory_id)
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, conversation_id: str = None, include_global: bool = True) -> List[Dict]:
        """
        Search for similar memories using TF-IDF cosine similarity
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            conversation_id: Optional filter by conversation
            include_global: Include team-global memories in search
            
        Returns:
            List of dicts with memory data and similarity scores
        """
        try:
            # Get memories from database
            memories_qs = Memory.objects.all()
            
            if conversation_id:
                if include_global:
                    # Include both conversation-specific and team-global memories
                    from django.db.models import Q
                    memories_qs = memories_qs.filter(
                        Q(conversation_id=conversation_id) | Q(scope='team-global')
                    )
                else:
                    # Only conversation-specific
                    memories_qs = memories_qs.filter(conversation_id=conversation_id)
            
            memories = list(memories_qs)
            
            if not memories:
                return []
            
            # Build corpus from memories
            texts = [m.text for m in memories]
            
            # Add query to corpus for vectorization
            all_texts = texts + [query]
            
            # Compute TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Query vector is the last one
            query_vector = tfidf_matrix[-1]
            
            # Document vectors are all except the last
            doc_vectors = tfidf_matrix[:-1]
            
            # Compute cosine similarity
            similarities = cosine_similarity(query_vector, doc_vectors).flatten()
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Build results
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:  # Only include non-zero similarities
                    memory = memories[idx]
                    results.append({
                        'id': memory.id,
                        'text': memory.text,
                        'score': float(similarities[idx]),
                        'tags': memory.tags,
                        'conversation_id': memory.conversation_id,
                        'scope': memory.scope,
                        'created_at': memory.created_at.isoformat()
                    })
            
            return results
            
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []
    
    def rebuild_index(self):
        """
        Rebuild the search index from database
        """
        self._corpus = []
        self._memory_ids = []
        
        memories = Memory.objects.all().order_by('id')
        for memory in memories:
            self._corpus.append(memory.text)
            self._memory_ids.append(memory.id)


# Global instance
memory_service = MemoryService()
