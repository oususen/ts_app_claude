# 新しいTransportPlannerのテスト
import pandas as pd
from datetime import date
import sys
import io
sys.path.insert(0, 'd:/ts_app_claude')

from domain.calculators.transport_planner import TransportPlanner

# 出力をファイルに保存
output = io.StringIO()

def log(msg):
    print(msg)
    output.write(msg + '\n')

# データ読み込み
log("=" * 80)
log("TransportPlanner テスト開始")
log("=" * 80)

# 1. トラックマスタ
trucks_df = pd.read_csv('truck_master.csv')
print(f"\n【トラックマスタ】")
print(f"  件数: {len(trucks_df)}件")
print(trucks_df[['id', 'name', 'width', 'depth', 'default_use', 'arrival_day_offset', 'priority_product_codes']])

# 2. 容器マスタ
containers_df = pd.read_csv('container_capacity.csv')
print(f"\n【容器マスタ】")
print(f"  件数: {len(containers_df)}件")
print(containers_df[['id', 'name', 'width', 'depth', 'height']])

# Container オブジェクトに変換（簡易クラス）
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

containers = [SimpleContainer(row) for _, row in containers_df.iterrows()]

# 3. 製品マスタ
products_df = pd.read_csv('products.csv')
print(f"\n【製品マスタ】")
print(f"  件数: {len(products_df)}件")
print(products_df[['id', 'product_code', 'product_name', 'capacity', 'used_container_id', 'used_truck_ids']])

# 4. 受注データ（10/10-10/17の範囲）
orders_df = pd.read_csv('DELIVERY_PROGRESS.csv')
# 未出荷のみ
orders_df = orders_df[orders_df['remaining_quantity'] > 0].copy()
# 日付フィルタ
orders_df['delivery_date'] = pd.to_datetime(orders_df['delivery_date']).dt.date
test_orders = orders_df[
    (orders_df['delivery_date'] >= date(2025, 10, 10)) &
    (orders_df['delivery_date'] <= date(2025, 10, 17))
].copy()

print(f"\n【受注データ】")
print(f"  全体: {len(orders_df)}件")
print(f"  テスト範囲(10/10-10/17): {len(test_orders)}件")

# 日別集計
daily_summary = test_orders.groupby('delivery_date').agg({
    'remaining_quantity': 'sum',
    'product_id': 'count'
}).rename(columns={'remaining_quantity': '数量', 'product_id': '件数'})
print("\n  日別サマリー:")
print(daily_summary)

# 5. カレンダー（簡易版）
class SimpleCalendar:
    def __init__(self):
        cal_df = pd.read_csv('CALENDER.csv')
        cal_df['calendar_date'] = pd.to_datetime(cal_df['calendar_date']).dt.date
        self.working_days = set(cal_df[cal_df['is_working_day'] == 1]['calendar_date'])
    
    def is_working_day(self, check_date):
        return check_date in self.working_days

calendar = SimpleCalendar()

# 6. TransportPlanner実行
print("\n" + "=" * 80)
print("📊 積載計画作成開始")
print("=" * 80)

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
    
    print("\n✅ 計画作成成功")
    
    # サマリー表示
    print(f"\n【サマリー】")
    summary = result['summary']
    print(f"  計画期間: {result['period']}")
    print(f"  営業日数: {summary['total_days']}日")
    print(f"  総便数: {summary['total_trips']}便")
    print(f"  警告数: {summary['total_warnings']}件")
    print(f"  非デフォルトトラック使用: {summary.get('use_non_default_truck', False)}")
    print(f"  ステータス: {summary['status']}")
    
    # 日別計画表示
    print(f"\n【日別計画】")
    for date_str in sorted(result['daily_plans'].keys()):
        plan = result['daily_plans'][date_str]
        print(f"\n📅 {date_str} ({len(plan['trucks'])}便)")
        
        if not plan['trucks']:
            print("  (積載なし)")
            continue
        
        for i, truck_plan in enumerate(plan['trucks'], 1):
            print(f"\n  🚚 便{i}: {truck_plan['truck_name']} (ID={truck_plan['truck_id']})")
            print(f"     積載率: 底面積{truck_plan['utilization']['floor_area_rate']}%")
            
            if truck_plan['loaded_items']:
                print(f"     積載製品:")
                for item in truck_plan['loaded_items']:
                    print(f"       - {item['product_code']}: {item['num_containers']}容器 "
                          f"({item['total_quantity']}個) 納期={item['delivery_date']}")
        
        if plan['warnings']:
            print(f"\n  ⚠️ 警告:")
            for warning in plan['warnings']:
                print(f"     {warning}")
    
    # 底面積分析
    print(f"\n【底面積分析（段積み考慮）】")
    for date_str in sorted(result['daily_plans'].keys()):
        plan = result['daily_plans'][date_str]
        if plan['trucks']:
            total_floor_area = 0
            for truck_plan in plan['trucks']:
                truck = trucks_df[trucks_df['id'] == truck_plan['truck_id']].iloc[0]
                truck_floor_area = truck['width'] * truck['depth']
                
                loaded_area = 0
                for item in truck_plan['loaded_items']:
                    # 段積み考慮
                    if item.get('stackable', False) and item.get('max_stack', 1) > 1:
                        stacked_containers = (item['num_containers'] + item['max_stack'] - 1) // item['max_stack']
                        item_area = item['floor_area_per_container'] * stacked_containers
                    else:
                        item_area = item['floor_area_per_container'] * item['num_containers']
                    loaded_area += item_area
                
                total_floor_area += loaded_area
                
                print(f"\n  {date_str} - {truck_plan['truck_name']}:")
                print(f"    トラック底面積: {truck_floor_area:,} mm²")
                print(f"    積載底面積: {loaded_area:,} mm²")
                print(f"    積載率: {loaded_area / truck_floor_area * 100:.1f}%")
                
                # 段積み詳細
                for item in truck_plan['loaded_items']:
                    if item.get('stackable', False) and item.get('max_stack', 1) > 1:
                        stacked = (item['num_containers'] + item['max_stack'] - 1) // item['max_stack']
                        print(f"      - {item['product_code']}: {item['num_containers']}容器 → {stacked}配置（{item['max_stack']}段積み）")

except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ テスト完了")
print("=" * 80)
