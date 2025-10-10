import pandas as pd
from datetime import date, timedelta

products = pd.read_csv('products.csv')
trucks = pd.read_csv('truck_master.csv')

# V053904703 (product_id=5)
p = products[products['id']==5].iloc[0]
truck_ids = [int(x.strip()) for x in str(p['used_truck_ids']).split(',')]

print(f"製品: {p['product_code']}")
print(f"トラック制約: {truck_ids}")
print(f"第1優先トラック: {truck_ids[0]}")

t = trucks[trucks['id']==truck_ids[0]].iloc[0]
print(f"トラック名: {t['name']}")
print(f"到着日オフセット: {t['arrival_day_offset']}")

delivery = date(2025, 10, 15)
loading = delivery - timedelta(days=int(t['arrival_day_offset']))

print(f"\n納期: {delivery}")
print(f"積載日: {loading}")
print(f"\n結論: 納期2025-10-15の場合、積載日は{loading}になるはず")
