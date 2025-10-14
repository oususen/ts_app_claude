# 前倒し配送の検証
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

# 前倒し配送を検証
with open('verify_advanced_result.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("前倒し配送の検証\n")
    f.write("="*80 + "\n\n")
    
    advanced_count = 0
    total_items = 0
    
    for date_str in sorted(result['daily_plans'].keys()):
        plan = result['daily_plans'][date_str]
        
        for truck in plan.get('trucks', []):
            for item in truck.get('loaded_items', []):
                total_items += 1
                is_advanced = item.get('is_advanced', False)
                
                if is_advanced:
                    advanced_count += 1
                    loading_date = item.get('loading_date')
                    delivery_date = item.get('delivery_date')
                    
                    f.write(f"[前倒し] {date_str} - {item['product_code']}\n")
                    f.write(f"  積載日: {loading_date}, 納期: {delivery_date}\n")
                    f.write(f"  トラック: {truck['truck_name']}\n")
                    f.write(f"  容器数: {item['num_containers']}\n\n")
    
    f.write("="*80 + "\n")
    f.write(f"サマリー:\n")
    f.write(f"  総アイテム数: {total_items}\n")
    f.write(f"  前倒しアイテム数: {advanced_count}\n")
    f.write(f"  前倒し率: {advanced_count/total_items*100:.1f}%\n")
    f.write("="*80 + "\n")

print(f"検証完了: 総アイテム数={total_items}, 前倒し={advanced_count}")
print("結果をverify_advanced_result.txtに出力しました")
