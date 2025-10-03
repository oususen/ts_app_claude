# app/domain/calculators/transport_planner.py
from typing import List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict
import pandas as pd

class TransportPlanner:
    """運送計画計算機 - 納期優先・前倒し対応版"""
    
    def calculate_loading_plan_from_orders(self,
                                          orders_df: pd.DataFrame,
                                          products_df: pd.DataFrame,
                                          containers: List[Any],
                                          trucks_df: pd.DataFrame,
                                          truck_container_rules: List[Any],
                                          start_date: date,
                                          days: int = 7) -> Dict[str, Any]:
        """
        オーダーから積載計画を作成
        
        Args:
            orders_df: 生産指示データ (instruction_date, product_id, instruction_quantity)
            products_df: 製品マスタ (id, capacity, used_container_id, used_truck_ids, can_advance)
            containers: 容器マスタ
            trucks_df: トラックマスタ
            truck_container_rules: トラック×容器ルール
            start_date: 計画開始日
            days: 計画日数
        """
        
        # 1. データ準備
        container_map = {c.id: c for c in containers}
        truck_map = {int(row['id']): row for _, row in trucks_df.iterrows()}
        
        # 2. 日別オーダーをトラック積載タスクに変換
        daily_tasks = self._create_daily_tasks(
            orders_df, products_df, container_map, truck_map, start_date, days
        )
        
        # 3. 日別に積載計画を作成
        daily_plans = {}
        unloaded_tasks = []
        
        for day in range(days):
            target_date = start_date + timedelta(days=day)
            date_str = target_date.strftime('%Y-%m-%d')
            
            if date_str not in daily_tasks:
                daily_plans[date_str] = {'trucks': [], 'total_trips': 0, 'warnings': []}
                continue
            
            # その日のタスクを積載計画に変換
            plan, remaining = self._plan_single_day(
                daily_tasks[date_str],
                container_map,
                truck_map,
                truck_container_rules
            )
            
            daily_plans[date_str] = plan
            
            # 積載できなかったタスクを前倒し候補に
            if remaining:
                unloaded_tasks.extend([(target_date, task) for task in remaining])
        
        # 4. 積載できなかったタスクを前倒し処理
        if unloaded_tasks:
            daily_plans, final_unloaded = self._reschedule_forward(
                unloaded_tasks, daily_plans, products_df, container_map, 
                truck_map, truck_container_rules, start_date
            )
        else:
            final_unloaded = []
        
        # 5. サマリー作成
        summary = self._create_summary(daily_plans, final_unloaded)
        
        return {
            'daily_plans': daily_plans,
            'summary': summary,
            'unloaded_tasks': final_unloaded,
            'period': f"{start_date.strftime('%Y-%m-%d')} ~ {(start_date + timedelta(days=days-1)).strftime('%Y-%m-%d')}"
        }
    
    def _create_daily_tasks(self, orders_df, products_df, container_map, 
                           truck_map, start_date, days) -> Dict[str, List[Dict]]:
        """オーダーを日別タスクに変換"""
        daily_tasks = defaultdict(list)
        
        # 製品情報をマップ化
        product_map = {int(row['id']): row for _, row in products_df.iterrows()}
        
        for _, order in orders_df.iterrows():
            product_id = int(order['product_id'])
            delivery_date = order['instruction_date']
            quantity = int(order['instruction_quantity'])
            
            if product_id not in product_map:
                continue
            
            product = product_map[product_id]
            container_id = product.get('used_container_id')
            used_truck_ids = product.get('used_truck_ids')
            capacity = product.get('capacity', 1)
            can_advance = bool(product.get('can_advance', False))
            
            if not container_id or pd.isna(container_id):
                continue
            
            # トラックIDリストを取得
            if used_truck_ids and not pd.isna(used_truck_ids):
                truck_ids = [int(tid.strip()) for tid in str(used_truck_ids).split(',')]
            else:
                # 使用トラック未指定の場合はデフォルト便を使用
                truck_ids = [int(tid) for tid, truck in truck_map.items() 
                           if truck.get('default_use', False)]
            
            if not truck_ids:
                continue
            
            # 容器数を計算（入り数で割り切れない場合は切り上げ）
            num_containers = (quantity + capacity - 1) // capacity
            
            # 各トラックの到着日を考慮して積載日を決定
            for truck_id in truck_ids:
                if truck_id not in truck_map:
                    continue
                
                truck = truck_map[truck_id]
                offset = int(truck.get('arrival_day_offset', 0))
                
                # 積載日 = 納期 - 到着日オフセット
                loading_date = delivery_date - timedelta(days=offset)
                
                # 計画期間内のみ
                if start_date <= loading_date < start_date + timedelta(days=days):
                    date_str = loading_date.strftime('%Y-%m-%d')
                    
                    daily_tasks[date_str].append({
                        'product_id': product_id,
                        'product_code': product.get('product_code', ''),
                        'product_name': product.get('product_name', ''),
                        'container_id': int(container_id),
                        'truck_id': truck_id,
                        'num_containers': num_containers,
                        'total_quantity': quantity,
                        'delivery_date': delivery_date,
                        'can_advance': can_advance,
                        'original_date': loading_date
                    })
        
        return dict(daily_tasks)
    
    def _plan_single_day(self, tasks, container_map, truck_map, 
                        truck_container_rules) -> Tuple[Dict, List]:
        """1日分の積載計画を作成"""
        
        # トラック別にグループ化
        truck_tasks = defaultdict(list)
        for task in tasks:
            truck_tasks[task['truck_id']].append(task)
        
        truck_plans = []
        remaining_tasks = []
        warnings = []
        
        for truck_id, truck_specific_tasks in truck_tasks.items():
            if truck_id not in truck_map:
                remaining_tasks.extend(truck_specific_tasks)
                continue
            
            truck_info = truck_map[truck_id]
            
            # このトラックに積載
            loaded, unloaded, truck_warnings = self._load_truck(
                truck_specific_tasks, truck_info, container_map, truck_container_rules
            )
            
            if loaded:
                truck_plans.append({
                    'truck_id': truck_id,
                    'truck_name': truck_info['name'],
                    'loaded_items': loaded,
                    'utilization': self._calculate_truck_utilization(loaded, truck_info, container_map)
                })
            
            remaining_tasks.extend(unloaded)
            warnings.extend(truck_warnings)
        
        return {
            'trucks': truck_plans,
            'total_trips': len(truck_plans),
            'warnings': warnings
        }, remaining_tasks
    
    def _load_truck(self, tasks, truck_info, container_map, 
                   truck_container_rules) -> Tuple[List, List, List]:
        """トラックに積載"""
        
        truck_width = int(truck_info['width'])
        truck_depth = int(truck_info['depth'])
        truck_height = int(truck_info['height'])
        max_weight = int(truck_info['max_weight'])
        
        loaded = []
        unloaded = []
        warnings = []
        
        current_weight = 0
        
        # 容器ごとの積載可能数を計算
        container_capacity_in_truck = {}
        
        for task in tasks:
            container_id = task['container_id']
            
            if container_id not in container_map:
                unloaded.append(task)
                warnings.append(f"容器ID {container_id} が見つかりません")
                continue
            
            container = container_map[container_id]
            
            # トラックに何個積めるか計算
            if container_id not in container_capacity_in_truck:
                max_containers = self._calculate_max_containers_in_truck(
                    container, truck_width, truck_depth, truck_height
                )
                container_capacity_in_truck[container_id] = {
                    'max': max_containers,
                    'used': 0
                }
            
            # 積載チェック
            needed = task['num_containers']
            available = container_capacity_in_truck[container_id]['max'] - \
                       container_capacity_in_truck[container_id]['used']
            
            if available >= needed:
                # 重量チェック
                container_weight = getattr(container, 'max_weight', 0) * needed
                if current_weight + container_weight <= max_weight:
                    loaded.append(task)
                    container_capacity_in_truck[container_id]['used'] += needed
                    current_weight += container_weight
                else:
                    unloaded.append(task)
                    warnings.append(f"重量超過: {task['product_name']}")
            else:
                unloaded.append(task)
                warnings.append(f"容積不足: {task['product_name']} (必要: {needed}, 空き: {available})")
        
        return loaded, unloaded, warnings
    
    def _calculate_max_containers_in_truck(self, container, truck_w, truck_d, truck_h) -> int:
        """トラックに積める容器の最大数を計算"""
        
        c_w = container.width
        c_d = container.depth
        c_h = container.height
        max_stack = getattr(container, 'max_stack', 1)
        stackable = getattr(container, 'stackable', False)
        
        if not stackable:
            max_stack = 1
        
        # 横方向の配置数
        num_w = truck_w // c_w
        num_d = truck_d // c_d
        
        # 縦方向の積み重ね数（物理的制約とmax_stackの小さい方）
        physical_max_h = truck_h // c_h
        actual_stack = min(physical_max_h, max_stack)
        
        return num_w * num_d * actual_stack
    
    def _calculate_truck_utilization(self, loaded_items, truck_info, container_map) -> Dict:
        """積載率を計算"""
        
        total_volume = 0
        total_weight = 0
        
        for item in loaded_items:
            container = container_map.get(item['container_id'])
            if container:
                vol = (container.width * container.depth * container.height) * item['num_containers']
                total_volume += vol
                total_weight += getattr(container, 'max_weight', 0) * item['num_containers']
        
        truck_volume = truck_info['width'] * truck_info['depth'] * truck_info['height']
        
        return {
            'volume_rate': round(total_volume / truck_volume * 100, 1) if truck_volume > 0 else 0,
            'weight_rate': round(total_weight / truck_info['max_weight'] * 100, 1) if truck_info['max_weight'] > 0 else 0
        }
    
    def _reschedule_forward(self, unloaded_tasks, daily_plans, products_df, 
                           container_map, truck_map, truck_container_rules, 
                           start_date) -> Tuple[Dict, List]:
        """前倒し処理"""
        
        product_map = {int(row['id']): row for _, row in products_df.iterrows()}
        final_unloaded = []
        
        for original_date, task in unloaded_tasks:
            product_id = task['product_id']
            
            # 前倒し可能かチェック
            if product_id in product_map:
                can_advance = bool(product_map[product_id].get('can_advance', False))
            else:
                can_advance = False
            
            if not can_advance:
                final_unloaded.append(task)
                continue
            
            # 前の日に移動を試みる
            rescheduled = False
            for days_back in range(1, 8):  # 最大7日前まで
                new_date = original_date - timedelta(days=days_back)
                
                if new_date < start_date:
                    break
                
                date_str = new_date.strftime('%Y-%m-%d')
                
                if date_str not in daily_plans:
                    daily_plans[date_str] = {'trucks': [], 'total_trips': 0, 'warnings': []}
                
                # この日に積載を試みる
                plan, remaining = self._plan_single_day(
                    [task],
                    container_map,
                    truck_map,
                    truck_container_rules
                )
                
                if plan['trucks']:
                    # 積載成功
                    daily_plans[date_str]['trucks'].extend(plan['trucks'])
                    daily_plans[date_str]['total_trips'] += len(plan['trucks'])
                    daily_plans[date_str]['warnings'].append(
                        f"前倒し: {task['product_name']} ({original_date.strftime('%m/%d')} → {new_date.strftime('%m/%d')})"
                    )
                    rescheduled = True
                    break
            
            if not rescheduled:
                final_unloaded.append(task)
        
        return daily_plans, final_unloaded
    
    def _create_summary(self, daily_plans, unloaded_tasks) -> Dict:
        """サマリー作成"""
        
        total_trips = sum(plan['total_trips'] for plan in daily_plans.values())
        total_warnings = sum(len(plan['warnings']) for plan in daily_plans.values())
        
        return {
            'total_days': len(daily_plans),
            'total_trips': total_trips,
            'total_warnings': total_warnings,
            'unloaded_count': len(unloaded_tasks),
            'status': '正常' if not unloaded_tasks else '警告あり'
        }