import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("trinetra.firebase")

_firebase_app = None
_firestore_db = None
_is_live_firebase = False

class LocalFirestoreDocument:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return self._data.copy()

    def get(self, key, default=None):
        return self._data.get(key, default)

class LocalFirestoreCollection:
    def __init__(self, store, name):
        self.store = store
        self.name = name

    def _get_items(self):
        return self.store.get_collection(self.name)

    def document(self, doc_id=None):
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())
        return LocalFirestoreDocumentRef(self.store, self.name, doc_id)

    def add(self, data):
        import uuid
        doc_id = data.get("id") or str(uuid.uuid4())
        data["id"] = doc_id
        self.store.set_doc(self.name, doc_id, data)
        return None, LocalFirestoreDocumentRef(self.store, self.name, doc_id)

    def stream(self):
        items = self._get_items()
        return [LocalFirestoreDocument(doc_id, data) for doc_id, data in items.items()]

    def get(self):
        return self.stream()

    def where(self, field, op, value):
        items = self._get_items()
        filtered = {}
        for doc_id, data in items.items():
            field_val = data.get(field)
            match = False
            if op == "==" and field_val == value:
                match = True
            elif op == "in" and isinstance(value, list) and field_val in value:
                match = True
            elif op == "array_contains" and isinstance(field_val, list) and value in field_val:
                match = True
            elif op == "array_contains_any" and isinstance(field_val, list) and any(v in field_val for v in value):
                match = True
            if match:
                filtered[doc_id] = data
        
        # Return a mock collection wrapper around filtered items
        sub_col = LocalFirestoreCollection(self.store, self.name)
        sub_col._get_items = lambda: filtered
        return sub_col

class LocalFirestoreDocumentRef:
    def __init__(self, store, collection_name, doc_id):
        self.store = store
        self.collection_name = collection_name
        self.id = doc_id

    def set(self, data, merge=False):
        self.store.set_doc(self.collection_name, self.id, data, merge=merge)

    def update(self, data):
        self.store.set_doc(self.collection_name, self.id, data, merge=True)

    def get(self):
        data = self.store.get_doc(self.collection_name, self.id)
        if data is None:
            class EmptyDoc:
                exists = False
                def to_dict(self): return None
            return EmptyDoc()
        
        doc = LocalFirestoreDocument(self.id, data)
        doc.exists = True
        return doc

    def delete(self):
        self.store.delete_doc(self.collection_name, self.id)

class LocalFirestoreStore:
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._data = {}
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.error(f"Failed loading local Firestore file: {e}")
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed saving local Firestore file: {e}")

    def collection(self, name):
        return LocalFirestoreCollection(self, name)

    def get_collection(self, name):
        return self._data.get(name, {})

    def get_doc(self, collection_name, doc_id):
        return self._data.get(collection_name, {}).get(str(doc_id))

    def set_doc(self, collection_name, doc_id, data, merge=False):
        if collection_name not in self._data:
            self._data[collection_name] = {}
        doc_id_str = str(doc_id)
        if merge and doc_id_str in self._data[collection_name]:
            self._data[collection_name][doc_id_str].update(data)
        else:
            self._data[collection_name][doc_id_str] = data
        self._save()

    def delete_doc(self, collection_name, doc_id):
        doc_id_str = str(doc_id)
        if collection_name in self._data and doc_id_str in self._data[collection_name]:
            del self._data[collection_name][doc_id_str]
            self._save()

def initialize_firebase():
    global _firebase_app, _firestore_db, _is_live_firebase

    if _firestore_db is not None:
        return _firestore_db

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    if service_account_path and not os.path.isabs(service_account_path) and not os.path.exists(service_account_path):
        backend_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", service_account_path))
        if os.path.exists(backend_dir_path):
            service_account_path = backend_dir_path

    force_local = os.getenv("USE_LOCAL_FIRESTORE", "false").lower() in ["true", "1", "yes"]
    local_store_path = Path(__file__).parent.parent / "data" / "firestore_store.json"

    if force_local or not service_account_path or not os.path.exists(service_account_path):
        logger.info("Initializing persistent Local Firestore store.")
        _firestore_db = LocalFirestoreStore(local_store_path)
        _is_live_firebase = False
        return _firestore_db

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            logger.info(f"Initializing Firebase with Service Account file: {service_account_path}")
            cred = credentials.Certificate(service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            _firestore_db = firestore.client()
            _is_live_firebase = True
        else:
            _firebase_app = firebase_admin.get_app()
            _firestore_db = firestore.client()
            _is_live_firebase = True

    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {e}. Falling back to persistent Firestore store.")
        _firestore_db = LocalFirestoreStore(local_store_path)
        _is_live_firebase = False

    return _firestore_db

def get_db():
    return initialize_firebase()

def is_firebase_live():
    initialize_firebase()
    return _is_live_firebase

def get_firebase_status():
    initialize_firebase()
    return {
        "firebase": "connected" if _is_live_firebase else "persistent_emulator_ready",
        "firestore": "connected",
        "mode": "Cloud Firestore" if _is_live_firebase else "Local Persistent Store (Firestore interface)"
    }
