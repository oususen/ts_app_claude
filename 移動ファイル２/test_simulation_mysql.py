# 10/10から10/31までのシミュレーション（MySQL版）
import pandas as pd
from datetime import date
import sys
sys.path.insert(0, 'd:/ts_app_claude')

from domain.calculators.transport_planner import TransportPlanner
from repository.database_manager import DatabaseManager
from repository.delivery_progress_repository import DeliveryProgressRepository
from repository.transport_repository import TransportRepository
from repository.product_repository import ProductRepository
from repository.calendar_repository import CalendarRepository

# 容器は既にSimpleNamespace形式で返されるので変換不要

print("="*80)
print("MySQLデータベースからシミュレーション実行")
print("="*80)

# データベース接続
print("\nデータベースに接続中...")
db = DatabaseManager()

# リポジトリ初期化
delivery_repo = DeliveryProgressRepository(db)
transport_repo = TransportRepository(db)
product_repo = ProductRepository(db)
calendar_repo = CalendarRepository(db)

# データ読み込み
print("データ読み込み中...")

# トラックマスタ
trucks_df = transport_repo.get_trucks()
print(f"  トラック: {len(trucks_df)}件")

# 容器マスタ（既にSimpleNamespace形式のリスト）
containers = transport_repo.get_containers()
print(f"  容器: {len(containers)}件")

# 製品マスタ
products_df = product_repo.get_all_products()
print(f"  製品: {len(products_df)}件")

# 納入進度（10/10-10/31）
orders_df = delivery_repo.get_delivery_progress(
    start_date=date(2025, 10, 10),
    end_date=date(2025, 10, 31)
)
print(f"  納入進度: {len(orders_df)}件")

# 未出荷のみ
if not orders_df.empty:
    orders_df = orders_df[orders_df['remaining_quantity'] > 0].copy()
    print(f"  未出荷: {len(orders_df)}件")

print(f"\nテスト範囲: 2025/10/10 - 2025/10/31")
print(f"対象オーダー: {len(orders_df)}件")

if orders_df.empty:
    print("\n⚠️ データがありません！")
    print("Streamlitアプリの「CSV受注取込」でデータをインポートしてください")
    db.close()
    sys.exit(1)

# 計画作成
planner = TransportPlanner()

try:
    result = planner.calculate_loading_plan_from_orders(
        orders_df=orders_df,
        products_df=products_df,
        containers=containers,
        trucks_df=trucks_df,
        truck_container_rules=[],
        start_date=date(2025, 10, 10),
        days=22,  # 10/10から10/31まで（営業日ベース）
        calendar_repo=calendar_repo
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
                    is_advanced = item.get('is_advanced', False)
                    advanced_mark = "⏩前倒し" if is_advanced else ""
                    
                    print(f"    - {item['product_code']}: {item['num_containers']}容器 {advanced_mark}")
                    print(f"      納期={item.get('delivery_date', 'N/A')}, 積載日={item.get('loading_date', 'N/A')}")
        
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
    with open('simulation_mysql_result.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("10/10-10/31 積載計画シミュレーション結果（MySQL版）\n")
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
                        is_advanced = item.get('is_advanced', False)
                        advanced_mark = "[前倒し]" if is_advanced else ""
                        
                        f.write(f"    - {item['product_code']}: {item['num_containers']}容器 {advanced_mark}\n")
                        f.write(f"      納期={item.get('delivery_date')}, 積載日={item.get('loading_date')}\n")
            
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
    
    print("\n✅ 結果をsimulation_mysql_result.txtに保存しました")

except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    print("\n完全なトレースバック:")
    traceback.print_exc()
    print("\n" + "="*80)

finally:
    # データベース接続を閉じる
    db.close()
    print("\nデータベース接続を閉じました")
