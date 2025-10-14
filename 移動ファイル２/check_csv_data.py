# CSVデータの確認
import pandas as pd
from datetime import date

# CSVから読み込み
csv_orders = pd.read_csv('DELIVERY_PROGRESS.csv')
csv_orders = csv_orders[csv_orders['remaining_quantity'] > 0].copy()
csv_orders['delivery_date'] = pd.to_datetime(csv_orders['delivery_date']).dt.date

# 10/10-10/31のデータ
csv_filtered = csv_orders[
    (csv_orders['delivery_date'] >= date(2025, 10, 10)) &
    (csv_orders['delivery_date'] <= date(2025, 10, 31))
].copy()

# 結果をファイルに出力
with open('csv_data_check.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("CSVデータ確認: DELIVERY_PROGRESS.csv\n")
    f.write("="*80 + "\n\n")
    
    f.write(f"期間: 2025-10-10 ~ 2025-10-31\n")
    f.write(f"総レコード数: {len(csv_filtered)}\n")
    f.write(f"製品種類数: {csv_filtered['product_id'].nunique()}\n")
    f.write(f"総数量: {csv_filtered['remaining_quantity'].sum()}\n\n")
    
    # 製品別集計
    f.write("="*80 + "\n")
    f.write("製品別集計\n")
    f.write("="*80 + "\n\n")
    
    product_summary = csv_filtered.groupby('product_id').agg({
        'remaining_quantity': 'sum',
        'order_id': 'count'
    }).sort_index()
    
    f.write(f"{'製品ID':<10} {'総数量':<15} {'オーダー件数':<15}\n")
    f.write("-"*45 + "\n")
    
    for product_id, row in product_summary.iterrows():
        f.write(f"{product_id:<10} {row['remaining_quantity']:<15} {row['order_id']:<15}\n")
    
    # 日別集計
    f.write("\n" + "="*80 + "\n")
    f.write("日別集計\n")
    f.write("="*80 + "\n\n")
    
    daily_summary = csv_filtered.groupby('delivery_date').agg({
        'remaining_quantity': 'sum',
        'order_id': 'count'
    }).sort_index()
    
    f.write(f"{'日付':<15} {'総数量':<15} {'オーダー件数':<15}\n")
    f.write("-"*50 + "\n")
    
    for dt, row in daily_summary.iterrows():
        f.write(f"{str(dt):<15} {row['remaining_quantity']:<15} {row['order_id']:<15}\n")
    
    # 10/23の詳細
    f.write("\n" + "="*80 + "\n")
    f.write("10/23の詳細データ\n")
    f.write("="*80 + "\n\n")
    
    orders_1023 = csv_filtered[csv_filtered['delivery_date'] == date(2025, 10, 23)]
    
    if not orders_1023.empty:
        f.write(f"件数: {len(orders_1023)}\n\n")
        
        for _, order in orders_1023.iterrows():
            f.write(f"オーダーID: {order['order_id']}\n")
            f.write(f"  製品ID: {order['product_id']}\n")
            f.write(f"  数量: {order['remaining_quantity']}\n")
            f.write(f"  納期: {order['delivery_date']}\n\n")
    else:
        f.write("10/23のデータがありません\n")
    
    f.write("="*80 + "\n")

print("CSVデータ確認完了！")
print(f"総レコード数: {len(csv_filtered)}")
print("詳細はcsv_data_check.txtを確認してください")
