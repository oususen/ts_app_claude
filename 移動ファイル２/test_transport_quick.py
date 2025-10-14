# 簡易テスト
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
trucks_df = pd.read_csv('truck_master.csv')
containers_df = pd.read_csv('container_capacity.csv')
products_df = pd.read_csv('products.csv')
orders_df = pd.read_csv('DELIVERY_PROGRESS.csv')

containers = [SimpleContainer(row) for _, row in containers_df.iterrows()]
calendar = SimpleCalendar()

# 未出荷のみ
orders_df = orders_df[orders_df['remaining_quantity'] > 0].copy()
orders_df['delivery_date'] = pd.to_datetime(orders_df['delivery_date']).dt.date

# テスト範囲
test_orders = orders_df[
    (orders_df['delivery_date'] >= date(2025, 10, 10)) &
    (orders_df['delivery_date'] <= date(2025, 10, 17))
].copy()

print(f"テスト範囲: {len(test_orders)}件")

# 計画作成
planner = TransportPlanner()

try:
    result = planner.calculate_loading_plan_from_orders(
        orders_df=test_orders,
        products_df=products_df,
        containers=containers,
        trucks_df=trucks_df,
        truck_container_rules=[],
        start_date=date(2025, 10, 10),
        days=7,
        calendar_repo=calendar
    )
    
    print("\n=== 計画作成成功 ===")
    print(f"総便数: {result['summary']['total_trips']}便")
    print(f"警告数: {result['summary']['total_warnings']}件")
    
    # 日別表示
    for date_str in sorted(result['daily_plans'].keys()):
        plan = result['daily_plans'][date_str]
        if plan['trucks']:
            print(f"\n{date_str} ({len(plan['trucks'])}便)")
            for truck_plan in plan['trucks']:
                print(f"  {truck_plan['truck_name']} (ID={truck_plan['truck_id']}) 積載率{truck_plan['utilization']['floor_area_rate']}%")
                for item in truck_plan['loaded_items']:
                    truck_ids_str = ','.join(map(str, item.get('truck_ids', [])))
                    loading_date = item.get('loading_date', 'N/A')
                    print(f"    - {item['product_code']}: {item['num_containers']}容器 納期={item['delivery_date']} 積載日={loading_date} (トラック制約:{truck_ids_str})")
        
        if plan['warnings']:
            for warning in plan['warnings']:
                print(f"  警告: {warning}")
    
    # 結果をファイルに保存
    with open('test_result_v2.txt', 'w', encoding='utf-8') as f:
        f.write(f"総便数: {result['summary']['total_trips']}便\n")
        f.write(f"警告数: {result['summary']['total_warnings']}件\n\n")
        
        for date_str in sorted(result['daily_plans'].keys()):
            plan = result['daily_plans'][date_str]
            if plan['trucks']:
                f.write(f"\n{date_str} ({len(plan['trucks'])}便)\n")
                for truck_plan in plan['trucks']:
                    f.write(f"  {truck_plan['truck_name']} (ID={truck_plan['truck_id']}) 積載率{truck_plan['utilization']['floor_area_rate']}%\n")
                    for item in truck_plan['loaded_items']:
                        truck_ids_str = ','.join(map(str, item.get('truck_ids', [])))
                        f.write(f"    - {item['product_code']}: {item['num_containers']}容器 納期={item['delivery_date']} (トラック制約:{truck_ids_str})\n")
            
            if plan['warnings']:
                for warning in plan['warnings']:
                    f.write(f"  警告: {warning}\n")
    
    print("\n結果をtest_result_v2.txtに保存しました")

except Exception as e:
    print(f"\nエラー: {e}")
    import traceback
    print("\n完全なトレースバック:")
    traceback.print_exc()
    print("\n" + "="*80)
