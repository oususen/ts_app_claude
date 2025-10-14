# データソースの比較
import pandas as pd
from datetime import date
import sys
sys.path.insert(0, 'd:/ts_app_claude')

from repository.database_manager import DatabaseManager
from repository.delivery_progress_repository import DeliveryProgressRepository

# CSVから読み込み
csv_orders = pd.read_csv('DELIVERY_PROGRESS.csv')
csv_orders = csv_orders[csv_orders['remaining_quantity'] > 0].copy()
csv_orders['delivery_date'] = pd.to_datetime(csv_orders['delivery_date']).dt.date

# 10/10-10/31のデータ
csv_filtered = csv_orders[
    (csv_orders['delivery_date'] >= date(2025, 10, 10)) &
    (csv_orders['delivery_date'] <= date(2025, 10, 31))
].copy()

# DBから読み込み
db = DatabaseManager()
repo = DeliveryProgressRepository(db)
db_orders = repo.get_delivery_progress(
    start_date=date(2025, 10, 10),
    end_date=date(2025, 10, 31)
)

# 比較結果をファイルに出力
with open('data_source_comparison.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("データソース比較: CSV vs データベース\n")
    f.write("="*80 + "\n\n")
    
    f.write(f"【CSVファイル】DELIVERY_PROGRESS.csv\n")
    f.write(f"  期間: 2025-10-10 ~ 2025-10-31\n")
    f.write(f"  総レコード数: {len(csv_filtered)}\n")
    f.write(f"  製品種類数: {csv_filtered['product_id'].nunique()}\n")
    f.write(f"  総数量: {csv_filtered['remaining_quantity'].sum()}\n\n")
    
    f.write(f"【データベース】delivery_progress テーブル\n")
    f.write(f"  期間: 2025-10-10 ~ 2025-10-31\n")
    f.write(f"  総レコード数: {len(db_orders)}\n")
    if not db_orders.empty:
        f.write(f"  製品種類数: {db_orders['product_id'].nunique()}\n")
        f.write(f"  総数量: {db_orders['remaining_quantity'].sum()}\n\n")
    else:
        f.write(f"  ⚠️ データが空です！\n\n")
    
    f.write("="*80 + "\n")
    f.write("詳細比較\n")
    f.write("="*80 + "\n\n")
    
    # 製品別の比較
    f.write("【製品別の数量比較】\n\n")
    
    if not db_orders.empty:
        csv_summary = csv_filtered.groupby('product_id')['remaining_quantity'].sum().sort_index()
        db_summary = db_orders.groupby('product_id')['remaining_quantity'].sum().sort_index()
        
        all_products = sorted(set(csv_summary.index) | set(db_summary.index))
        
        f.write(f"{'製品ID':<10} {'CSV数量':<15} {'DB数量':<15} {'差分':<15}\n")
        f.write("-"*60 + "\n")
        
        for product_id in all_products:
            csv_qty = csv_summary.get(product_id, 0)
            db_qty = db_summary.get(product_id, 0)
            diff = csv_qty - db_qty
            
            diff_mark = ""
            if diff != 0:
                diff_mark = " ⚠️"
            
            f.write(f"{product_id:<10} {csv_qty:<15} {db_qty:<15} {diff:<15}{diff_mark}\n")
    else:
        f.write("⚠️ データベースにデータがありません\n")
        f.write("\nCSVの製品一覧:\n")
        csv_summary = csv_filtered.groupby('product_id')['remaining_quantity'].sum().sort_index()
        for product_id, qty in csv_summary.items():
            f.write(f"  製品ID {product_id}: {qty}個\n")
    
    f.write("\n" + "="*80 + "\n")
    
    # 日別の比較
    f.write("\n【日別の件数比較】\n\n")
    
    if not db_orders.empty:
        csv_daily = csv_filtered.groupby('delivery_date').size().sort_index()
        db_daily = db_orders.groupby('delivery_date').size().sort_index()
        
        all_dates = sorted(set(csv_daily.index) | set(db_daily.index))
        
        f.write(f"{'日付':<15} {'CSV件数':<10} {'DB件数':<10} {'差分':<10}\n")
        f.write("-"*50 + "\n")
        
        for dt in all_dates:
            csv_count = csv_daily.get(dt, 0)
            db_count = db_daily.get(dt, 0)
            diff = csv_count - db_count
            
            diff_mark = ""
            if diff != 0:
                diff_mark = " ⚠️"
            
            f.write(f"{str(dt):<15} {csv_count:<10} {db_count:<10} {diff:<10}{diff_mark}\n")
    
    f.write("\n" + "="*80 + "\n")

db.close()

print("比較完了！")
print(f"CSV: {len(csv_filtered)}件")
print(f"DB: {len(db_orders)}件")
print("\n詳細はdata_source_comparison.txtを確認してください")
