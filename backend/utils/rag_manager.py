"""Optional semantic memory for the classic builder (ChromaDB).

ChromaDB is no longer used for anything authoritative (users and projects live
in the relational database). If `chromadb` is installed it is used with a
*persistent* client; otherwise this degrades to an in-process store so the
app still runs without the heavy dependency.
"""
import logging
import os
from collections import defaultdict
from datetime import datetime

log = logging.getLogger("aidevs.rag")


class RAGManager:
    def __init__(self, persist_directory=None):
        self.collection = None
        self._fallback = defaultdict(list)
        if os.getenv("ENABLE_CHROMADB", "0") != "1":
            return
        try:
            import chromadb
            path = persist_directory or os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
            client = chromadb.PersistentClient(path=path)
            self.collection = client.get_or_create_collection(name="aidevs_conversations")
        except Exception as exc:  # optional component
            log.warning("ChromaDB unavailable, using in-memory context store: %s", exc)

    def store_interaction(self, session_id, agent, message, response, stage):
        text = f"User: {message}\n{agent}: {response}"
        if self.collection is None:
            self._fallback[session_id].append({"agent": agent, "stage": stage, "text": text})
            self._fallback[session_id] = self._fallback[session_id][-50:]
            return
        self.collection.add(
            documents=[text],
            metadatas=[{"session_id": session_id, "agent": agent, "stage": stage,
                        "timestamp": datetime.now().isoformat()}],
            ids=[f"{session_id}_{agent}_{datetime.now().isoformat()}"])

    def retrieve_context(self, query, session_id, n_results=5):
        try:
            if self.collection is None:
                items = self._fallback.get(session_id, [])[-n_results:]
                return "\n\n".join(f"[{i['agent']} at {i['stage']}]: {i['text'][:300]}" for i in items)
            results = self.collection.query(query_texts=[query], n_results=n_results,
                                            where={"session_id": session_id})
            if not results["documents"] or not results["documents"][0]:
                return ""
            return "\n\n".join(f"[{m['agent']} at {m['stage']}]: {d[:300]}"
                               for d, m in zip(results["documents"][0], results["metadatas"][0], strict=False))
        except Exception as exc:
            log.warning("RAG retrieval error: %s", exc)
            return ""

    def clear_session(self, session_id):
        self._fallback.pop(session_id, None)
        if self.collection is not None:
            try:
                ids = self.collection.get(where={"session_id": session_id})["ids"]
                if ids:
                    self.collection.delete(ids=ids)
            except Exception as exc:
                log.warning("Error clearing session: %s", exc)
