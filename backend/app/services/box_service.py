from app.infrastructure.supabase_adapter import SupabaseAdapter

class BoxService:
    """
    Service layer for Box CRUD operations.
    Maintains architecture consistency.
    """
    def __init__(self, db: SupabaseAdapter):
        self.db = db

    def create_box(self, name: str, user_id: str, description: str = None) -> dict:
        return self.db.create_box(name, user_id, description)

    def list_boxes(self, user_id: str) -> list[dict]:
        return self.db.list_boxes(user_id)

    def get_box(self, box_id: str, user_id: str) -> dict:
        return self.db.get_box(box_id, user_id)

    def update_box(self, box_id: str, user_id: str, data: dict) -> dict:
        return self.db.update_box(box_id, user_id, data)

    def delete_box(self, box_id: str, user_id: str) -> bool:
        return self.db.delete_box(box_id, user_id)
