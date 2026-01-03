"""RAG Manager using ChromaDB for context storage and retrieval"""
import chromadb
from chromadb.config import Settings
import json
from datetime import datetime

class RAGManager:
    def __init__(self, persist_directory="./chroma_db"):
        """Initialize ChromaDB for RAG storage"""
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Create or get collection for conversations
        self.collection = self.client.get_or_create_collection(
            name="aidevs_conversations",
            metadata={"description": "AIDevs conversation history and context"}
        )
        
        # Create or get collection for users
        self.users_collection = self.client.get_or_create_collection(
            name="aidevs_users",
            metadata={"description": "AIDevs user accounts"}
        )
    
    def store_interaction(self, session_id, agent, message, response, stage):
        """Store conversation interaction in vector database"""
        # Create unique ID
        interaction_id = f"{session_id}_{agent}_{datetime.now().isoformat()}"
        
        # Combine message and response for embedding
        combined_text = f"User: {message}\n{agent}: {response}"
        
        # Store in ChromaDB
        self.collection.add(
            documents=[combined_text],
            metadatas=[{
                "session_id": session_id,
                "agent": agent,
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
                "message": message[:500],  # Truncate for metadata
                "response": response[:500]
            }],
            ids=[interaction_id]
        )
    
    def retrieve_context(self, query, session_id, n_results=5):
        """Retrieve relevant context from conversation history"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"session_id": session_id}
            )
            
            if not results['documents'] or not results['documents'][0]:
                return ""
            
            # Format context
            context_parts = []
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                context_parts.append(f"[{metadata['agent']} at {metadata['stage']}]: {doc[:300]}")
            
            return "\n\n".join(context_parts)
        
        except Exception as e:
            print(f"RAG retrieval error: {e}")
            return ""
    
    def get_session_history(self, session_id, limit=10):
        """Get full session history"""
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                limit=limit
            )
            
            return results
        except Exception as e:
            print(f"Error getting session history: {e}")
            return {"documents": [], "metadatas": []}
    
    def clear_session(self, session_id):
        """Clear all data for a session"""
        try:
            # Get all IDs for this session
            results = self.collection.get(
                where={"session_id": session_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
        
        except Exception as e:
            print(f"Error clearing session: {e}")
    
    def get_latest_code(self, session_id, agent='frontend'):
        """Retrieve latest generated code from specific agent"""
        try:
            results = self.collection.query(
                query_texts=["code generation"],
                n_results=1,
                where={
                    "session_id": session_id,
                    "agent": agent
                }
            )
            
            if results['metadatas'] and results['metadatas'][0]:
                return results['metadatas'][0][0].get('response', '')
            
            return ""
        
        except Exception as e:
            print(f"Error getting latest code: {e}")
            return ""
    
    def store_user(self, user_data):
        """Store user account in ChromaDB"""
        username = user_data['username']
        
        # Store user document
        self.users_collection.upsert(
            documents=[f"User: {username}"],
            metadatas=[user_data],
            ids=[username]
        )
    
    def get_user(self, username):
        """Retrieve user by username"""
        try:
            results = self.users_collection.get(
                ids=[username]
            )
            
            if results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0]
            
            return None
        
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_last_login(self, username):
        """Update user's last login timestamp"""
        user = self.get_user(username)
        if user:
            user['last_login'] = datetime.now().isoformat()
            self.store_user(user)
