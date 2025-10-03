# test_orders.py
from repository.database_manager import DatabaseManager
from repository.production_repository import ProductionRepository
from datetime import date

def test_orders():
    db = DatabaseManager()
    repo = ProductionRepository(db)
    
    # テスト期間: 2025-10-06 〜 2025-10-12
    start_date = date(2025, 10, 6)
    end_date = date(2025, 10, 12)
    
    orders_df = repo.get_production_instructions(start_date, end_date)
    
    print(f"📊 テスト結果:")
    print(f"  - DataFrameタイプ: {type(orders_df)}")
    print(f"  - データ件数: {len(orders_df)}")
    print(f"  - カラム: {list(orders_df.columns) if not orders_df.empty else '空'}")
    
    if not orders_df.empty:
        print(f"  - サンプルデータ:")
        print(orders_df.head())

if __name__ == "__main__":
    test_orders()
