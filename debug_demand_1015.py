import pandas as pd
from datetime import date, timedelta

products = pd.read_csv('products.csv')
trucks = pd.read_csv('truck_master.csv')
orders = pd.read_csv('DELIVERY_PROGRESS.csv')

# 未出荷のみ
orders = orders[orders['remaining_quantity'] > 0].copy()
orders['delivery_date'] = pd.to_datetime(orders['delivery_date']).dt.date

# 2025-10-15納期の受注
orders_1015 = orders[orders['delivery_date'] == date(2025, 10, 15)]

print("=== 2025-10-15納期の受注 ===")
for _, order in orders_1015.iterrows():
    product = products[products['id'] == order['product_id']].iloc[0]
    truck_ids_str = product.get('used_truck_ids', '')
    if pd.notna(truck_ids_str):
        truck_ids = [int(x.strip()) for x in str(truck_ids_str).split(',')]
        first_truck = trucks[trucks['id'] == truck_ids[0]].iloc[0]
        offset = int(first_truck['arrival_day_offset'])
    else:
        truck_ids = []
        offset = 0
    
    loading_date = order['delivery_date'] - timedelta(days=offset)
    
    print(f"\n製品: {product['product_code']}")
    print(f"  数量: {order['remaining_quantity']}")
    print(f"  トラック制約: {truck_ids}")
    print(f"  積載日: {loading_date}")

print("\n\n=== 2025-10-15積載日の製品（前倒し含む） ===")
# 2025-10-16納期で前倒し可能な製品
orders_1016 = orders[orders['delivery_date'] == date(2025, 10, 16)]
for _, order in orders_1016.iterrows():
    product = products[products['id'] == order['product_id']].iloc[0]
    truck_ids_str = product.get('used_truck_ids', '')
    if pd.notna(truck_ids_str):
        truck_ids = [int(x.strip()) for x in str(truck_ids_str).split(',')]
        first_truck = trucks[trucks['id'] == truck_ids[0]].iloc[0]
        offset = int(first_truck['arrival_day_offset'])
    else:
        truck_ids = []
        offset = 0
    
    loading_date = order['delivery_date'] - timedelta(days=offset)
    
    if loading_date == date(2025, 10, 15):
        print(f"\n製品: {product['product_code']}")
        print(f"  数量: {order['remaining_quantity']}")
        print(f"  納期: {order['delivery_date']}")
        print(f"  トラック制約: {truck_ids}")
        print(f"  積載日: {loading_date}")
