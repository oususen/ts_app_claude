# app/services/transport_service.py（カレンダー統合版）
from typing import List, Dict, Any
from datetime import date, timedelta
from repository.transport_repository import TransportRepository
from repository.production_repository import ProductionRepository
from repository.product_repository import ProductRepository
from repository.loading_plan_repository import LoadingPlanRepository
from repository.delivery_progress_repository import DeliveryProgressRepository
from repository.calendar_repository import CalendarRepository  # ✅ 追加
from domain.calculators.transport_planner import TransportPlanner
from domain.validators.loading_validator import LoadingValidator
from domain.models.transport import LoadingItem
import pandas as pd
from datetime import datetime
from io import BytesIO


class TransportService:
    """運送関連ビジネスロジック（カレンダー統合版）"""
    
    def __init__(self, db_manager):
        self.transport_repo = TransportRepository(db_manager)
        self.production_repo = ProductionRepository(db_manager)
        self.product_repo = ProductRepository(db_manager)
        self.loading_plan_repo = LoadingPlanRepository(db_manager)
        self.delivery_progress_repo = DeliveryProgressRepository(db_manager)
        self.calendar_repo = CalendarRepository(db_manager)  # ✅ 追加
        
        self.planner = TransportPlanner()
        self.db = db_manager
    
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
    
    def calculate_loading_plan_from_orders(self, 
                                          start_date: date, 
                                          days: int = 7,
                                          use_delivery_progress: bool = True,
                                          use_calendar: bool = True) -> Dict[str, Any]:  # ✅ use_calendar追加
        """
        オーダー情報から積載計画を自動作成（カレンダー対応）
        
        Args:
            start_date: 計画開始日
            days: 計画日数
            use_delivery_progress: 納入進度を使用するか
            use_calendar: 会社カレンダーを使用するか（営業日のみで計画）
        """
        
        end_date = start_date + timedelta(days=days - 1)
        
        if use_delivery_progress:
            orders_df = self.delivery_progress_repo.get_delivery_progress(start_date, end_date)
            
            if orders_df.empty:
                orders_df = self.production_repo.get_production_instructions(start_date, end_date)
                
                if not orders_df.empty:
                    orders_df = orders_df.rename(columns={
                        'instruction_date': 'delivery_date',
                        'instruction_quantity': 'order_quantity'
                    })
        else:
            orders_df = self.production_repo.get_production_instructions(start_date, end_date)
            
            if not orders_df.empty:
                orders_df = orders_df.rename(columns={
                    'instruction_date': 'delivery_date',
                    'instruction_quantity': 'order_quantity'
                })
        
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
        
        # ✅ カレンダーリポジトリを渡す
        result = self.planner.calculate_loading_plan_from_orders(
            orders_df=orders_df,
            products_df=products_df,
            containers=containers,
            trucks_df=trucks_df,
            truck_container_rules=truck_container_rules,
            start_date=start_date,
            days=days,
            calendar_repo=self.calendar_repo if use_calendar else None  # ✅ カレンダー渡す
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
   
    def export_loading_plan_to_excel(self, plan_result: Dict[str, Any], 
                                     export_format: str = 'daily') -> BytesIO:
        """積載計画をExcelファイルとして出力"""
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_df = pd.DataFrame([{
                '項目': k,
                '値': v
            } for k, v in plan_result['summary'].items()])
            summary_df.to_excel(writer, sheet_name='サマリー', index=False)
            
            if export_format == 'daily':
                self._export_daily_plan(writer, plan_result)
            elif export_format == 'weekly':
                self._export_weekly_plan(writer, plan_result)
            
            if plan_result.get('unloaded_tasks'):
                unloaded_df = pd.DataFrame([{
                    '製品コード': task['product_code'],
                    '製品名': task['product_name'],
                    '容器数': task['num_containers'],
                    '合計数量': task['total_quantity'],
                    '納期': task['delivery_date'].strftime('%Y-%m-%d')
                } for task in plan_result['unloaded_tasks']])
                unloaded_df.to_excel(writer, sheet_name='積載不可', index=False)
            
            warnings_data = []
            for date_str, plan in plan_result['daily_plans'].items():
                for warning in plan.get('warnings', []):
                    warnings_data.append({
                        '日付': date_str,
                        '警告内容': warning
                    })
            
            if warnings_data:
                warnings_df = pd.DataFrame(warnings_data)
                warnings_df.to_excel(writer, sheet_name='警告一覧', index=False)
        
        output.seek(0)
        return output
    
    def _export_daily_plan(self, writer, plan_result):
        """日別計画をExcelシートに出力"""
        
        daily_data = []
        
        for date_str in sorted(plan_result['daily_plans'].keys()):
            plan = plan_result['daily_plans'][date_str]
            
            for truck in plan.get('trucks', []):
                for item in truck.get('loaded_items', []):
                    daily_data.append({
                        '積載日': date_str,
                        'トラック名': truck['truck_name'],
                        '製品コード': item.get('product_code', ''),
                        '製品名': item.get('product_name', ''),
                        '容器数': item.get('num_containers', 0),
                        '合計数量': item.get('total_quantity', 0),
                        '納期': item['delivery_date'].strftime('%Y-%m-%d') if 'delivery_date' in item else '',
                        '体積積載率': f"{truck['utilization']['volume_rate']}%",
                        '重量積載率': f"{truck['utilization']['weight_rate']}%"
                    })
        
        if daily_data:
            daily_df = pd.DataFrame(daily_data)
            daily_df.to_excel(writer, sheet_name='日別計画', index=False)
    
    def _export_weekly_plan(self, writer, plan_result):
        """週別計画をExcelシートに出力"""
        
        from datetime import datetime
        
        weekly_data = {}
        
        for date_str in sorted(plan_result['daily_plans'].keys()):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            week_num = date_obj.isocalendar()[1]
            week_key = f"{date_obj.year}年第{week_num}週"
            
            if week_key not in weekly_data:
                weekly_data[week_key] = []
            
            plan = plan_result['daily_plans'][date_str]
            
            for truck in plan.get('trucks', []):
                for item in truck.get('loaded_items', []):
                    weekly_data[week_key].append({
                        '週': week_key,
                        '積載日': date_str,
                        'トラック名': truck['truck_name'],
                        '製品コード': item.get('product_code', ''),
                        '製品名': item.get('product_name', ''),
                        '容器数': item.get('num_containers', 0),
                        '合計数量': item.get('total_quantity', 0)
                    })
        
        for week_key, items in weekly_data.items():
            if items:
                week_df = pd.DataFrame(items)
                sheet_name = week_key[:31]
                week_df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    def export_loading_plan_to_csv(self, plan_result: Dict[str, Any]) -> str:
        """積載計画をCSV形式で出力"""
        
        daily_data = []
        
        for date_str in sorted(plan_result['daily_plans'].keys()):
            plan = plan_result['daily_plans'][date_str]
            
            for truck in plan.get('trucks', []):
                for item in truck.get('loaded_items', []):
                    daily_data.append({
                        '積載日': date_str,
                        'トラック名': truck['truck_name'],
                        '製品コード': item.get('product_code', ''),
                        '製品名': item.get('product_name', ''),
                        '容器数': item.get('num_containers', 0),
                        '合計数量': item.get('total_quantity', 0),
                        '納期': item['delivery_date'].strftime('%Y-%m-%d') if 'delivery_date' in item else '',
                        '体積積載率': truck['utilization']['volume_rate'],
                        '重量積載率': truck['utilization']['weight_rate']
                    })
        
        if daily_data:
            df = pd.DataFrame(daily_data)
            return df.to_csv(index=False, encoding='utf-8-sig')
        else:
            return ""