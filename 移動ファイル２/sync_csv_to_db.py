"""
CSVファイルのデータをデータベースに同期するスクリプト

使い方:
    python sync_csv_to_db.py

このスクリプトは:
1. DELIVERY_PROGRESS.csvを読み込み
2. データベースのdelivery_progressテーブルを更新
3. 既存データを削除して新しいデータを挿入
"""

import pandas as pd
from datetime import datetime
import sqlite3

# CSVファイルを読み込み
print("CSVファイルを読み込み中...")
df = pd.read_csv('DELIVERY_PROGRESS.csv')

print(f"読み込んだレコード数: {len(df)}")
print(f"列: {list(df.columns)}")

# データベースに接続
print("\nデータベースに接続中...")
conn = sqlite3.connect('production_planning.db')
cursor = conn.cursor()

# 既存のdelivery_progressテーブルのデータを削除
print("既存データを削除中...")
cursor.execute("DELETE FROM delivery_progress")
conn.commit()

# CSVデータをデータベースに挿入
print("新しいデータを挿入中...")

inserted_count = 0
for _, row in df.iterrows():
    try:
        cursor.execute("""
            INSERT INTO delivery_progress (
                order_id, product_id, order_date, delivery_date,
                order_quantity, planned_quantity, shipped_quantity, remaining_quantity,
                status, customer_code, customer_name, delivery_location, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['order_id'],
            int(row['product_id']),
            row['order_date'],
            row['delivery_date'],
            int(row['order_quantity']),
            int(row.get('planned_quantity', 0)),
            int(row.get('shipped_quantity', 0)),
            int(row['remaining_quantity']),
            row.get('status', '未出荷'),
            row.get('customer_code', ''),
            row.get('customer_name', ''),
            row.get('delivery_location', ''),
            int(row.get('priority', 5))
        ))
        inserted_count += 1
    except Exception as e:
        print(f"エラー (行 {_}): {e}")
        print(f"  データ: {row.to_dict()}")

conn.commit()

# 確認
cursor.execute("SELECT COUNT(*) FROM delivery_progress")
db_count = cursor.fetchone()[0]

print(f"\n同期完了！")
print(f"  挿入したレコード数: {inserted_count}")
print(f"  データベースのレコード数: {db_count}")

# 10/23のデータを確認
cursor.execute("""
    SELECT COUNT(*), SUM(remaining_quantity)
    FROM delivery_progress
    WHERE delivery_date = '2025-10-23'
""")
result = cursor.fetchone()

print(f"\n10/23のデータ確認:")
print(f"  件数: {result[0]}")
print(f"  総数量: {result[1]}")

conn.close()

print("\n✅ データベースとCSVの同期が完了しました")
print("これでStreamlitアプリとシミュレーションが同じデータを使用します")
