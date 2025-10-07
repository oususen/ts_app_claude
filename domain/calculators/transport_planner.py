# app/domain/calculators/transport_planner.py
from typing import List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict
import pandas as pd

# transport_planner.py に追加する修正例

class TransportPlanner:
    """運送計画計算機 - カレンダー対応版"""
    
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
        """
        カレンダーを考慮した積載計画作成
        """
        
        self.calendar_repo = calendar_repo
        
        # ✅ 営業日のみで計画期間を構築
        working_dates = []
        current_date = start_date
        
        while len(working_dates) < days:
            if not calendar_repo or calendar_repo.is_working_day(current_date):
                working_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # 1. データ準備
        container_map = {c.id: c for c in containers}
        truck_map = {int(row['id']): row for _, row in trucks_df.iterrows()}
        
        # 2. 営業日ベースでタスク作成
        daily_tasks = self._create_daily_tasks_with_calendar(
            orders_df, products_df, container_map, truck_map, 
            working_dates, calendar_repo
        )
        
        # 残りは同じロジック...
        daily_plans = {}
        unloaded_tasks = []
        
        for working_date in working_dates:
            date_str = working_date.strftime('%Y-%m-%d')
            
            if date_str not in daily_tasks:
                daily_plans[date_str] = {'trucks': [], 'total_trips': 0, 'warnings': []}
                continue
            
            plan, remaining = self._plan_single_day(
                daily_tasks[date_str],
                container_map,
                truck_map,
                truck_container_rules,
                working_date
            )
            
            daily_plans[date_str] = plan
            
            if remaining:
                unloaded_tasks.extend([(working_date, task) for task in remaining])
        
        # 前倒し処理も営業日を考慮
        if unloaded_tasks:
            daily_plans, final_unloaded = self._reschedule_forward_with_calendar(
                unloaded_tasks, daily_plans, products_df, container_map, 
                truck_map, truck_container_rules, working_dates[0], calendar_repo
            )
        else:
            final_unloaded = []
        
        summary = self._create_summary(daily_plans, final_unloaded)
        
        return {
            'daily_plans': daily_plans,
            'summary': summary,
            'unloaded_tasks': final_unloaded,
            'period': f"{working_dates[0].strftime('%Y-%m-%d')} ~ {working_dates[-1].strftime('%Y-%m-%d')}",
            'working_dates': [d.strftime('%Y-%m-%d') for d in working_dates]
        }
    
    def _create_daily_tasks_with_calendar(self, orders_df, products_df, container_map, 
                                         truck_map, working_dates, calendar_repo):
        """営業日を考慮したタスク作成"""
        daily_tasks = defaultdict(list)
        product_map = {int(row['id']): row for _, row in products_df.iterrows()}
        
        for _, order in orders_df.iterrows():
            product_id = int(order['product_id'])
            delivery_date = order.get('delivery_date') or order.get('instruction_date')
            quantity = int(order.get('order_quantity') or order.get('instruction_quantity', 0))
            
            if not delivery_date or quantity <= 0 or product_id not in product_map:
                continue
            
            product = product_map[product_id]
            container_id = product.get('used_container_id')
            used_truck_ids = product.get('used_truck_ids')
            
            if not container_id or pd.isna(container_id):
                continue
            
            # トラックIDリスト取得
            if used_truck_ids and not pd.isna(used_truck_ids):
                truck_ids = [int(tid.strip()) for tid in str(used_truck_ids).split(',')]
            else:
                truck_ids = [int(tid) for tid, truck in truck_map.items() 
                           if truck.get('default_use', False)]
            
            if not truck_ids:
                continue
            
            # ✅ 納期に間に合う & 営業日のトラックを選定
            valid_truck_ids = []
            for truck_id in truck_ids:
                if truck_id in truck_map:
                    truck = truck_map[truck_id]
                    offset = int(truck.get('arrival_day_offset', 0))
                    
                    # 積載日 = 納期 - オフセット
                    loading_date = delivery_date - timedelta(days=offset)
                    
                    # ✅ 積載日が営業日かチェック
                    if calendar_repo:
                        # 最寄りの営業日を探す
                        check_date = loading_date
                        for _ in range(7):  # 最大7日前まで遡る
                            if calendar_repo.is_working_day(check_date):
                                loading_date = check_date
                                break
                            check_date -= timedelta(days=1)
                    
                    # 到着日チェック
                    arrival_date = loading_date + timedelta(days=offset)
                    
                    if arrival_date <= delivery_date:
                        valid_truck_ids.append((truck_id, loading_date, offset))
            
            if not valid_truck_ids:
                continue
            
            # 当日着優先でソート
            valid_truck_ids.sort(key=lambda x: (x[2], x[1]))
            best_truck_id, best_loading_date, best_offset = valid_truck_ids[0]
            
            # 容器数計算
            capacity = product.get('capacity', 1)
            num_containers = (quantity + capacity - 1) // capacity
            
            # 営業日内のみ計画
            if best_loading_date in working_dates:
                date_str = best_loading_date.strftime('%Y-%m-%d')
                
                daily_tasks[date_str].append({
                    'product_id': product_id,
                    'product_code': product.get('product_code', ''),
                    'product_name': product.get('product_name', ''),
                    'container_id': int(container_id),
                    'truck_ids': [tid for tid, _, _ in valid_truck_ids],
                    'num_containers': num_containers,
                    'total_quantity': quantity,
                    'delivery_date': delivery_date,
                    'can_advance': bool(product.get('can_advance', False)),
                    'original_date': best_loading_date,
                    'capacity': capacity,
                    'arrival_offset': best_offset
                })
        
        return dict(daily_tasks)
    
    def _reschedule_forward_with_calendar(self, unloaded_tasks, daily_plans, products_df, 
                                         container_map, truck_map, truck_container_rules, 
                                         start_date, calendar_repo):
        """営業日を考慮した前倒し処理"""
        
        product_map = {int(row['id']): row for _, row in products_df.iterrows()}
        final_unloaded = []
        
        for original_date, task in unloaded_tasks:
            product_id = task['product_id']
            
            if product_id in product_map:
                can_advance = bool(product_map[product_id].get('can_advance', False))
            else:
                can_advance = False
            
            if not can_advance:
                final_unloaded.append(task)
                continue
            
            # ✅ 営業日のみで前倒し試行
            rescheduled = False
            for days_back in range(1, 8):
                new_date = original_date - timedelta(days=days_back)
                
                if new_date < start_date:
                    break
                
                # ✅ 営業日チェック
                if calendar_repo and not calendar_repo.is_working_day(new_date):
                    continue
                
                date_str = new_date.strftime('%Y-%m-%d')
                
                if date_str not in daily_plans:
                    daily_plans[date_str] = {'trucks': [], 'total_trips': 0, 'warnings': []}
                
                plan, remaining = self._plan_single_day(
                    [task],
                    container_map,
                    truck_map,
                    truck_container_rules,
                    new_date
                )
                
                if plan['trucks']:
                    daily_plans[date_str]['trucks'].extend(plan['trucks'])
                    daily_plans[date_str]['total_trips'] += len(plan['trucks'])
                    daily_plans[date_str]['warnings'].append(
                        f"📅 前倒し（営業日調整）: {task['product_code']} "
                        f"({original_date.strftime('%m/%d')} → {new_date.strftime('%m/%d')})"
                    )
                    rescheduled = True
                    break
            
            if not rescheduled:
                final_unloaded.append(task)
        
        return daily_plans, final_unloaded
   
    def _plan_single_day(self, tasks, container_map, truck_map, 
                        truck_container_rules, loading_date: date) -> Tuple[Dict, List]:
        """1日分の積載計画を作成 - 納期チェック強化版"""
        
        truck_plans = []
        remaining_tasks = []
        warnings = []
        
        # トラックごとの使用済み容量を追跡
        truck_used_space = defaultdict(lambda: defaultdict(int))
        
        # 製品ごとにグループ化
        product_tasks = defaultdict(list)
        for task in tasks:
            key = (task['product_id'], task['delivery_date'])
            product_tasks[key].append(task)
        
        # 容器数の多い順にソート
        sorted_product_tasks = sorted(
            product_tasks.items(),
            key=lambda x: (
                -sum(t['num_containers'] for t in x[1]),
                x[1][0].get('product_code', '')
            )
        )
        
        # 各製品について積載
        for (product_id, delivery_date), task_list in sorted_product_tasks:
            total_containers = sum(t['num_containers'] for t in task_list)
            remaining_containers = total_containers
            
            # ✅ 使用可能なトラックIDを取得（納期チェック付き）
            available_truck_ids = set()
            for task in task_list:
                if 'truck_ids' in task:
                    for truck_id in task['truck_ids']:
                        # 納期チェック
                        if truck_id in truck_map:
                            truck = truck_map[truck_id]
                            offset = int(truck.get('arrival_day_offset', 0))
                            arrival_date = loading_date + timedelta(days=offset)
                            
                            # ✅ 到着日 <= 納期 のみ許可
                            if arrival_date <= delivery_date:
                                available_truck_ids.add(truck_id)
            
            if not available_truck_ids:
                # 納期に間に合うトラックがない
                for task in task_list:
                    remaining_tasks.append(task)
                warnings.append(
                    f"❌ 納期遅れ: {task_list[0]['product_code']} "
                    f"(納期 {delivery_date.strftime('%m/%d')} に間に合うトラックがありません)"
                )
                continue
            
            # トラックを残容量の大きい順にソート
            sorted_trucks = self._sort_trucks_by_remaining_capacity(
                available_truck_ids, truck_map, container_map, 
                task_list[0]['container_id'], truck_used_space
            )
            
            # トラックに順番に積載
            loaded_count = 0
            for truck_id in sorted_trucks:
                if remaining_containers <= 0:
                    break
                
                if truck_id not in truck_map:
                    continue
                
                truck_info = truck_map[truck_id]
                container_id = task_list[0]['container_id']
                
                # このトラックの残容量を計算
                max_containers = self._calculate_max_containers_in_truck(
                    container_map.get(container_id),
                    truck_info['width'],
                    truck_info['depth'],
                    truck_info['height']
                )
                
                # 既に使用済みの容器数を引く
                used_containers = truck_used_space[truck_id][container_id]
                available_space = max(0, max_containers - used_containers)
                
                # 積載する容器数を決定
                containers_to_load = min(remaining_containers, available_space)
                
                if containers_to_load > 0:
                    # 積載タスク作成
                    loaded_task = task_list[0].copy()
                    loaded_task['truck_id'] = truck_id
                    loaded_task['num_containers'] = containers_to_load
                    loaded_task['total_quantity'] = containers_to_load * task_list[0].get('capacity', 1)
                    
                    # トラック計画に追加
                    truck_plan = self._find_or_create_truck_plan(
                        truck_plans, truck_id, truck_info
                    )
                    truck_plan['loaded_items'].append(loaded_task)
                    
                    # 使用済み容量を更新
                    truck_used_space[truck_id][container_id] += containers_to_load
                    
                    # 残り容器数を更新
                    remaining_containers -= containers_to_load
                    loaded_count += 1
                    
                    if loaded_count > 1:
                        warnings.append(
                            f"🚛 分散積載: {loaded_task['product_code']} "
                            f"({containers_to_load}容器をトラック{truck_info['name']}に追加積載 - "
                            f"合計{total_containers - remaining_containers}/{total_containers}容器)"
                        )
            
            # 積み残しがあれば記録
            if remaining_containers > 0:
                unloaded_task = task_list[0].copy()
                unloaded_task['num_containers'] = remaining_containers
                remaining_tasks.append(unloaded_task)
                warnings.append(
                    f"⚠️ 積載不可: {unloaded_task['product_code']} "
                    f"({remaining_containers}容器が未積載)"
                )
        
        # 各トラックの積載率を計算
        for truck_plan in truck_plans:
            truck_plan['utilization'] = self._calculate_truck_utilization(
                truck_plan['loaded_items'], 
                truck_map[truck_plan['truck_id']], 
                container_map
            )
        
        return {
            'trucks': truck_plans,
            'total_trips': len(truck_plans),
            'warnings': warnings
        }, remaining_tasks

    def _sort_trucks_by_remaining_capacity(self, truck_ids, truck_map, container_map, 
                                           container_id, truck_used_space):
        """トラックを残容量の大きい順にソート + デフォルト便優先 + 当日着優先"""
        
        container = container_map.get(container_id)
        if not container:
            return sorted(truck_ids)
        
        truck_capacities = []
        for truck_id in truck_ids:
            if truck_id not in truck_map:
                continue
            
            truck = truck_map[truck_id]
            
            # トラックの最大積載容量
            max_containers = self._calculate_max_containers_in_truck(
                container,
                truck['width'],
                truck['depth'],
                truck['height']
            )
            
            # 既に使用済みの容器数
            used_containers = truck_used_space[truck_id][container_id]
            
            # 残容量を計算
            remaining_capacity = max(0, max_containers - used_containers)
            
            # デフォルト便フラグを取得
            is_default = truck.get('default_use', False)
            
            # ✅ 到着日オフセットを取得（当日着優先）
            arrival_offset = int(truck.get('arrival_day_offset', 0))
            
            truck_capacities.append((truck_id, remaining_capacity, is_default, arrival_offset))
        
        # ✅ ソート優先順位: 当日着優先 → デフォルト便優先 → 残容量大
        truck_capacities.sort(key=lambda x: (x[3], -x[2], -x[1]))
        
        return [truck_id for truck_id, _, _, _ in truck_capacities]

    def _find_or_create_truck_plan(self, truck_plans, truck_id, truck_info):
        """トラック計画を検索または新規作成"""
        for plan in truck_plans:
            if plan['truck_id'] == truck_id:
                return plan
        
        # 新規作成
        new_plan = {
            'truck_id': truck_id,
            'truck_name': truck_info['name'],
            'loaded_items': [],
            'utilization': {'volume_rate': 0, 'weight_rate': 0}
        }
        truck_plans.append(new_plan)
        return new_plan
    
    def _calculate_max_containers_in_truck(self, container, truck_w, truck_d, truck_h) -> int:
        """トラックに積める容器の最大数を計算（水平回転のみ、縦置き不可）"""
        
        if not container:
            return 0
        
        c_w = container.width
        c_d = container.depth
        c_h = container.height
        max_stack = getattr(container, 'max_stack', 1)
        stackable = getattr(container, 'stackable', False)
        
        if not stackable:
            max_stack = 1
        
        # 水平面での配置パターンのみ
        patterns = []
        
        # パターン1: 通常配置
        num_w1 = truck_w // c_w
        num_d1 = truck_d // c_d
        physical_h1 = truck_h // c_h
        stack1 = min(physical_h1, max_stack)
        pattern1_total = num_w1 * num_d1 * stack1
        patterns.append(pattern1_total)
        
        # パターン2: 90度水平回転
        num_w2 = truck_w // c_d
        num_d2 = truck_d // c_w
        physical_h2 = truck_h // c_h
        stack2 = min(physical_h2, max_stack)
        pattern2_total = num_w2 * num_d2 * stack2
        patterns.append(pattern2_total)
        
        max_count = max(patterns) if patterns else 0
        
        return max_count
    
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
            for days_back in range(1, 8):
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
                    truck_container_rules,
                    new_date  # ✅ 積載日を渡す
                )
                
                if plan['trucks']:
                    # 積載成功
                    daily_plans[date_str]['trucks'].extend(plan['trucks'])
                    daily_plans[date_str]['total_trips'] += len(plan['trucks'])
                    daily_plans[date_str]['warnings'].append(
                        f"📅 前倒し: {task['product_code']} ({original_date.strftime('%m/%d')} → {new_date.strftime('%m/%d')})"
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