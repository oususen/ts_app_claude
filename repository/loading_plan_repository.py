# app/repository/loading_plan_repository.py
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Dict, Any, List
from datetime import date
from .database_manager import DatabaseManager


class LoadingPlanRepository:
    """積載計画保存・取得リポジトリ"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    def save_loading_plan(self, plan_result: Dict[str, Any], plan_name: str = None) -> int:
        """積載計画を保存 + delivery_progressに計画数を登録"""
        session = self.db.get_session()
        
        try:
            # 計画名の自動生成
            if not plan_name:
                period = plan_result.get('period', '')
                plan_name = f"積載計画_{period.split(' ~ ')[0]}"
            
            summary = plan_result['summary']
            period_parts = plan_result['period'].split(' ~ ')
            start_date = period_parts[0]
            end_date = period_parts[1]
            
            # 1. ヘッダー保存
            header_sql = text("""
                INSERT INTO loading_plan_header 
                (plan_name, start_date, end_date, total_days, total_trips, status)
                VALUES (:plan_name, :start_date, :end_date, :total_days, :total_trips, '作成済')
            """)
            
            result = session.execute(header_sql, {
                'plan_name': plan_name,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': summary['total_days'],
                'total_trips': summary['total_trips']
            })
            
            session.flush()
            plan_id = result.lastrowid
            
            # 2. 明細保存 + delivery_progress更新用のデータを収集
            daily_plans = plan_result.get('daily_plans', {})
            progress_updates = {}  # {product_id: {delivery_date: planned_quantity}}
            
            for date_str, plan in daily_plans.items():
                for truck_plan in plan.get('trucks', []):
                    trip_number = 1
                    
                    for item in truck_plan.get('loaded_items', []):
                        # 明細保存
                        detail_sql = text("""
                            INSERT INTO loading_plan_detail
                            (plan_id, loading_date, truck_id, truck_name, trip_number,
                            product_id, product_code, product_name, container_id,
                            num_containers, total_quantity, delivery_date,
                            is_advanced, original_date, volume_utilization, weight_utilization)
                            VALUES 
                            (:plan_id, :loading_date, :truck_id, :truck_name, :trip_number,
                            :product_id, :product_code, :product_name, :container_id,
                            :num_containers, :total_quantity, :delivery_date,
                            :is_advanced, :original_date, :volume_util, :weight_util)
                        """)
                        
                        is_advanced = item.get('original_date') and \
                                    item['original_date'].strftime('%Y-%m-%d') != date_str
                        
                        session.execute(detail_sql, {
                            'plan_id': plan_id,
                            'loading_date': date_str,
                            'truck_id': truck_plan['truck_id'],
                            'truck_name': truck_plan['truck_name'],
                            'trip_number': trip_number,
                            'product_id': item['product_id'],
                            'product_code': item.get('product_code', ''),
                            'product_name': item.get('product_name', ''),
                            'container_id': item['container_id'],
                            'num_containers': item['num_containers'],
                            'total_quantity': item['total_quantity'],
                            'delivery_date': item['delivery_date'],
                            'is_advanced': is_advanced,
                            'original_date': item.get('original_date'),
                            'volume_util': truck_plan['utilization']['volume_rate'],
                            'weight_util': truck_plan['utilization']['weight_rate']
                        })
                        
                        # ✅ delivery_progress更新用データを収集
                        product_id = item['product_id']
                        delivery_date = item['delivery_date']
                        quantity = item['total_quantity']
                        
                        key = (product_id, delivery_date)
                        if key not in progress_updates:
                            progress_updates[key] = {
                                'product_id': product_id,
                                'delivery_date': delivery_date,
                                'planned_quantity': 0,
                                'loading_date': date_str,
                                'truck_id': truck_plan['truck_id']
                            }
                        progress_updates[key]['planned_quantity'] += quantity
            
            # ✅ 3. delivery_progressに計画数を登録/更新
            for (product_id, delivery_date), update_data in progress_updates.items():
                # 既存のdelivery_progressレコードを検索
                check_sql = text("""
                    SELECT id, order_quantity, planned_quantity 
                    FROM delivery_progress
                    WHERE product_id = :product_id 
                    AND delivery_date = :delivery_date
                """)
                
                existing = session.execute(check_sql, {
                    'product_id': product_id,
                    'delivery_date': delivery_date
                }).fetchone()
                
                if existing:
                    # 既存レコードを更新
                    update_sql = text("""
                        UPDATE delivery_progress
                        SET planned_quantity = :planned_quantity,
                            status = CASE 
                                WHEN shipped_quantity >= order_quantity THEN '出荷完了'
                                WHEN shipped_quantity > 0 THEN '一部出荷'
                                ELSE '計画済'
                            END
                        WHERE id = :progress_id
                    """)
                    session.execute(update_sql, {
                        'progress_id': existing[0],
                        'planned_quantity': update_data['planned_quantity']
                    })
                else:
                    # 新規レコードを作成（オーダーIDを自動生成）
                    order_id = f"PLAN-{delivery_date.strftime('%Y%m%d')}-{product_id:04d}"
                    
                    insert_sql = text("""
                        INSERT INTO delivery_progress
                        (order_id, product_id, delivery_date, order_quantity, 
                        planned_quantity, shipped_quantity, status, notes)
                        VALUES
                        (:order_id, :product_id, :delivery_date, :order_quantity,
                        :planned_quantity, 0, '計画済', :notes)
                    """)
                    
                    session.execute(insert_sql, {
                        'order_id': order_id,
                        'product_id': product_id,
                        'delivery_date': delivery_date,
                        'order_quantity': update_data['planned_quantity'],
                        'planned_quantity': update_data['planned_quantity'],
                        'notes': f"積載計画ID:{plan_id} より自動登録"
                    })
            
            # 4. 警告保存
            for date_str, plan in daily_plans.items():
                for warning in plan.get('warnings', []):
                    warning_sql = text("""
                        INSERT INTO loading_plan_warnings
                        (plan_id, warning_date, warning_type, warning_message)
                        VALUES (:plan_id, :warning_date, :warning_type, :warning_message)
                    """)
                    
                    warning_type = '前倒し' if '前倒し' in warning else '容量不足'
                    
                    session.execute(warning_sql, {
                        'plan_id': plan_id,
                        'warning_date': date_str,
                        'warning_type': warning_type,
                        'warning_message': warning
                    })
            
            # 5. 積載不可アイテム保存
            unloaded_tasks = plan_result.get('unloaded_tasks', [])
            for task in unloaded_tasks:
                unloaded_sql = text("""
                    INSERT INTO loading_plan_unloaded
                    (plan_id, product_id, product_code, product_name, container_id,
                    num_containers, total_quantity, delivery_date, reason)
                    VALUES
                    (:plan_id, :product_id, :product_code, :product_name, :container_id,
                    :num_containers, :total_quantity, :delivery_date, '積載容量不足')
                """)
                
                session.execute(unloaded_sql, {
                    'plan_id': plan_id,
                    'product_id': task['product_id'],
                    'product_code': task.get('product_code', ''),
                    'product_name': task.get('product_name', ''),
                    'container_id': task.get('container_id'),
                    'num_containers': task.get('num_containers'),
                    'total_quantity': task.get('total_quantity'),
                    'delivery_date': task.get('delivery_date')
                })
            
            session.commit()
            return plan_id
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"積載計画保存エラー: {e}")
            raise
        finally:
            session.close()    

    
    def get_loading_plan(self, plan_id: int) -> Dict[str, Any]:
        """積載計画を取得"""
        session = self.db.get_session()
        
        try:
            # ヘッダー取得
            header_sql = text("""
                SELECT * FROM loading_plan_header WHERE id = :plan_id
            """)
            header_result = session.execute(header_sql, {'plan_id': plan_id}).fetchone()
            
            if not header_result:
                return None
            
            # 明細取得
            detail_sql = text("""
                SELECT * FROM loading_plan_detail 
                WHERE plan_id = :plan_id 
                ORDER BY loading_date, truck_id, trip_number
            """)
            details = session.execute(detail_sql, {'plan_id': plan_id}).fetchall()
            
            # 警告取得
            warning_sql = text("""
                SELECT * FROM loading_plan_warnings WHERE plan_id = :plan_id
            """)
            warnings = session.execute(warning_sql, {'plan_id': plan_id}).fetchall()
            
            # 積載不可取得
            unloaded_sql = text("""
                SELECT * FROM loading_plan_unloaded WHERE plan_id = :plan_id
            """)
            unloaded = session.execute(unloaded_sql, {'plan_id': plan_id}).fetchall()
            
            return {
                'header': dict(header_result._mapping),
                'details': [dict(row._mapping) for row in details],
                'warnings': [dict(row._mapping) for row in warnings],
                'unloaded': [dict(row._mapping) for row in unloaded]
            }
            
        except SQLAlchemyError as e:
            print(f"積載計画取得エラー: {e}")
            return None
        finally:
            session.close()
    
    def get_all_plans(self) -> List[Dict]:
        """全積載計画のリスト取得"""
        session = self.db.get_session()
        
        try:
            sql = text("""
                SELECT 
                    id, plan_name, start_date, end_date, 
                    total_days, total_trips, status, created_at
                FROM loading_plan_header
                ORDER BY created_at DESC
            """)
            results = session.execute(sql).fetchall()
            
            plans = []
            for row in results:
                row_dict = dict(row._mapping)
                
                # ✅ summaryキーを追加
                row_dict['summary'] = {
                    'total_days': row_dict.get('total_days', 0),
                    'total_trips': row_dict.get('total_trips', 0),
                    'status': row_dict.get('status', '不明'),
                    'total_warnings': 0,  # ヘッダーにはないのでデフォルト値
                    'unloaded_count': 0   # ヘッダーにはないのでデフォルト値
                }
                
                plans.append(row_dict)
            
            return plans
            
        except SQLAlchemyError as e:
            print(f"積載計画リスト取得エラー: {e}")
            return []
        finally:
            session.close()
    
    def delete_loading_plan(self, plan_id: int) -> bool:
        """積載計画を削除"""
        session = self.db.get_session()
        
        try:
            sql = text("DELETE FROM loading_plan_header WHERE id = :plan_id")
            session.execute(sql, {'plan_id': plan_id})
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"積載計画削除エラー: {e}")
            return False
        finally:
            session.close()