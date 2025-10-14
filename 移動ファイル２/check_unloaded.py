import pandas as pd

products = pd.read_csv('products.csv')
containers = pd.read_csv('container_capacity.csv')
trucks = pd.read_csv('truck_master.csv')

# 積み残しのV065104642
p = products[products['product_code']=='V065104642'].iloc[0]
c = containers[containers['id']==p['used_container_id']].iloc[0]

print(f"=== 積み残し製品: {p['product_code']} ===")
print(f"容器: {c['name']} ({c['width']}x{c['depth']})")
print(f"1容器の底面積: {c['width'] * c['depth']:,} mm²")
print(f"トラック制約: {p['used_truck_ids']}")
print(f"前倒し可能: {'はい' if p['can_advance'] == 1 else 'いいえ'}")

print("\n=== 2025-10-14の積み残し（1容器）===")
# トラックID=3の状態
t3 = trucks[trucks['id']==3].iloc[0]
t3_area = t3['width'] * t3['depth']
print(f"トラックID=3 底面積: {t3_area:,} mm²")
print(f"積載率: 96.4%")
print(f"使用済み: {t3_area * 0.964:,.0f} mm²")
print(f"空き: {t3_area * 0.036:,.0f} mm²")

container_area = c['width'] * c['depth']
print(f"\n1容器の底面積: {container_area:,} mm²")
print(f"積載可能: {container_area <= t3_area * 0.036}")

print("\n=== 前倒しで解決できるか？ ===")
print("2025-10-14の積み残し1容器を2025-10-10に前倒し:")
print(f"  2025-10-10のトラックID=3: 積載率87.7%")
print(f"  空き容量: {t3_area * 0.123:,.0f} mm²")
print(f"  1容器積載可能: {container_area <= t3_area * 0.123}")

print("\n2025-10-15の積み残し4容器を前日に前倒し:")
print(f"  2025-10-14のトラックID=3: 積載率96.4% → 空き不足")
print(f"  2025-10-10に4容器前倒し:")
print(f"    空き容量: {t3_area * 0.123:,.0f} mm²")
print(f"    4容器の底面積: {container_area * 4:,} mm²")
print(f"    積載可能: {container_area * 4 <= t3_area * 0.123}")
