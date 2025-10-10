# app/domain/calculators/transport_planner_v2.py
from typing import List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict
import pandas as pd


class TransportPlannerV2:
    """
    運送計画計算機 V2 - 新ルール対応版
    
    【基本ルール】
    1. 底面積ベースで計算（体積ではなく）
    2. デフォルト3台 + 非デフォルト1台
    3. 前倒しは1日前のみ
    4. トラックの優先積載製品を考慮
    
    【計画プロセス】
    Step1: 需要分析とトラック台数決定
    Step2: 前倒し処理（最終日から逆順）
    Step3: 日次積載計画作成（優先製品→同容器製品→異容器製品）
    Step4: 非デフォルトトラック活用
    """
    
    def __init__(self, calendar_repo=None):
        self.calendar_repo = calendar_repo
    
    def calculate_loading_plan_from_orders(self,
                                          orders_df: pd.DataFrame,
                                          products_df: pd.DataFrame,
                                          containers: List[Any],
                                          trucks_df: pd.DataFrame,
                                          truck_container_rules: List[Any],
                                          start_date: date,
                                          days: int = 7,
                                          calendar_repo=None) -> Dict[str, Any]:
        """新ルールに基づく積載計画作成"""
        
        self.calendar_repo = calendar_repo
        
        # 営業日のみで計画期間を構築
        working_dates = self._get_working_dates(start_date, days, calendar_repo)
        
        # データ準備
        container_map = {c.id: c for c in containers}
        truck_map = {int(row['id']): row for _, row in trucks_df.iterrows()}
        product_map = {int(row['id']): row for _, row in products_df.iterrows()}
        
        # Step1: 需要分析とトラック台数決定
        daily_demands, use_non_default = self._analyze_demand_and_decide_trucks(
            orders_df, product_map, container_map, truck_map, working_dates
        )
        
        # Step2: 前倒し処理（最終日から逆順）
        adjusted_demands = self._forward_scheduling(
            daily_demands, truck_map, container_map, working_dates, use_non_default
        )
        
        # Step3: 日次積載計画作成
        daily_plans = {}
        for working_date in working_dates:
            date_str = working_date.strftime('%Y-%m-%d')
            
            if date_str not in adjusted_demands or not adjusted_demands[date_str]:
                daily_plans[date_str] = {'trucks': [], 'total_trips': 0, 'warnings': []}
                continue
            
            plan = self._create_daily_loading_plan(
                adjusted_demands[date_str],
                truck_map,
                container_map,
                product_map,
                use_non_default
            )
            
            daily_plans[date_str] = plan
        
        # サマリー作成
        summary = self._create_summary(daily_plans, use_non_default)
        
        return {
            'daily_plans': daily_plans,
            'summary': summary,
            'period': f"{working_dates[0].strftime('%Y-%m-%d')} ~ {working_dates[-1].strftime('%Y-%m-%d')}",
            'working_dates': [d.strftime('%Y-%m-%d') for d in working_dates],
            'use_non_default_truck': use_non_default
        }
    
    def _get_working_dates(self, start_date: date, days: int, calendar_repo) -> List[date]:
        """営業日のみを取得"""
        working_dates = []
        current_date = start_date
        
        while len(working_dates) < days:
            if not calendar_repo or calendar_repo.is_working_day(current_date):
                working_dates.append(current_date)
            current_date += timedelta(days=1)
        
        return working_dates
    
    def _analyze_demand_and_decide_trucks(self, orders_df, product_map, container_map, 
                                         truck_map, working_dates) -> Tuple[Dict, bool]:
        """
        Step1: 需要分析とトラック台数決定
        
        Returns:
            daily_demands: {日付: [需要リスト]}
            use_non_default: 非デフォルトトラックを使用するか
        """
        daily_demands = defaultdict(list)
        total_floor_area = 0
        
        # デフォルトトラックの総底面積を計算
        default_trucks = [t for _, t in truck_map.items() if t.get('default_use', False)]
        default_total_floor_area = sum(t['width'] * t['depth'] for t in default_trucks)
        
        # 各受注を処理
        for _, order in orders_df.iterrows():
            product_id = int(order['product_id'])
            
            if product_id not in product_map:
                continue
            
            product = product_map[product_id]
            
            # 納期取得
            delivery_date = self._parse_date(order.get('delivery_date') or order.get('instruction_date'))
            if not delivery_date:
                continue
            
            # 数量取得
            quantity = int(order.get('order_quantity') or order.get('instruction_quantity', 0))
            if quantity <= 0:
                continue
            
            # 容器情報取得
            container_id = product.get('used_container_id')
            if not container_id or pd.isna(container_id):
                continue
            
            container = container_map.get(int(container_id))
            if not container:
                continue
            
            # 容器数と底面積を計算
            capacity = product.get('capacity', 1)
            num_containers = (quantity + capacity - 1) // capacity
            floor_area_per_container = container.width * container.depth
            total_floor_area_needed = floor_area_per_container * num_containers
            
            total_floor_area += total_floor_area_needed
            
            # トラックの到着日オフセットを考慮して積載日を決定
            truck_ids_str = product.get('used_truck_ids')
            if truck_ids_str and not pd.isna(truck_ids_str):
                truck_ids = [int(tid.strip()) for tid in str(truck_ids_str).split(',')]
            else:
                truck_ids = [tid for tid, t in truck_map.items() if t.get('default_use', False)]
            
            # 最初のトラックのオフセットを使用
            if truck_ids and truck_ids[0] in truck_map:
                offset = int(truck_map[truck_ids[0]].get('arrival_day_offset', 0))
                loading_date = delivery_date - timedelta(days=offset)
                
                # 営業日チェック
                if self.calendar_repo:
                    for _ in range(7):
                        if self.calendar_repo.is_working_day(loading_date):
                            break
                        loading_date -= timedelta(days=1)
                
                # 計画期間内のみ
                if loading_date in working_dates:
                    date_str = loading_date.strftime('%Y-%m-%d')
                    
                    daily_demands[date_str].append({
                        'product_id': product_id,
                        'product_code': product.get('product_code', ''),
                        'product_name': product.get('product_name', ''),
                        'container_id': int(container_id),
                        'num_containers': num_containers,
                        'total_quantity': quantity,
                        'floor_area': total_floor_area_needed,
                        'floor_area_per_container': floor_area_per_container,
                        'delivery_date': delivery_date,
                        'loading_date': loading_date,
                        'capacity': capacity,
                        'truck_ids': truck_ids
                    })
        
        # 日平均積載量を計算
        avg_floor_area = total_floor_area / len(working_dates) if working_dates else 0
        
        # 非デフォルトトラック使用判定
        use_non_default = avg_floor_area > default_total_floor_area
        
        return dict(daily_demands), use_non_default
    
    def _forward_scheduling(self, daily_demands, truck_map, container_map, 
                           working_dates, use_non_default) -> Dict:
        """
        Step2: 前倒し処理（最終日から逆順）
        
        各日の積載量がトラック能力を超過する場合、超過分を前日に前倒し
        """
        adjusted_demands = {d.strftime('%Y-%m-%d'): [] for d in working_dates}
        
        # 初期需要をコピー
        for date_str, demands in daily_demands.items():
            adjusted_demands[date_str] = [d.copy() for d in demands]
        
        # トラックの総底面積を計算
        if use_non_default:
            available_trucks = [t for _, t in truck_map.items()]
        else:
            available_trucks = [t for _, t in truck_map.items() if t.get('default_use', False)]
        
        total_truck_floor_area = sum(t['width'] * t['depth'] for t in available_trucks)
        
        # 最終日から逆順に処理
        for i in range(len(working_dates) - 1, 0, -1):
            current_date = working_dates[i]
            prev_date = working_dates[i - 1]
            
            current_date_str = current_date.strftime('%Y-%m-%d')
            prev_date_str = prev_date.strftime('%Y-%m-%d')
            
            # 当日の総底面積を計算
            current_floor_area = sum(d['floor_area'] for d in adjusted_demands[current_date_str])
            
            # 超過分を前倒し
            if current_floor_area > total_truck_floor_area:
                excess_area = current_floor_area - total_truck_floor_area
                
                # 前倒し可能な製品を選択（can_advance=Trueまたは全て）
                demands_to_forward = []
                remaining_demands = []
                
                for demand in adjusted_demands[current_date_str]:
                    if excess_area > 0:
                        demands_to_forward.append(demand)
                        excess_area -= demand['floor_area']
                    else:
                        remaining_demands.append(demand)
                
                # 前日に追加
                adjusted_demands[prev_date_str].extend(demands_to_forward)
                adjusted_demands[current_date_str] = remaining_demands
        
        return adjusted_demands
    
    def _create_daily_loading_plan(self, demands, truck_map, container_map, 
                                   product_map, use_non_default) -> Dict:
        """
        Step3: 日次積載計画作成
        
        優先順位:
        1. 各トラックの優先積載製品
        2. 同容器の製品
        3. 異容器の製品
        """
        truck_plans = []
        remaining_demands = []
        warnings = []
        
        # 使用可能なトラックを取得
        if use_non_default:
            available_trucks = [(tid, t) for tid, t in truck_map.items()]
        else:
            available_trucks = [(tid, t) for tid, t in truck_map.items() if t.get('default_use', False)]
        
        # デフォルトトラック優先でソート
        available_trucks.sort(key=lambda x: (not x[1].get('default_use', False), x[0]))
        
        used_truck_ids = set()
        
        # 各トラックについて積載計画を作成
        for truck_id, truck_info in available_trucks:
            if truck_id in used_truck_ids:
                continue
            
            truck_plan = {
                'truck_id': truck_id,
                'truck_name': truck_info['name'],
                'loaded_items': [],
                'utilization': {'floor_area_rate': 0}
            }
            
            truck_floor_area = truck_info['width'] * truck_info['depth']
            remaining_floor_area = truck_floor_area
            
            # 優先積載製品を取得
            priority_products = self._get_priority_products(truck_info)
            
            # Step3-1: 優先積載製品を積載
            demands, remaining_floor_area = self._load_priority_products(
                demands, truck_plan, priority_products, container_map, remaining_floor_area
            )
            
            # Step3-2: 同容器の製品を積載
            if truck_plan['loaded_items']:
                loaded_container_ids = set(item['container_id'] for item in truck_plan['loaded_items'])
                demands, remaining_floor_area = self._load_same_container_products(
                    demands, truck_plan, loaded_container_ids, container_map, remaining_floor_area
                )
            
            # Step3-3: 異容器の製品を積載
            demands, remaining_floor_area = self._load_other_products(
                demands, truck_plan, container_map, remaining_floor_area
            )
            
            # 積載率を計算
            if truck_plan['loaded_items']:
                total_loaded_area = sum(
                    item['floor_area_per_container'] * item['num_containers']
                    for item in truck_plan['loaded_items']
                )
                truck_plan['utilization']['floor_area_rate'] = round(
                    total_loaded_area / truck_floor_area * 100, 1
                )
                
                truck_plans.append(truck_plan)
                used_truck_ids.add(truck_id)
        
        # 積み残しチェック
        if demands:
            for demand in demands:
                remaining_demands.append(demand)
                warnings.append(
                    f"❌ 積み残し: {demand['product_code']} ({demand['num_containers']}容器)"
                )
        
        return {
            'trucks': truck_plans,
            'total_trips': len(truck_plans),
            'warnings': warnings,
            'remaining_demands': remaining_demands
        }
    
    def _get_priority_products(self, truck_info) -> List[str]:
        """トラックの優先積載製品を取得"""
        priority_products_str = truck_info.get('priority_products', '')
        if priority_products_str and not pd.isna(priority_products_str):
            return [p.strip() for p in str(priority_products_str).split(',')]
        return []
    
    def _load_priority_products(self, demands, truck_plan, priority_products, 
                               container_map, remaining_floor_area):
        """優先積載製品を積載"""
        if not priority_products:
            return demands, remaining_floor_area
        
        remaining_demands = []
        
        for demand in demands:
            product_code = demand['product_code']
            
            if product_code in priority_products:
                # 積載可能かチェック
                if demand['floor_area'] <= remaining_floor_area:
                    truck_plan['loaded_items'].append(demand)
                    remaining_floor_area -= demand['floor_area']
                else:
                    remaining_demands.append(demand)
            else:
                remaining_demands.append(demand)
        
        return remaining_demands, remaining_floor_area
    
    def _load_same_container_products(self, demands, truck_plan, loaded_container_ids,
                                     container_map, remaining_floor_area):
        """同容器の製品を積載"""
        remaining_demands = []
        
        for demand in demands:
            container_id = demand['container_id']
            
            if container_id in loaded_container_ids:
                if demand['floor_area'] <= remaining_floor_area:
                    truck_plan['loaded_items'].append(demand)
                    remaining_floor_area -= demand['floor_area']
                else:
                    remaining_demands.append(demand)
            else:
                remaining_demands.append(demand)
        
        return remaining_demands, remaining_floor_area
    
    def _load_other_products(self, demands, truck_plan, container_map, remaining_floor_area):
        """異容器の製品を積載"""
        remaining_demands = []
        
        for demand in demands:
            if demand['floor_area'] <= remaining_floor_area:
                truck_plan['loaded_items'].append(demand)
                remaining_floor_area -= demand['floor_area']
            else:
                remaining_demands.append(demand)
        
        return remaining_demands, remaining_floor_area
    
    def _parse_date(self, date_value):
        """日付を解析"""
        if not date_value:
            return None
        
        if isinstance(date_value, date):
            return date_value
        
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except:
                try:
                    return datetime.strptime(date_value, '%Y/%m/%d').date()
                except:
                    return None
        
        if hasattr(date_value, 'date'):
            return date_value.date()
        
        return None
    
    def _create_summary(self, daily_plans, use_non_default) -> Dict:
        """サマリー作成"""
        total_trips = sum(plan['total_trips'] for plan in daily_plans.values())
        total_warnings = sum(len(plan['warnings']) for plan in daily_plans.values())
        
        return {
            'total_days': len(daily_plans),
            'total_trips': total_trips,
            'total_warnings': total_warnings,
            'use_non_default_truck': use_non_default,
            'status': '正常' if total_warnings == 0 else '警告あり'
        }
