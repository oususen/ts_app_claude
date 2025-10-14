# 10/10から10/31までのシミュレーション
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
print(f"納期の範囲: {test_orders['delivery_date'].min()} - {test_orders['delivery_date'].max()}")

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
        days=22,  # 10/10から10/31まで（営業日ベース）
        calendar_repo=calendar
    )
    
    print("\n" + "="*80)
    print("=== 計画作成成功 ===")
    print("="*80)
    print(f"総便数: {result['summary']['total_trips']}便")
    print(f"警告数: {result['summary']['total_warnings']}件")
    print(f"非デフォルトトラック使用: {result.get('use_non_default_truck', False)}")
    
    # 積み残しカウント
    total_unloaded = 0
    unloaded_details = []
    
    # 日別表示
    print("\n" + "="*80)
    print("=== 日別計画 ===")
    print("="*80)
    
    for date_str in sorted(result['daily_plans'].keys()):
        plan = result['daily_plans'][date_str]
        
        if plan['trucks']:
            print(f"\n📅 {date_str} ({len(plan['trucks'])}便)")
            for truck_plan in plan['trucks']:
                print(f"  🚛 {truck_plan['truck_name']} (ID={truck_plan['truck_id']}) 積載率{truck_plan['utilization']['floor_area_rate']}%")
                for item in truck_plan['loaded_items']:
                    truck_ids_str = ','.join(map(str, item.get('truck_ids', [])))
                    loading_date = item.get('loading_date', 'N/A')
                    delivery_date = item.get('delivery_date', 'N/A')
                    is_advanced = item.get('is_advanced', False)
                    advanced_mark = "⏩前倒し" if is_advanced else ""
                    
                    # truck_loading_datesを表示
                    truck_loading_dates = item.get('truck_loading_dates', {})
                    tld_str = ', '.join([f"T{tid}:{dt}" for tid, dt in truck_loading_dates.items()])
                    
                    print(f"    - {item['product_code']}: {item['num_containers']}容器 {advanced_mark}")
                    print(f"      納期={delivery_date}, 積載日={loading_date}")
                    print(f"      トラック制約:[{truck_ids_str}], 各トラック積載日:[{tld_str}]")
        
        if plan['warnings']:
            print(f"\n  ⚠️ 警告:")
            for warning in plan['warnings']:
                print(f"    {warning}")
                if "積み残し" in warning:
                    total_unloaded += 1
                    unloaded_details.append(f"{date_str}: {warning}")
    
    # サマリー
    print("\n" + "="*80)
    print("=== サマリー ===")
    print("="*80)
    print(f"計画期間: {result['period']}")
    print(f"総便数: {result['summary']['total_trips']}便")
    print(f"警告数: {result['summary']['total_warnings']}件")
    print(f"積み残し件数: {total_unloaded}件")
    
    if unloaded_details:
        print("\n📋 積み残し詳細:")
        for detail in unloaded_details:
            print(f"  - {detail}")
    
    # 結果をファイルに保存
    with open('simulation_1010_1031_result.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("10/10-10/31 積載計画シミュレーション結果\n")
        f.write("="*80 + "\n\n")
        f.write(f"計画期間: {result['period']}\n")
        f.write(f"総便数: {result['summary']['total_trips']}便\n")
        f.write(f"警告数: {result['summary']['total_warnings']}件\n")
        f.write(f"積み残し件数: {total_unloaded}件\n\n")
        
        for date_str in sorted(result['daily_plans'].keys()):
            plan = result['daily_plans'][date_str]
            if plan['trucks']:
                f.write(f"\n{date_str} ({len(plan['trucks'])}便)\n")
                f.write("-"*60 + "\n")
                for truck_plan in plan['trucks']:
                    f.write(f"  {truck_plan['truck_name']} (ID={truck_plan['truck_id']}) 積載率{truck_plan['utilization']['floor_area_rate']}%\n")
                    for item in truck_plan['loaded_items']:
                        truck_ids_str = ','.join(map(str, item.get('truck_ids', [])))
                        is_advanced = item.get('is_advanced', False)
                        advanced_mark = "[前倒し]" if is_advanced else ""
                        
                        truck_loading_dates = item.get('truck_loading_dates', {})
                        tld_str = ', '.join([f"T{tid}:{dt}" for tid, dt in truck_loading_dates.items()])
                        
                        f.write(f"    - {item['product_code']}: {item['num_containers']}容器 {advanced_mark}\n")
                        f.write(f"      納期={item['delivery_date']}, 積載日={item.get('loading_date')}\n")
                        f.write(f"      トラック制約:[{truck_ids_str}], 各トラック積載日:[{tld_str}]\n")
            
            if plan['warnings']:
                f.write(f"\n  警告:\n")
                for warning in plan['warnings']:
                    f.write(f"    {warning}\n")
        
        if unloaded_details:
            f.write("\n" + "="*80 + "\n")
            f.write("積み残し詳細\n")
            f.write("="*80 + "\n")
            for detail in unloaded_details:
                f.write(f"  - {detail}\n")
    
    print("\n✅ 結果をsimulation_1010_1031_result.txtに保存しました")

except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    print("\n完全なトレースバック:")
    traceback.print_exc()
    print("\n" + "="*80)
