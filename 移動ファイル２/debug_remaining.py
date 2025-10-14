import pandas as pd

products = pd.read_csv('products.csv')
containers = pd.read_csv('container_capacity.csv')
trucks = pd.read_csv('truck_master.csv')

# V065103703
p = products[products['product_code']=='V065103703'].iloc[0]
c = containers[containers['id']==p['used_container_id']].iloc[0]

print(f"製品: {p['product_code']}")
print(f"容器: {c['name']} ({c['width']}x{c['depth']})")
print(f"トラック制約: {p['used_truck_ids']}")
print(f"1容器の底面積: {c['width'] * c['depth']:,} mm²")

print("\n2025-10-15のトラック空き容量:")
# NO_2_10T: 95.2%使用 → 4.8%空き
t3 = trucks[trucks['id']==3].iloc[0]
t3_area = t3['width'] * t3['depth']
t3_used = t3_area * 0.952
t3_free = t3_area - t3_used
print(f"  NO_2_10T (ID=3): {t3_free:,.0f} mm² 空き")

# NO_4_10T: 93.7%使用 → 6.3%空き
t10 = trucks[trucks['id']==10].iloc[0]
t10_area = t10['width'] * t10['depth']
t10_used = t10_area * 0.937
t10_free = t10_area - t10_used
print(f"  NO_4_10T (ID=10): {t10_free:,.0f} mm² 空き")

# NO_3_10T: 77.1%使用 → 22.9%空き
t11 = trucks[trucks['id']==11].iloc[0]
t11_area = t11['width'] * t11['depth']
t11_used = t11_area * 0.771
t11_free = t11_area - t11_used
print(f"  NO_3_10T (ID=11): {t11_free:,.0f} mm² 空き")

container_area = c['width'] * c['depth']
print(f"\n1容器の底面積: {container_area:,} mm²")
print(f"トラックID=3に積載可能: {container_area <= t3_free}")
print(f"トラックID=10に積載可能: {container_area <= t10_free}")
