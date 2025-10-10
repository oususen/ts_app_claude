import pandas as pd

trucks = pd.read_csv('truck_master.csv')
products = pd.read_csv('products.csv')
containers = pd.read_csv('container_capacity.csv')

t = trucks[trucks['id']==10].iloc[0]
floor_area = t['width'] * t['depth']

print(f"トラック: {t['name']}")
print(f"底面積: {floor_area:,} mm²")

print(f"\nV053904703: 23容器")
p = products[products['product_code']=='V053904703'].iloc[0]
c = containers[containers['id']==p['used_container_id']].iloc[0]

container_area = c['width'] * c['depth']
stacked = (23 + c['max_stack'] - 1) // c['max_stack']
needed_area = container_area * stacked

print(f"容器: {c['name']} ({c['width']}x{c['depth']})")
print(f"段積み: {c['max_stack']}段")
print(f"配置数: {stacked}")
print(f"必要底面積: {needed_area:,} mm²")
print(f"積載可能: {needed_area <= floor_area}")
print(f"積載率: {needed_area / floor_area * 100:.1f}%")
