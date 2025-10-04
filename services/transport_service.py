# app/services/transport_service.py（納入進度統合版）
from typing import List, Dict, Any
from datetime import date, timedelta
from repository.transport_repository import TransportRepository
from repository.production_repository import ProductionRepository
from repository.product_repository import ProductRepository
from repository.loading_plan_repository import LoadingPlanRepository
from repository.delivery_progress_repository import DeliveryProgressRepository
from domain.calculators.transport_planner import TransportPlanner
from domain.validators.loading_validator import LoadingValidator
from domain.models.transport import LoadingItem
import pandas as pd

class TransportService:
    """運送関連ビジネスロジック（納入進度統合版）"""
    
    def __init__(self, db_manager):
        self.transport_repo = TransportRepository(db_manager)
        self.production_repo = ProductionRepository(db_manager)
        self.product_repo = ProductRepository(db_manager)
        self.loading_plan_repo = LoadingPlanRepository(db_manager)
        self.delivery_progress_repo = DeliveryProgressRepository(db_manager)  # 追加
        self.planner = TransportPlanner()
        self.validator = LoadingValidator()
    
    # ===== 既存機能 =====
    
    def get_containers(self):
        """容器一覧取得"""
        return self.transport_repo.get_containers()

    def get_trucks(self):
        """トラック一覧取得"""
        return self.transport_repo.get_trucks()

    def delete_truck(self, truck_id: int) -> bool:
        """トラック削除"""
        return self.transport_repo.delete_truck(truck_id) 
    
    def update_truck(self, truck_id: int, update_data: dict) -> bool:
        """トラック更新"""
        return self.transport_repo.update_truck(truck_id, update_data)

    def create_container(self, container_data: dict) -> bool:
        container_data.pop("max_volume", None)
        container_data.pop("created_at", None)
        return self.transport_repo.save_container(container_data)

    def update_container(self, container_id: int, update_data: dict) -> bool:
        update_data.pop("max_volume", None)
        update_data.pop("created_at", None)
        return self.transport_repo.update_container(container_id, update_data)
    
    def delete_container(self, container_id: int) -> bool:
        """容器削除"""
        return self.transport_repo.delete_container(container_id)

    def create_truck(self, truck_data: dict) -> bool:
        """トラック作成"""
        return self.transport_repo.save_truck(truck_data)
    
    # ===== 積載計画機能 =====
    
    def calculate_loading_plan_from_orders(self, 
                                          start_date: date, 
                                          days: int = 7,
                                          use_delivery_progress: bool = True) -> Dict[str, Any]:
        """
        オーダー情報から積載計画を自動作成
        
        Args:
            start_date: 計画開始日
            days: 計画日数（デフォルト7日間）
            use_delivery_progress: 納入進度テーブルを使用するか（True推奨）
        
        Returns:
            日別積載計画
        """
        
        end_date = start_date + timedelta(days=days - 1)
        
        # ✅ 修正: 納入進度テーブルがあればそれを優先、なければ生産指示テーブルを使用
        if use_delivery_progress:
            orders_df = self.delivery_progress_repo.get_delivery_progress(start_date, end_date)
            
            if orders_df.empty:
                print("⚠️ 納入進度データがありません。生産指示データを使用します。")
                orders_df = self.production_repo.get_production_instructions(start_date, end_date)
                
                # ✅ カラム名を統一（必須）
                if not orders_df.empty:
                    orders_df = orders_df.rename(columns={
                        'instruction_date': 'delivery_date',
                        'instruction_quantity': 'order_quantity'
                    })
            else:
                print(f"✅ 納入進度データを使用: {len(orders_df)}件")
        else:
            # 生産指示テーブルから取得
            orders_df = self.production_repo.get_production_instructions(start_date, end_date)
            
            # ✅ カラム名を統一（必須）
            if not orders_df.empty:
                orders_df = orders_df.rename(columns={
                    'instruction_date': 'delivery_date',
                    'instruction_quantity': 'order_quantity'
                })
        
        # ✅ デバッグ情報
        if not orders_df.empty:
            print(f"📊 オーダーデータ: {len(orders_df)}件")
            print(f"📊 カラム: {orders_df.columns.tolist()}")
            print(f"📊 サンプル: {orders_df.head(1).to_dict()}")
        
        # データ確認
        if orders_df is None or orders_df.empty:
            return {
                'daily_plans': {},
                'summary': {
                    'total_days': days,
                    'total_trips': 0,
                    'total_warnings': 0,
                    'unloaded_count': 0,
                    'status': '正常'
                },
                'unloaded_tasks': [],
                'period': f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
            }
        
        products_df = self.product_repo.get_all_products()
        containers = self.get_containers()
        trucks_df = self.get_trucks()
        truck_container_rules = self.transport_repo.get_truck_container_rules()
        
        # 積載計画計算
        result = self.planner.calculate_loading_plan_from_orders(
            orders_df=orders_df,
            products_df=products_df,
            containers=containers,
            trucks_df=trucks_df,
            truck_container_rules=truck_container_rules,
            start_date=start_date,
            days=days
        )
        
        return result
    
    def save_loading_plan(self, plan_result: Dict[str, Any], plan_name: str = None) -> int:
        """積載計画をDBに保存"""
        return self.loading_plan_repo.save_loading_plan(plan_result, plan_name)
    
    def get_loading_plan(self, plan_id: int) -> Dict[str, Any]:
        """保存済み積載計画を取得"""
        return self.loading_plan_repo.get_loading_plan(plan_id)
    
    def get_all_loading_plans(self) -> List[Dict]:
        """全積載計画のリスト取得"""
        return self.loading_plan_repo.get_all_plans()
    
    def delete_loading_plan(self, plan_id: int) -> bool:
        """積載計画を削除"""
        return self.loading_plan_repo.delete_loading_plan(plan_id)
    
    # ===== 納入進度機能（新規） =====
    
    def get_delivery_progress(self, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """納入進度取得"""
        return self.delivery_progress_repo.get_delivery_progress(start_date, end_date)
    
    def create_delivery_progress(self, progress_data: Dict[str, Any]) -> int:
        """納入進度を新規作成"""
        return self.delivery_progress_repo.create_delivery_progress(progress_data)
    
    def update_delivery_progress(self, progress_id: int, update_data: Dict[str, Any]) -> bool:
        """納入進度を更新"""
        return self.delivery_progress_repo.update_delivery_progress(progress_id, update_data)
    
    def delete_delivery_progress(self, progress_id: int) -> bool:
        """納入進度を削除"""
        return self.delivery_progress_repo.delete_delivery_progress(progress_id)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """納入進度サマリー取得"""
        return self.delivery_progress_repo.get_progress_summary()
    
    def create_shipment_record(self, shipment_data: Dict[str, Any]) -> bool:
        """出荷実績を登録"""
        return self.delivery_progress_repo.create_shipment_record(shipment_data)
    
    def get_shipment_records(self, progress_id: int = None) -> pd.DataFrame:
        """出荷実績を取得"""
        return self.delivery_progress_repo.get_shipment_records(progress_id)