# アプリと同じ方法で積載計画を作成（CSVから直接）
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

print(f"テスト範囲: 2025/10/10 - 2025/10/31")
print(f"対象オーダー: {len(test_orders)}件")

# 計画作成
planner = TransportPlanner()

print("積載計画を作成中...")
try:
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
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("計画結果")
print("="*80)
print(f"計画期間: {result['period']}")
print(f"総便数: {result['summary']['total_trips']}便")
print(f"警告数: {result['summary']['total_warnings']}件")

# 積み残しをカウント
total_unloaded = 0
unloaded_details = []

for date_str in sorted(result['daily_plans'].keys()):
    plan = result['daily_plans'][date_str]
    
    if plan['warnings']:
        for warning in plan['warnings']:
            if "積み残し" in warning:
                total_unloaded += 1
                unloaded_details.append(f"{date_str}: {warning}")

print(f"積み残し件数: {total_unloaded}件\n")

if unloaded_details:
    print("積み残し詳細:")
    for detail in unloaded_details:
        print(f"  {detail}")

# 詳細をファイルに保存
with open('app_simulation_result.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("アプリシミュレーション結果\n")
    f.write("="*80 + "\n\n")
    f.write(f"計画期間: {result['period']}\n")
    f.write(f"総便数: {result['summary']['total_trips']}便\n")
    f.write(f"警告数: {result['summary']['total_warnings']}件\n")
    f.write(f"積み残し件数: {total_unloaded}件\n\n")
    
    for date_str in sorted(result['daily_plans'].keys()):
        plan = result['daily_plans'][date_str]
        if plan['trucks'] or plan['warnings']:
            f.write(f"\n{date_str}\n")
            f.write("-"*60 + "\n")
            
            for truck_plan in plan['trucks']:
                f.write(f"  {truck_plan['truck_name']} (ID={truck_plan['truck_id']}) 積載率{truck_plan['utilization']['floor_area_rate']}%\n")
                for item in truck_plan['loaded_items']:
                    is_advanced = item.get('is_advanced', False)
                    can_advance = item.get('can_advance', False)
                    advanced_mark = "[前倒し]" if is_advanced else ""
                    f.write(f"    - {item['product_code']}: {item['num_containers']}容器 {advanced_mark}\n")
                    f.write(f"      納期={item['delivery_date']}, can_advance={can_advance}\n")
            
            if plan['warnings']:
                f.write(f"\n  警告:\n")
                for warning in plan['warnings']:
                    f.write(f"    {warning}\n")

print("\n✅ 結果をapp_simulation_result.txtに保存しました")
