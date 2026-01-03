"""Check what's in the database"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from utils.rag_manager import RAGManager
from utils.auth_manager import AuthManager

rag = RAGManager()
auth = AuthManager(rag)

# Get all users
try:
    result = rag.users_collection.get()
    print("=" * 60)
    print("USERS IN DATABASE:")
    print("=" * 60)
    
    if result['ids']:
        for i, user_id in enumerate(result['ids']):
            metadata = result['metadatas'][i]
            print(f"\nUser {i+1}:")
            print(f"  Username: {metadata.get('username')}")
            print(f"  First Name: {metadata.get('first_name')}")
            print(f"  Last Name: {metadata.get('last_name')}")
            print(f"  Encrypted API Key: {metadata.get('encrypted_api_key', '')[:30]}...")
            
            # Try to decrypt
            encrypted_key = metadata.get('encrypted_api_key')
            if encrypted_key:
                try:
                    decrypted = auth.decrypt_api_key(encrypted_key)
                    print(f"  Decrypted API Key: {decrypted[:20]}...{decrypted[-10:]}")
                except Exception as e:
                    print(f"  ❌ Decryption failed: {e}")
    else:
        print("No users found in database!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
