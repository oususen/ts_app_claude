# app/repository/production_repository.py
from .database_manager import DatabaseManager
import pandas as pd

class ProductionRepository:
    """生産関連データアクセス"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_production_instructions(self, start_date=None, end_date=None) -> pd.DataFrame:
        """生産指示データ取得 - 製品情報と結合"""
        base_query = """
        SELECT 
            pid.id,
            pid.product_id,
            pid.instruction_date,
            pid.instruction_quantity,
            pid.inspection_category,
            p.product_code,
            p.product_name
        FROM production_instructions_detail pid
        LEFT JOIN products p ON pid.product_id = p.id
        WHERE pid.instruction_quantity IS NOT NULL 
        AND pid.instruction_quantity > 0
        """
        
        if start_date and end_date:
            query = base_query + " AND pid.instruction_date BETWEEN %s AND %s ORDER BY pid.instruction_date"
            return self.db.execute_query(query, [start_date, end_date])
        else:
            query = base_query + " ORDER BY pid.instruction_date"
            return self.db.execute_query(query)# app/repository/production_repository.py
from .database_manager import DatabaseManager
import pandas as pd

class ProductionRepository:
    """生産関連データアクセス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # 既存
    def get_production_instructions(self, start_date=None, end_date=None) -> pd.DataFrame:
        ...

    # --- 新規追加 ---

    def create_production(self, plan_data: dict) -> bool:
        """生産計画を新規登録"""
        try:
            query = """
            INSERT INTO production_instructions_detail
            (product_id, instruction_date, instruction_quantity, inspection_category)
            VALUES (%s, %s, %s, %s)
            """
            params = (
                plan_data["product_id"],
                plan_data["scheduled_date"],
                plan_data["quantity"],
                plan_data.get("inspection_category", "A")  # デフォルト: "A"
            )
            return self.db.execute_update(query, params)
        except Exception as e:
            print(f"生産計画登録エラー: {e}")
            return False

    def get_productions(self):
        """登録済み生産計画を取得"""
        try:
            query = """
            SELECT 
                pid.id,
                pid.product_id,
                pid.instruction_date AS scheduled_date,
                pid.instruction_quantity AS quantity,
                pid.inspection_category,
                p.product_name
            FROM production_instructions_detail pid
            LEFT JOIN products p ON pid.product_id = p.id
            ORDER BY pid.instruction_date
            """
            return self.db.execute_query(query)
        except Exception as e:
            print(f"生産計画取得エラー: {e}")
            return []

    def update_production(self, plan_id: int, update_data: dict) -> bool:
        """生産計画を更新"""
        try:
            query = """
            UPDATE production_instructions_detail
            SET product_id = %s,
                instruction_date = %s,
                instruction_quantity = %s
            WHERE id = %s
            """
            params = (
                update_data["product_id"],
                update_data["scheduled_date"],
                update_data["quantity"],
                plan_id
            )
            return self.db.execute_update(query, params)
        except Exception as e:
            print(f"生産計画更新エラー: {e}")
            return False

    def delete_production(self, plan_id: int) -> bool:
        """生産計画を削除"""
        try:
            query = "DELETE FROM production_instructions_detail WHERE id = %s"
            return self.db.execute_update(query, (plan_id,))
        except Exception as e:
            print(f"生産計画削除エラー: {e}")
            return False
