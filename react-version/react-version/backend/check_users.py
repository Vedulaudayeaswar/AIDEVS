"""Check registered users in ChromaDB"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from utils.rag_manager import RAGManager
from utils.auth_manager import AuthManager

# Initialize managers
rag_manager = RAGManager()
auth_manager = AuthManager(rag_manager)

print("=" * 60)
print("CHECKING REGISTERED USERS")
print("=" * 60)

try:
    # Get all documents from users collection
    results = rag_manager.users_collection.get()
    
    if not results['ids'] or len(results['ids']) == 0:
        print("\n❌ NO USERS REGISTERED YET!")
        print("\nPlease register at: http://localhost:3000/register")
    else:
        print(f"\n✅ Found {len(results['ids'])} registered user(s):\n")
        
        for i, (user_id, metadata) in enumerate(zip(results['ids'], results['metadatas']), 1):
            print(f"{i}. Username: {user_id}")
            print(f"   Name: {metadata.get('first_name', '')} {metadata.get('last_name', '')}")
            print(f"   Registered: {metadata.get('registered_at', 'N/A')}")
            print(f"   Last Login: {metadata.get('last_login', 'N/A')}")
            
            # Try to decrypt API key
            encrypted_key = metadata.get('api_key_encrypted', '')
            if encrypted_key:
                try:
                    decrypted_key = auth_manager.decrypt_api_key(encrypted_key)
                    print(f"   API Key: {decrypted_key[:20]}...{decrypted_key[-10:]}")
                    print(f"   ✅ API Key decrypts successfully!")
                except Exception as e:
                    print(f"   ❌ API Key decryption failed: {str(e)}")
            else:
                print(f"   ❌ No API key stored!")
            
            print()

except Exception as e:
    print(f"\n❌ Error checking users: {str(e)}")
    import traceback
    traceback.print_exc()

print("=" * 60)
