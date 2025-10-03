# app/services/transport_service.py
from typing import List, Dict, Any
from datetime import date, timedelta
from repository.transport_repository import TransportRepository
from repository.production_repository import ProductionRepository
from repository.product_repository import ProductRepository
from repository.loading_plan_repository import LoadingPlanRepository
from domain.calculators.transport_planner import TransportPlanner
from domain.validators.loading_validator import LoadingValidator
from domain.models.transport import LoadingItem
import pandas as pd

class TransportService:
    """運送関連ビジネスロジック"""
    
    def __init__(self, db_manager):
        self.transport_repo = TransportRepository(db_manager)
        self.production_repo = ProductionRepository(db_manager)
        self.product_repo = ProductRepository(db_manager)
        self.loading_plan_repo = LoadingPlanRepository(db_manager)
        self.planner = TransportPlanner()
        self.validator = LoadingValidator()
    
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
    
    def calculate_delivery_plan(self, delivery_items: List[dict]) -> Dict[str, Any]:
        """配送計画計算（旧バージョン・互換性のため残す）"""
        containers = self.get_containers()
        trucks = self.get_trucks()
        
        items = [LoadingItem(**item) for item in delivery_items]
        return self.planner.calculate_loading_plan(items, containers, trucks)
    
    def validate_loading(self, items: List[dict], truck_id: int) -> tuple:
        """積載バリデーション"""
        containers = self.get_containers()
        trucks_df = self.get_trucks()
        
        truck_row = trucks_df[trucks_df['id'] == truck_id]
        if truck_row.empty:
            return False, ["トラックが見つかりません"]
        
        loading_items = [LoadingItem(**item) for item in items]
        return self.validator.validate_loading(loading_items, containers, truck_row.iloc[0])
    
    def calculate_loading_plan_from_orders(self, 
                                          start_date: date, 
                                          days: int = 7) -> Dict[str, Any]:
        """
        オーダー情報から積載計画を自動作成
        
        Args:
            start_date: 計画開始日
            days: 計画日数（デフォルト7日間）
        
        Returns:
            日別積載計画
        """
        
        # データ取得
        end_date = start_date + timedelta(days=days - 1)
        
        # production_repository経由でオーダー取得
        orders_df = self.production_repo.get_production_instructions(start_date, end_date)
        
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