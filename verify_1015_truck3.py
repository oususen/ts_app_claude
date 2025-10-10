import pandas as pd

containers = pd.read_csv('container_capacity.csv')
trucks = pd.read_csv('truck_master.csv')

t3 = trucks[trucks['id']==3].iloc[0]
truck_area = t3['width'] * t3['depth']

print(f"=== トラックID=3 (NO_2_10T) ===")
print(f"底面積: {truck_area:,} mm²\n")

# 積載内容
items = [
    ('V065104703', 18, 1),  # product_code, num_containers, container_id
    ('V053904703', 3, 1),
    ('V065103703', 1, 1),
]

print("積載内容:")
total_area = 0
for product_code, num_containers, container_id in items:
    c = containers[containers['id']==container_id].iloc[0]
    container_area = c['width'] * c['depth']
    max_stack = c['max_stack']
    
    stacked = (num_containers + max_stack - 1) // max_stack
    floor_area = container_area * stacked
    total_area += floor_area
    
    print(f"  {product_code}: {num_containers}容器 → {stacked}配置 → {floor_area:,} mm²")

print(f"\n合計底面積: {total_area:,} mm²")
print(f"積載率: {total_area / truck_area * 100:.1f}%")

print("\n=== 段積み統合の正しい計算 ===")
c = containers[containers['id']==1].iloc[0]
container_area = c['width'] * c['depth']
max_stack = c['max_stack']

# 全容器を合計
total_containers = 18 + 3 + 1
total_stacks = (total_containers + max_stack - 1) // max_stack
correct_area = container_area * total_stacks

print(f"全容器数: {total_containers}")
print(f"配置数: {total_stacks}")
print(f"底面積: {correct_area:,} mm²")
print(f"積載率: {correct_area / truck_area * 100:.1f}%")
