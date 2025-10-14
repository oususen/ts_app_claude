"""
積み残し原因の分析
"""
import pandas as pd

# データ読み込み
orders = pd.read_csv('delivery_progress.csv')
trucks = pd.read_csv('truck_master.csv')
products = pd.read_csv('products.csv')
containers = pd.read_csv('container_capacity.csv')

print("=" * 80)
print("2025-10-14の積み残し分析")
print("=" * 80)

# 2025-10-14の納期データ
orders_1014 = orders[orders['delivery_date'] == '2025-10-14']
print(f"\n2025-10-14納期の製品:")
for _, row in orders_1014.iterrows():
    p = products[products['id'] == row['product_id']].iloc[0]
    print(f"  {p['product_code']}: {row['remaining_quantity']}個 (トラック制約: {p['used_truck_ids']})")

# トラック容量
print(f"\n使用可能なトラック（デフォルト）:")
default_trucks = trucks[trucks['default_use'] == 1]
total_area = 0
for _, t in default_trucks.iterrows():
    area = t['width'] * t['depth']
    total_area += area
    print(f"  {t['name']} (ID={t['id']}): {area:,} mm² (到着オフセット={t['arrival_day_offset']}日)")
print(f"  合計: {total_area:,} mm²")

# 2025-10-14に必要な容量
print(f"\n2025-10-14に積載が必要な製品:")
total_needed = 0
for _, row in orders_1014.iterrows():
    p = products[products['id'] == row['product_id']].iloc[0]
    c = containers[containers['id'] == p['used_container_id']].iloc[0]
    
    capacity = p['capacity']
    num_containers = row['remaining_quantity'] // capacity
    if row['remaining_quantity'] % capacity > 0:
        num_containers += 1
    
    area_per_container = c['width'] * c['depth']
    
    # 段積み考慮
    if c['stackable'] == 1 and c['max_stack'] > 1:
        stacks = (num_containers + c['max_stack'] - 1) // c['max_stack']
        total_area_needed = area_per_container * stacks
    else:
        total_area_needed = area_per_container * num_containers
    
    total_needed += total_area_needed
    print(f"  {p['product_code']}: {num_containers}容器 × {area_per_container:,} mm² = {total_area_needed:,} mm²")

print(f"\n合計必要容量: {total_needed:,} mm²")
print(f"利用可能容量: {total_area:,} mm²")
print(f"超過: {total_needed - total_area:,} mm² ({(total_needed / total_area - 1) * 100:.1f}%)")

print("\n" + "=" * 80)
print("解決策")
print("=" * 80)
print("1. 非デフォルトトラックを追加する")
print("2. 前倒し可能な製品を前日に移動する")
print("3. 複数日に分散する")
