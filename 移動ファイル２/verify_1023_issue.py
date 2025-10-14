# 10/23のトラック使用状況を検証
import pandas as pd
from datetime import date
import sys
sys.path.insert(0, 'd:/ts_app_claude')

from domain.calculators.transport_planner import TransportPlanner

# 容器クラス
class SimpleContainer:
    def __init__(self, row):
        self.id = int(row['id'])
        self.name = row['name']
        self.width = int(row['width'])
        self.depth = int(row['depth'])
        self.height = int(row['height'])
        self.max_weight = int(row['max_weight'])
        self.stackable = bool(row['stackable'])
        self.max_stack = int(row['max_stack'])

# カレンダー
class SimpleCalendar:
    def __init__(self):
        cal_df = pd.read_csv('CALENDER.csv')
        cal_df['calendar_date'] = pd.to_datetime(cal_df['calendar_date']).dt.date
        self.working_days = set(cal_df[cal_df['is_working_day'] == 1]['calendar_date'])
    
    def is_working_day(self, check_date):
        return check_date in self.working_days

# データ読み込み
print("データ読み込み中...")
trucks_df = pd.read_csv('truck_master.csv')
containers_df = pd.read_csv('container_capacity.csv')
products_df = pd.read_csv('products.csv')
orders_df = pd.read_csv('DELIVERY_PROGRESS.csv')

containers = [SimpleContainer(row) for _, row in containers_df.iterrows()]
calendar = SimpleCalendar()

# 未出荷のみ
orders_df = orders_df[orders_df['remaining_quantity'] > 0].copy()
orders_df['delivery_date'] = pd.to_datetime(orders_df['delivery_date']).dt.date

# 10/10から10/31までのオーダーを抽出
test_orders = orders_df[
    (orders_df['delivery_date'] >= date(2025, 10, 10)) &
    (orders_df['delivery_date'] <= date(2025, 10, 31))
].copy()

print(f"対象オーダー: {len(test_orders)}件")

# 計画作成
planner = TransportPlanner()

result = planner.calculate_loading_plan_from_orders(
    orders_df=test_orders,
    products_df=products_df,
    containers=containers,
    trucks_df=trucks_df,
    truck_container_rules=[],
    start_date=date(2025, 10, 10),
    days=22,
    calendar_repo=calendar
)

# 10/23の計画を確認
date_1023 = '2025-10-23'

# ファイルに出力
with open('verify_1023_result.txt', 'w', encoding='utf-8') as f:
    if date_1023 in result['daily_plans']:
        plan_1023 = result['daily_plans'][date_1023]
        
        f.write("\n" + "="*80 + "\n")
        f.write("=== 2025-10-23の積載計画 ===\n")
        f.write("="*80 + "\n")
        f.write(f"便数: {len(plan_1023['trucks'])}便\n")
        
        for truck_plan in plan_1023['trucks']:
            truck_id = truck_plan['truck_id']
            truck_name = truck_plan['truck_name']
            utilization = truck_plan['utilization']['floor_area_rate']
            
            f.write(f"\nトラック: {truck_name} (ID={truck_id}) 積載率{utilization}%\n")
            
            for item in truck_plan['loaded_items']:
                product_code = item['product_code']
                num_containers = item['num_containers']
                delivery_date = item['delivery_date']
                is_advanced = item.get('is_advanced', False)
                advanced_mark = "[前倒し]" if is_advanced else ""
                
                f.write(f"  - {product_code}: {num_containers}容器 {advanced_mark}\n")
                f.write(f"    納期={delivery_date}\n")
        
        if plan_1023['warnings']:
            f.write(f"\n警告:\n")
            for warning in plan_1023['warnings']:
                f.write(f"  {warning}\n")
        
        # トラックID=10が使われているか確認
        truck_ids_used = [t['truck_id'] for t in plan_1023['trucks']]
        f.write(f"\n使用されたトラックID: {truck_ids_used}\n")
        
        if 10 not in truck_ids_used:
            f.write(f"\n問題: トラックID=10 (NO_4_10T)が使われていません！\n")
            
            # 10/23納期の製品を確認
            f.write(f"\n10/23納期の製品を確認:\n")
            orders_1023 = test_orders[test_orders['delivery_date'] == date(2025, 10, 23)]
            for _, order in orders_1023.iterrows():
                product_id = int(order['product_id'])
                product = products_df[products_df['id'] == product_id].iloc[0]
                f.write(f"  - {product['product_code']}: {order['order_quantity']}個\n")
                f.write(f"    used_truck_ids: {product.get('used_truck_ids', 'なし')}\n")
        else:
            f.write(f"\nOK: トラックID=10 (NO_4_10T)は使われています\n")
    else:
        f.write(f"エラー: 2025-10-23の計画が見つかりません\n")
    
    f.write("\n" + "="*80 + "\n")

print("結果をverify_1023_result.txtに出力しました")
