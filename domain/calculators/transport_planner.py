# app/domain/calculators/transport_planner.py
from typing import List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict
import pandas as pd


class TransportPlanner:
    """
    運送計画計算機 - 新ルール対応版
    
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
            'unloaded_tasks': [],  # 互換性のため
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
            
            # 容器数と底面積を計算（段積み考慮）
            capacity = product.get('capacity', 1)
            num_containers = (quantity + capacity - 1) // capacity
            floor_area_per_container = container.width * container.depth
            
            # 段積み可能な場合、底面積を段数で割る
            max_stack = getattr(container, 'max_stack', 1)
            if max_stack > 1 and getattr(container, 'stackable', False):
                # 段積み後の実際の底面積
                stacked_containers = (num_containers + max_stack - 1) // max_stack
                total_floor_area_needed = floor_area_per_container * stacked_containers
            else:
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
                        'truck_ids': truck_ids,
                        'max_stack': max_stack,
                        'stackable': getattr(container, 'stackable', False)
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
                
                # 前倒し可能な製品を選択
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
        
        製品ごとに適切なトラックを選択して積載
        """
        truck_plans = {}
        remaining_demands = []
        warnings = []
        
        # 使用可能なトラックを取得
        if use_non_default:
            available_trucks = {tid: t for tid, t in truck_map.items()}
        else:
            available_trucks = {tid: t for tid, t in truck_map.items() if t.get('default_use', False)}
        
        # トラック状態を初期化
        truck_states = {}
        for truck_id, truck_info in available_trucks.items():
            truck_floor_area = truck_info['width'] * truck_info['depth']
            truck_states[truck_id] = {
                'truck_id': truck_id,
                'truck_name': truck_info['name'],
                'truck_info': truck_info,
                'loaded_items': [],
                'remaining_floor_area': truck_floor_area,
                'total_floor_area': truck_floor_area,
                'loaded_container_ids': set(),
                'priority_products': self._get_priority_products(truck_info)
            }
        
        # 製品を優先度順にソート
        # 1. 優先積載製品指定あり
        # 2. トラック制約あり（used_truck_ids）
        sorted_demands = self._sort_demands_by_priority(demands, truck_states)
        
        # 各製品を適切なトラックに積載
        for demand in sorted_demands:
            loaded = False
            
            # 製品のトラック制約を取得
            allowed_truck_ids = demand.get('truck_ids', [])
            if not allowed_truck_ids:
                allowed_truck_ids = list(available_trucks.keys())
            
            # 制約に合うトラックのみを対象
            candidate_trucks = [tid for tid in allowed_truck_ids if tid in truck_states]
            
            # デバッグ: 候補トラックが空の場合
            if not candidate_trucks and allowed_truck_ids:
                warnings.append(
                    f"⚠️ {demand['product_code']}: トラック制約{allowed_truck_ids}のトラックが使用不可"
                )
            
            # 候補トラックを優先順位でソート
            # 1. 優先積載製品に指定されているトラック
            # 2. 同容器が既に積載されているトラック
            # 3. 空き容量が大きいトラック
            candidate_trucks = self._sort_candidate_trucks(
                candidate_trucks, demand, truck_states
            )
            
            # トラックに積載を試みる
            remaining_demand = demand.copy()
            
            for truck_id in candidate_trucks:
                truck_state = truck_states[truck_id]
                container_id = remaining_demand['container_id']
                
                # 同じ容器が既に積載されているか確認（段積み統合用）
                same_container_items = [item for item in truck_state['loaded_items'] 
                                       if item['container_id'] == container_id]
                
                if same_container_items:
                    # 同じ容器が既にある場合、段積みとして統合できるか確認
                    container = container_map.get(container_id)
                    if container and getattr(container, 'stackable', False):
                        max_stack = getattr(container, 'max_stack', 1)
                        floor_area_per_container = container.width * container.depth
                        
                        # 既存の容器数を計算（同じ容器IDの全製品）
                        existing_containers = sum(item['num_containers'] for item in same_container_items)
                        new_total_containers = existing_containers + remaining_demand['num_containers']
                        
                        # 既存の配置数
                        existing_stacks = (existing_containers + max_stack - 1) // max_stack
                        # 新しい配置数
                        new_stacks = (new_total_containers + max_stack - 1) // max_stack
                        
                        # 追加で必要な配置数
                        additional_stacks = new_stacks - existing_stacks
                        additional_floor_area = additional_stacks * floor_area_per_container
                        
                        if additional_floor_area <= truck_state['remaining_floor_area']:
                            # 段積みとして統合可能
                            truck_state['loaded_items'].append(remaining_demand)
                            truck_state['remaining_floor_area'] -= additional_floor_area
                            loaded = True
                            break
                
                # 通常の積載チェック
                if remaining_demand['floor_area'] <= truck_state['remaining_floor_area']:
                    # 全量積載可能
                    truck_state['loaded_items'].append(remaining_demand)
                    truck_state['remaining_floor_area'] -= remaining_demand['floor_area']
                    truck_state['loaded_container_ids'].add(remaining_demand['container_id'])
                    loaded = True
                    break
                elif truck_state['remaining_floor_area'] > 0:
                    # 一部積載可能（分割）
                    container = container_map.get(remaining_demand['container_id'])
                    if container:
                        floor_area_per_container = container.width * container.depth
                        max_stack = getattr(container, 'max_stack', 1)
                        
                        # 段積み考慮で積載可能な容器数を計算
                        if max_stack > 1 and getattr(container, 'stackable', False):
                            # 段積み可能
                            max_stacks = int(truck_state['remaining_floor_area'] / floor_area_per_container)
                            loadable_containers = max_stacks * max_stack
                        else:
                            # 段積みなし
                            loadable_containers = int(truck_state['remaining_floor_area'] / floor_area_per_container)
                        
                        if loadable_containers > 0 and loadable_containers < remaining_demand['num_containers']:
                            # 分割積載
                            capacity = remaining_demand['capacity']
                            loadable_quantity = loadable_containers * capacity
                            
                            # 段積み後の底面積
                            if max_stack > 1 and getattr(container, 'stackable', False):
                                stacked = (loadable_containers + max_stack - 1) // max_stack
                                loadable_floor_area = floor_area_per_container * stacked
                            else:
                                loadable_floor_area = floor_area_per_container * loadable_containers
                            
                            # 分割して積載
                            split_demand = remaining_demand.copy()
                            split_demand['num_containers'] = loadable_containers
                            split_demand['total_quantity'] = loadable_quantity
                            split_demand['floor_area'] = loadable_floor_area
                            
                            truck_state['loaded_items'].append(split_demand)
                            truck_state['remaining_floor_area'] -= loadable_floor_area
                            truck_state['loaded_container_ids'].add(remaining_demand['container_id'])
                            
                            # 残りを更新
                            remaining_demand['num_containers'] -= loadable_containers
                            remaining_demand['total_quantity'] -= loadable_quantity
                            remaining_demand['floor_area'] -= loadable_floor_area
                            
                            # 次のトラックへ
                            continue
            
            if not loaded and remaining_demand['num_containers'] > 0:
                remaining_demands.append(remaining_demand)
        
        # トラックプランを作成（積載があるトラックのみ）
        final_truck_plans = []
        for truck_id, truck_state in truck_states.items():
            if truck_state['loaded_items']:
                # 積載率を計算（容器別に段積み考慮）
                container_totals = {}  # container_id -> 容器数の合計
                
                # 容器別に集計
                for item in truck_state['loaded_items']:
                    container_id = item['container_id']
                    if container_id not in container_totals:
                        container_totals[container_id] = {
                            'num_containers': 0,
                            'floor_area_per_container': item['floor_area_per_container'],
                            'stackable': item.get('stackable', False),
                            'max_stack': item.get('max_stack', 1)
                        }
                    container_totals[container_id]['num_containers'] += item['num_containers']
                
                # 容器別に底面積を計算
                total_loaded_area = 0
                for container_id, info in container_totals.items():
                    if info['stackable'] and info['max_stack'] > 1:
                        # 段積み可能
                        stacked_containers = (info['num_containers'] + info['max_stack'] - 1) // info['max_stack']
                        container_area = info['floor_area_per_container'] * stacked_containers
                    else:
                        # 段積みなし
                        container_area = info['floor_area_per_container'] * info['num_containers']
                    total_loaded_area += container_area
                
                utilization_rate = round(total_loaded_area / truck_state['total_floor_area'] * 100, 1)
                
                truck_plan = {
                    'truck_id': truck_id,
                    'truck_name': truck_state['truck_name'],
                    'loaded_items': truck_state['loaded_items'],
                    'utilization': {
                        'floor_area_rate': utilization_rate,
                        'volume_rate': utilization_rate,
                        'weight_rate': 0
                    }
                }
                final_truck_plans.append(truck_plan)
        
        # 積み残し警告
        if remaining_demands:
            for demand in remaining_demands:
                warnings.append(
                    f"❌ 積み残し: {demand['product_code']} ({demand['num_containers']}容器)"
                )
        
        return {
            'trucks': final_truck_plans,
            'total_trips': len(final_truck_plans),
            'warnings': warnings,
            'remaining_demands': remaining_demands
        }
    
    def _get_priority_products(self, truck_info) -> List[str]:
        """トラックの優先積載製品を取得"""
        priority_products_str = truck_info.get('priority_product_codes') or truck_info.get('priority_products', '')
        if priority_products_str and not pd.isna(priority_products_str):
            return [p.strip() for p in str(priority_products_str).split(',')]
        return []
    
    def _sort_demands_by_priority(self, demands, truck_states):
        """製品を優先度順にソート"""
        def get_priority(demand):
            product_code = demand['product_code']
            
            # 優先積載製品に指定されている場合は最優先
            for truck_id, truck_state in truck_states.items():
                if product_code in truck_state['priority_products']:
                    return (0, truck_id, product_code)
            
            # トラック制約がある場合は次
            if demand.get('truck_ids'):
                return (1, demand['truck_ids'][0], product_code)
            
            # その他
            return (2, 0, product_code)
        
        return sorted(demands, key=get_priority)
    
    def _sort_candidate_trucks(self, candidate_trucks, demand, truck_states):
        """候補トラックを優先順位でソート"""
        product_code = demand['product_code']
        container_id = demand['container_id']
        
        def get_truck_priority(truck_id):
            truck_state = truck_states[truck_id]
            
            # 1. 優先積載製品に指定されている
            if product_code in truck_state['priority_products']:
                return (0, -truck_state['remaining_floor_area'])
            
            # 2. 同容器が既に積載されている
            if container_id in truck_state['loaded_container_ids']:
                return (1, -truck_state['remaining_floor_area'])
            
            # 3. 空き容量が大きい
            return (2, -truck_state['remaining_floor_area'])
        
        return sorted(candidate_trucks, key=get_truck_priority)
    
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
            'unloaded_count': 0,  # 互換性のため
            'use_non_default_truck': use_non_default,
            'status': '正常' if total_warnings == 0 else '警告あり'
        }
