import pandas as pd

products = pd.read_csv('products.csv')
containers = pd.read_csv('container_capacity.csv')
trucks = pd.read_csv('truck_master.csv')

# 2025-10-15のトラックID=3の積載内容
print("=== 2025-10-15 トラックID=3 (NO_2_10T) ===")
t3 = trucks[trucks['id']==3].iloc[0]
t3_area = t3['width'] * t3['depth']
print(f"トラック底面積: {t3_area:,} mm²")

# 積載内容（結果ファイルより）
items = [
    ('V065104703', 18),
    ('V053904703', 3),
]

total_area = 0
print("\n積載内容:")
for product_code, num_containers in items:
    p = products[products['product_code']==product_code].iloc[0]
    c = containers[containers['id']==p['used_container_id']].iloc[0]
    
    container_area = c['width'] * c['depth']
    max_stack = c['max_stack']
    
    # 段積み考慮
    if max_stack > 1:
        stacked = (num_containers + max_stack - 1) // max_stack
        floor_area = container_area * stacked
    else:
        floor_area = container_area * num_containers
    
    total_area += floor_area
    
    print(f"  {product_code}: {num_containers}容器")
    print(f"    容器: {c['name']} ({c['width']}x{c['depth']}) max_stack={max_stack}")
    print(f"    配置数: {stacked if max_stack > 1 else num_containers}")
    print(f"    底面積: {floor_area:,} mm²")

print(f"\n合計底面積: {total_area:,} mm²")
print(f"積載率: {total_area / t3_area * 100:.1f}%")
print(f"空き容量: {t3_area - total_area:,} mm²")

# V065103703の情報
print("\n=== 積み残し V065103703 (1容器) ===")
p = products[products['product_code']=='V065103703'].iloc[0]
c = containers[containers['id']==p['used_container_id']].iloc[0]
container_area = c['width'] * c['depth']

print(f"容器: {c['name']} ({c['width']}x{c['depth']})")
print(f"1容器の底面積: {container_area:,} mm²")
print(f"段積み: max_stack={c['max_stack']}")

free_space = t3_area - total_area
print(f"\n空き容量: {free_space:,} mm²")
print(f"必要容量: {container_area:,} mm²")
print(f"積載可能: {container_area <= free_space}")

if container_area <= free_space:
    print(f"\n✅ 積載可能！空き容量が十分あります")
    print(f"   積載後の積載率: {(total_area + container_area) / t3_area * 100:.1f}%")
