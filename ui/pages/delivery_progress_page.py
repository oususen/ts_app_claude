# app/ui/pages/delivery_progress_page.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta

class DeliveryProgressPage:
    """納入進度管理ページ"""
    
    def __init__(self, transport_service):
        self.service = transport_service
    
    def show(self):
        """ページ表示"""
        st.title("📋 納入進度管理")
        st.write("受注から出荷までの進捗を管理します。")
        
        tab1, tab2, tab3 = st.tabs(["📊 進度一覧", "➕ 新規登録", "📦 出荷実績"])
        
        with tab1:
            self._show_progress_list()
        with tab2:
            self._show_progress_registration()
        with tab3:
            self._show_shipment_records()
    
    def _show_progress_list(self):
        """進度一覧表示"""
        st.header("📊 納入進度一覧")
        
        # サマリー表示
        try:
            summary = self.service.get_progress_summary()
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("総オーダー数", summary.get('total_orders', 0))
            with col2:
                st.metric("未出荷", summary.get('unshipped', 0))
            with col3:
                st.metric("一部出荷", summary.get('partial', 0))
            with col4:
                st.metric("遅延", summary.get('delayed', 0), delta_color="inverse")
            with col5:
                st.metric("緊急", summary.get('urgent', 0), delta_color="inverse")
        
        except Exception as e:
            st.warning(f"サマリー取得エラー: {e}")
        
        # フィルター
        st.subheader("🔍 フィルター")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            start_date = st.date_input(
                "納期（開始）",
                value=date.today(),
                key="progress_start_date"
            )
        
        with col_f2:
            end_date = st.date_input(
                "納期（終了）",
                value=date.today() + timedelta(days=30),
                key="progress_end_date"
            )
        
        with col_f3:
            status_filter = st.multiselect(
                "ステータス",
                options=['未出荷', '一部出荷', '出荷完了'],
                default=['未出荷', '一部出荷'],
                key="progress_status_filter"
            )
        
        # 進度データ取得
        try:
            progress_df = self.service.get_delivery_progress(start_date, end_date)
            
            if not progress_df.empty:
                # ステータスフィルター適用
                if status_filter:
                    progress_df = progress_df[progress_df['status'].isin(status_filter)]
                
                # 緊急度フラグ追加
                progress_df['days_to_delivery'] = (
                    pd.to_datetime(progress_df['delivery_date']) - pd.Timestamp(date.today())
                ).dt.days
                
                progress_df['urgency'] = progress_df.apply(
                    lambda row: '🔴遅延' if row['days_to_delivery'] < 0 and row['status'] != '出荷完了'
                    else '🟡緊急' if 0 <= row['days_to_delivery'] <= 3 and row['status'] != '出荷完了'
                    else '🟢',
                    axis=1
                )
                
                # 表示用データフレーム
                display_df = progress_df[[
                    'urgency', 'order_id', 'product_code', 'product_name',
                    'customer_name', 'delivery_date', 'order_quantity',
                    'shipped_quantity', 'remaining_quantity', 'status'
                ]].copy()
                
                display_df.columns = [
                    '緊急度', 'オーダーID', '製品コード', '製品名',
                    '得意先', '納期', '受注数', '出荷済', '残数', 'ステータス'
                ]
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "納期": st.column_config.DateColumn("納期", format="YYYY-MM-DD"),
                    }
                )
                
                # 詳細編集
                st.subheader("📝 詳細編集")
                
                if not progress_df.empty:
                    # オーダー選択
                    order_options = {
                        f"{row['order_id']} - {row['product_name']} ({row['delivery_date']})": row['id']
                        for _, row in progress_df.iterrows()
                    }
                    
                    selected_order_key = st.selectbox(
                        "編集するオーダーを選択",
                        options=list(order_options.keys()),
                        key="progress_edit_selector"
                    )
                    
                    if selected_order_key:
                        progress_id = order_options[selected_order_key]
                        progress_row = progress_df[progress_df['id'] == progress_id].iloc[0]
                        
                        with st.form(f"edit_progress_{progress_id}"):
                            st.write("**進度情報を編集**")
                            
                            col_e1, col_e2 = st.columns(2)
                            
                            with col_e1:
                                new_delivery_date = st.date_input(
                                    "納期",
                                    value=progress_row['delivery_date'],
                                    key=f"delivery_{progress_id}"
                                )
                                new_priority = st.number_input(
                                    "優先度（1-10）",
                                    min_value=1,
                                    max_value=10,
                                    value=int(progress_row.get('priority', 5)),
                                    key=f"priority_{progress_id}"
                                )
                            
                            with col_e2:
                                new_status = st.selectbox(
                                    "ステータス",
                                    options=['未出荷', '一部出荷', '出荷完了', 'キャンセル'],
                                    index=['未出荷', '一部出荷', '出荷完了', 'キャンセル'].index(progress_row['status']),
                                    key=f"status_{progress_id}"
                                )
                                new_notes = st.text_area(
                                    "備考",
                                    value=progress_row.get('notes', '') or '',
                                    key=f"notes_{progress_id}"
                                )
                            
                            submitted = st.form_submit_button("💾 更新", type="primary")
                            
                            if submitted:
                                update_data = {
                                    'delivery_date': new_delivery_date,
                                    'priority': new_priority,
                                    'status': new_status,
                                    'notes': new_notes
                                }
                                
                                success = self.service.update_delivery_progress(progress_id, update_data)
                                if success:
                                    st.success("進度を更新しました")
                                    st.rerun()
                                else:
                                    st.error("進度更新に失敗しました")
                        
                        # 削除ボタン
                        if st.button(f"🗑️ 削除", key=f"delete_progress_{progress_id}"):
                            success = self.service.delete_delivery_progress(progress_id)
                            if success:
                                st.success("進度を削除しました")
                                st.rerun()
                            else:
                                st.error("進度削除に失敗しました")
            
            else:
                st.info("指定期間内に納入進度データがありません")
        
        except Exception as e:
            st.error(f"進度一覧エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _show_progress_registration(self):
        """新規登録"""
        st.header("➕ 新規納入進度登録")
        
        with st.form("create_progress_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**オーダー情報**")
                order_id = st.text_input("オーダーID *", placeholder="例: ORD-2025-001")
                
                # 製品選択
                try:
                    products = self.service.product_repo.get_all_products()
                    if not products.empty:
                        product_options = {
                            f"{row['product_code']} - {row['product_name']}": row['id']
                            for _, row in products.iterrows()
                        }
                        selected_product = st.selectbox("製品 *", options=list(product_options.keys()))
                        product_id = product_options[selected_product]
                    else:
                        st.warning("製品が登録されていません")
                        product_id = None
                except:
                    st.error("製品データ取得エラー")
                    product_id = None
                
                order_date = st.date_input("受注日 *", value=date.today())
                delivery_date = st.date_input("納期 *", value=date.today() + timedelta(days=7))
                order_quantity = st.number_input("受注数量 *", min_value=1, value=100, step=1)
            
            with col2:
                st.write("**得意先情報**")
                customer_code = st.text_input("得意先コード", placeholder="例: C001")
                customer_name = st.text_input("得意先名", placeholder="例: 株式会社〇〇")
                delivery_location = st.text_input("納入先", placeholder="例: 東京工場")
                priority = st.number_input("優先度（1-10）", min_value=1, max_value=10, value=5)
                notes = st.text_area("備考")
            
            submitted = st.form_submit_button("➕ 登録", type="primary")
            
            if submitted:
                if not order_id or not product_id:
                    st.error("オーダーIDと製品は必須です")
                else:
                    progress_data = {
                        'order_id': order_id,
                        'product_id': product_id,
                        'order_date': order_date,
                        'delivery_date': delivery_date,
                        'order_quantity': order_quantity,
                        'customer_code': customer_code,
                        'customer_name': customer_name,
                        'delivery_location': delivery_location,
                        'priority': priority,
                        'notes': notes
                    }
                    
                    progress_id = self.service.create_delivery_progress(progress_data)
                    if progress_id > 0:
                        st.success(f"納入進度を登録しました（ID: {progress_id}）")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("納入進度登録に失敗しました")
    
    def _show_shipment_records(self):
        """出荷実績表示"""
        st.header("📦 出荷実績")
        
        try:
            shipment_df = self.service.get_shipment_records()
            
            if not shipment_df.empty:
                st.dataframe(
                    shipment_df[[
                        'order_id', 'product_code', 'product_name', 'truck_name',
                        'shipment_date', 'shipped_quantity', 'num_containers'
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "shipment_date": st.column_config.DateColumn("出荷日", format="YYYY-MM-DD"),
                    }
                )
            else:
                st.info("出荷実績がありません")
        
        except Exception as e:
            st.error(f"出荷実績取得エラー: {e}")
            import traceback
            st.code(traceback.format_exc())