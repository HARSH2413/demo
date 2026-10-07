from app.infrastructure.supabase_adapter import SupabaseAdapter
from app.interfaces.lexical_store import ILexicalStore

class BoxService:
    """
    Service layer for Box CRUD operations.
    Maintains architecture consistency.
    """
    def __init__(self, db: SupabaseAdapter, lexical_store: ILexicalStore):
        self.db = db
        self.lexical_store = lexical_store

    def create_box(self, name: str, user_id: str, description: str = None, domain: str = None) -> dict:
        return self.db.create_box(name, user_id, description, domain)

    def list_boxes(self, user_id: str) -> list[dict]:
        return self.db.list_boxes(user_id)

    def get_box(self, box_id: str, user_id: str) -> dict:
        return self.db.get_box(box_id, user_id)

    def update_box(self, box_id: str, user_id: str, data: dict) -> dict:
        return self.db.update_box(box_id, user_id, data)

    def delete_box(self, box_id: str, user_id: str) -> bool:
        success = self.db.delete_box(box_id, user_id)
        if success:
            self.lexical_store.invalidate_box(box_id)
        return success
