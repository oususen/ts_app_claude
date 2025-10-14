import traceback
from domain.calculators.transport_planner import TransportPlanner
from infrastructure.repositories.csv_repository import CSVRepository
from datetime import date, timedelta

try:
    # リポジトリ初期化
    csv_repo = CSVRepository()
    planner = TransportPlanner(csv_repo)
    
    # データ読み込み
    orders_df = csv_repo.get_delivery_progress()
    products_df = csv_repo.get_products()
    containers_df = csv_repo.get_containers()
    trucks_df = csv_repo.get_trucks()
    
    print(f"受注データ: {len(orders_df)}件")
    print(f"製品データ: {len(products_df)}件")
    print(f"容器データ: {len(containers_df)}件")
    print(f"トラックデータ: {len(trucks_df)}件")
    
    # 期間設定
    start_date = date.today()
    end_date = date.today() + timedelta(days=10)
    
    print(f"\n計画期間: {start_date} ～ {end_date}")
    
    # 計画作成
    result = planner.calculate_loading_plan_from_orders(
        orders_df, products_df, containers_df, trucks_df,
        start_date, end_date
    )
    
    print("\n✅ 計画作成成功")
    
except Exception as e:
    print("\n❌ エラー発生:")
    print(traceback.format_exc())
