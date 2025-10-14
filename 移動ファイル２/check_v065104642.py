import pandas as pd
from datetime import date, timedelta

products = pd.read_csv('products.csv')
trucks = pd.read_csv('truck_master.csv')

p = products[products['product_code']=='V065104642'].iloc[0]
print(f"製品: {p['product_code']}")
print(f"トラック制約: {p['used_truck_ids']}")

truck_ids = [int(x.strip()) for x in str(p['used_truck_ids']).split(',')]

print(f"\nトラック情報:")
for tid in truck_ids:
    t = trucks[trucks['id']==tid].iloc[0]
    print(f"  ID={tid}: {t['name']} 到着日オフセット={t['arrival_day_offset']}日")

print(f"\n納期2025-10-10の場合:")
delivery_date = date(2025, 10, 10)
for tid in truck_ids:
    t = trucks[trucks['id']==tid].iloc[0]
    offset = int(t['arrival_day_offset'])
    loading_date = delivery_date - timedelta(days=offset)
    arrival_date = loading_date + timedelta(days=offset)
    print(f"  トラックID={tid}:")
    print(f"    積載日: {loading_date}")
    print(f"    到着日: {arrival_date}")
    print(f"    納期: {delivery_date}")
    if arrival_date <= delivery_date:
        print(f"    ✅ 間に合う")
    else:
        print(f"    ❌ 納期遅れ！")
