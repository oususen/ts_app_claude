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

        # フィルター - デフォルトを過去10日間に変更
        st.subheader("🔍 フィルター")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            start_date = st.date_input(
                "納期（開始）",
                value=date.today() - timedelta(days=10),
                key="progress_start_date"
            )
        
        with col_f2:
            end_date = st.date_input(
                "納期（終了）",
                value=date.today()+timedelta(days=10),
                key="progress_end_date"
            )
        
        with col_f3:
            status_filter = st.multiselect(
                "ステータス",
                options=['未出荷', '計画済', '一部出荷', '出荷完了'],
                default=['未出荷', '計画済', '一部出荷'],
                key="progress_status_filter"
            )
        
        # 進度データ取得
        try:
            progress_df = self.service.get_delivery_progress(start_date, end_date)
            
            if not progress_df.empty:
                # ステータスフィルター適用
                if status_filter:
                    progress_df = progress_df[progress_df['status'].isin(status_filter)]
                
                # 表示形式選択を追加
                st.subheader("📋 表示形式")
                view_mode = st.radio(
                    "表示モード",
                    options=['一覧表示', 'マトリックス表示（日付×製品）'],
                    horizontal=True,
                    key="view_mode_selector"
                )
                
                if view_mode == 'マトリックス表示（日付×製品）':
                    self._show_matrix_view(progress_df)
                else:
                    # 既存の一覧表示
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
                    display_columns = ['urgency', 'order_id', 'product_code', 'product_name',
                                     'customer_name', 'delivery_date', 'order_quantity']
                    
                    # planned_quantityカラムがあれば追加
                    if 'planned_quantity' in progress_df.columns:
                        display_columns.append('planned_quantity')
                    
                    display_columns.extend(['shipped_quantity', 'remaining_quantity', 'status'])
                    
                    display_df = progress_df[display_columns].copy()
                    
                    # カラム名を日本語に変更
                    column_names = {
                        'urgency': '緊急度',
                        'order_id': 'オーダーID',
                        'product_code': '製品コード',
                        'product_name': '製品名',
                        'customer_name': '得意先',
                        'delivery_date': '納期',
                        'order_quantity': '受注数',
                        'planned_quantity': '計画数',
                        'shipped_quantity': '出荷済',
                        'remaining_quantity': '残数',
                        'status': 'ステータス'
                    }
                    
                    display_df.columns = [column_names.get(col, col) for col in display_df.columns]
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "納期": st.column_config.DateColumn("納期", format="YYYY-MM-DD"),
                        }
                    )
                    
                    # 詳細編集・出荷実績入力
                    st.subheader("📝 詳細編集・出荷実績入力")
                    
                    if not progress_df.empty:
                        # オーダー選択 - 製品コード表示
                        order_options = {
                            f"{row['order_id']} - {row['product_code']} ({row['delivery_date']})": row['id']
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
                            
                            # タブで編集と出荷実績を分離
                            edit_tab, shipment_tab = st.tabs(["📝 進度編集", "📦 出荷実績入力"])
                            
                            with edit_tab:
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
                                            options=['未出荷', '計画済', '一部出荷', '出荷完了', 'キャンセル'],
                                            index=['未出荷', '計画済', '一部出荷', '出荷完了', 'キャンセル'].index(progress_row['status']) if progress_row['status'] in ['未出荷', '計画済', '一部出荷', '出荷完了', 'キャンセル'] else 0,
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
                            
                            # 出荷実績入力タブ
                            with shipment_tab:
                                # 現在の出荷状況を表示
                                st.info(f"""
                                **現在の状況:**
                                - 受注数: {progress_row.get('order_quantity', 0)}
                                - 計画数: {progress_row.get('planned_quantity', 0)}
                                - 出荷済: {progress_row.get('shipped_quantity', 0)}
                                - 残数: {progress_row.get('remaining_quantity', 0)}
                                """)
                                
                                with st.form(f"shipment_form_{progress_id}"):
                                    st.write("**出荷実績を入力**")
                                    
                                    col_s1, col_s2 = st.columns(2)
                                    
                                    with col_s1:
                                        shipment_date = st.date_input(
                                            "出荷日 *",
                                            value=date.today(),
                                            key=f"ship_date_{progress_id}"
                                        )
                                        
                                        # トラック選択
                                        try:
                                            trucks_df = self.service.get_trucks()
                                            
                                            if not trucks_df.empty:
                                                truck_options = dict(zip(trucks_df['name'], trucks_df['id']))
                                                selected_truck = st.selectbox(
                                                    "使用トラック *",
                                                    options=list(truck_options.keys()),
                                                    key=f"ship_truck_{progress_id}"
                                                )
                                                truck_id = truck_options[selected_truck]
                                            else:
                                                st.warning("トラックが登録されていません")
                                                truck_id = None
                                        except:
                                            st.warning("トラック情報の取得に失敗しました")
                                            truck_id = None
                                        
                                        remaining_qty = int(progress_row.get('remaining_quantity', 0))
                                        if remaining_qty > 0:
                                            shipped_quantity = st.number_input(
                                                "出荷数量 *",
                                                min_value=1,
                                                max_value=remaining_qty,
                                                value=min(100, remaining_qty),
                                                key=f"ship_qty_{progress_id}"
                                            )
                                        else:
                                            st.warning("出荷可能な数量がありません")
                                            shipped_quantity = 0
                                    
                                    with col_s2:
                                        driver_name = st.text_input(
                                            "ドライバー名",
                                            key=f"driver_{progress_id}"
                                        )
                                        
                                        actual_departure = st.time_input(
                                            "実出発時刻",
                                            key=f"dep_time_{progress_id}"
                                        )
                                        
                                        actual_arrival = st.time_input(
                                            "実到着時刻",
                                            key=f"arr_time_{progress_id}"
                                        )
                                        
                                        shipment_notes = st.text_area(
                                            "備考",
                                            key=f"ship_notes_{progress_id}"
                                        )
                                    
                                    ship_submitted = st.form_submit_button("📦 出荷実績を登録", type="primary")
                                    
                                    if ship_submitted:
                                        if not truck_id:
                                            st.error("トラックを選択してください")
                                        elif shipped_quantity <= 0:
                                            st.error("出荷数量を入力してください")
                                        else:
                                            shipment_data = {
                                                'progress_id': progress_id,
                                                'truck_id': truck_id,
                                                'shipment_date': shipment_date,
                                                'shipped_quantity': shipped_quantity,
                                                'driver_name': driver_name,
                                                'actual_departure_time': actual_departure,
                                                'actual_arrival_time': actual_arrival,
                                                'notes': shipment_notes
                                            }
                                            
                                            success = self.service.create_shipment_record(shipment_data)
                                            if success:
                                                st.success(f"✅ 出荷実績を登録しました（{shipped_quantity}個）")
                                                st.balloons()
                                                st.rerun()
                                            else:
                                                st.error("❌ 出荷実績登録に失敗しました")
                            
                            # 削除ボタンは外に配置
                            st.markdown("---")
                            col_del1, col_del2 = st.columns([1, 5])
                            with col_del1:
                                if st.button(f"🗑️ 削除", key=f"delete_progress_{progress_id}", type="secondary"):
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
    
    def _show_matrix_view(self, progress_df: pd.DataFrame):
        """マトリックス表示（横軸=日付、縦軸=製品コード×状態）- 編集可能"""
        
        # 製品名マッピング作成
        product_names = progress_df.groupby('product_code')['product_name'].first().to_dict()
        
        # 製品コード一覧を取得
        product_codes = sorted(progress_df['product_code'].unique())
        
        # 日付一覧を取得（文字列形式）
        dates = sorted(progress_df['delivery_date'].unique())
        date_columns = [d.strftime('%m月%d日') for d in dates]
        
        st.write(f"**製品数**: {len(product_codes)}")
        st.write(f"**日付数**: {len(dates)}")
        
        # オーダーIDマッピング（更新用）
        order_mapping = {}  # {(product_code, date_str): order_id}
        for _, row in progress_df.iterrows():
            key = (row['product_code'], row['delivery_date'].strftime('%m月%d日'))
            order_mapping[key] = row['id']
        
        # 結果を格納するリスト
        result_rows = []
        
        for product_code in product_codes:
            product_data = progress_df[progress_df['product_code'] == product_code]
            
            # 各指標の行を作成
            order_row = {'製品コード': product_code, '状態': '受注数', 'row_type': 'order'}
            planned_row = {'製品コード': '', '状態': '納入計画数', 'row_type': 'planned'}
            shipped_row = {'製品コード': '', '状態': '納入実績', 'row_type': 'shipped'}
            progress_row = {'製品コード': '', '状態': '進度', 'row_type': 'progress'}
            
            cumulative_order = 0
            cumulative_planned = 0
            cumulative_shipped = 0
            
            for idx, (date_obj, date_str) in enumerate(zip(dates, date_columns)):
                # その日のデータを取得
                day_data = product_data[product_data['delivery_date'] == date_obj]
                
                if not day_data.empty:
                    row = day_data.iloc[0]
                    
                    order_qty = int(row['order_quantity']) if pd.notna(row['order_quantity']) else 0
                    
                    # planned_quantity の安全な取得
                    if 'planned_quantity' in day_data.columns and pd.notna(row['planned_quantity']):
                        planned_qty = int(row['planned_quantity'])
                    else:
                        planned_qty = 0
                    
                    # shipped_quantity の安全な取得
                    if 'shipped_quantity' in day_data.columns and pd.notna(row['shipped_quantity']):
                        shipped_qty = int(row['shipped_quantity'])
                    else:
                        shipped_qty = 0
                    
                    cumulative_order += order_qty
                    cumulative_planned += planned_qty
                    cumulative_shipped += shipped_qty
                    
                    order_row[date_str] = order_qty
                    planned_row[date_str] = planned_qty
                    shipped_row[date_str] = shipped_qty
                else:
                    order_row[date_str] = 0
                    planned_row[date_str] = 0
                    shipped_row[date_str] = 0
                
                # 進度 = 累計出荷 - 累計受注
                progress = cumulative_shipped - cumulative_order
                progress_row[date_str] = int(progress)
            
            result_rows.extend([order_row, planned_row, shipped_row, progress_row])
        
        # DataFrameに変換
        result_df = pd.DataFrame(result_rows)
        
        # カラムの順序を整理
        columns = ['製品コード', '状態', 'row_type'] + date_columns
        result_df = result_df[columns]
        
        st.write("---")
        st.write("**日付×製品マトリックス（受注・計画・実績・進度）**")
        
        # 修正: 列を固定表示（製品コードと状態列を固定）
        edited_df = st.data_editor(
            result_df,
            use_container_width=True,
            hide_index=True,
            disabled=['製品コード', '状態', 'row_type'],  # 編集不可カラム
            column_config={
                "製品コード": st.column_config.TextColumn(
                    "製品コード", 
                    width="medium",
                    pinned=True
                ),
                "状態": st.column_config.TextColumn(
                    "状態", 
                    width="small",
                    pinned=True
                ),
                "row_type": None,  # 非表示
                **{col: st.column_config.NumberColumn(col, min_value=0, step=1) for col in date_columns}
            },
            key="matrix_editor"
        )
        
        # 保存ボタン
        col_save1, col_save2 = st.columns([1, 5])
        
        with col_save1:
            if st.button("💾 変更を保存", type="primary", use_container_width=True):
                # 変更を検出して保存
                changes_saved = self._save_matrix_changes(
                    original_df=result_df,
                    edited_df=edited_df,
                    order_mapping=order_mapping,
                    product_codes=product_codes,
                    dates=dates,
                    date_columns=date_columns,
                    progress_df=progress_df
                )
                
                if changes_saved:
                    st.success("✅ 変更を保存しました")
                    st.rerun()
                else:
                    st.info("変更はありませんでした")
        
        with col_save2:
            st.caption("※ 「進度」行は自動計算されます（累計出荷 - 累計受注）")
        
        # 説明
        with st.expander("📋 表の見方"):
            st.write("""
            **各行の意味:**
            - **受注数**: その日の受注数量（編集不可）
            - **納入計画数**: 積載計画で設定された数量（編集可）
            - **納入実績**: 実際に出荷した数量（編集可）
            - **進度**: 累計出荷 - 累計受注（自動計算、マイナスは未納分）
            
            **編集方法:**
            1. 「納入計画数」または「納入実績」のセルをダブルクリック
            2. 数値を入力
            3. 「💾 変更を保存」ボタンをクリック
            """)

    def _save_matrix_changes(self, original_df, edited_df, order_mapping, 
                            product_codes, dates, date_columns, progress_df):
        """マトリックスの変更をデータベースに保存"""
        
        changes_made = False
        
        for product_code in product_codes:
            for date_obj, date_str in zip(dates, date_columns):
                # オーダーIDを取得
                order_key = (product_code, date_str)
                if order_key not in order_mapping:
                    continue
                
                order_id = order_mapping[order_key]
                
                # 元データを取得
                original_data = progress_df[
                    (progress_df['product_code'] == product_code) & 
                    (progress_df['delivery_date'] == date_obj)
                ]
                
                if original_data.empty:
                    continue
                
                original_planned = int(original_data['planned_quantity'].iloc[0]) if 'planned_quantity' in original_data.columns else 0
                original_shipped = int(original_data['shipped_quantity'].iloc[0])
                
                # 編集後のデータを取得
                planned_rows = edited_df[
                    (edited_df['row_type'] == 'planned') &
                    ((edited_df['製品コード'] == product_code) | (edited_df['製品コード'] == ''))
                ]
                
                shipped_rows = edited_df[
                    (edited_df['row_type'] == 'shipped') &
                    ((edited_df['製品コード'] == product_code) | (edited_df['製品コード'] == ''))
                ]
                
                # 納入計画数の変更チェック
                if not planned_rows.empty and date_str in planned_rows.columns:
                    # 製品コードでフィルタ
                    product_planned_rows = planned_rows[
                        (planned_rows.index > edited_df[edited_df['製品コード'] == product_code].index.min()) &
                        (planned_rows.index < edited_df[edited_df['製品コード'] == product_code].index.min() + 4)
                    ]
                    
                    if not product_planned_rows.empty:
                        new_planned = int(product_planned_rows.iloc[0][date_str]) if pd.notna(product_planned_rows.iloc[0][date_str]) else 0
                        
                        if new_planned != original_planned:
                            update_data = {'planned_quantity': new_planned}
                            self.service.update_delivery_progress(order_id, update_data)
                            changes_made = True
                
                # 納入実績の変更チェック
                if not shipped_rows.empty and date_str in shipped_rows.columns:
                    # 製品コードでフィルタ
                    product_shipped_rows = shipped_rows[
                        (shipped_rows.index > edited_df[edited_df['製品コード'] == product_code].index.min()) &
                        (shipped_rows.index < edited_df[edited_df['製品コード'] == product_code].index.min() + 4)
                    ]
                    
                    if not product_shipped_rows.empty:
                        new_shipped = int(product_shipped_rows.iloc[0][date_str]) if pd.notna(product_shipped_rows.iloc[0][date_str]) else 0
                        
                        diff = new_shipped - original_shipped
                        
                        if diff != 0:
                            # 出荷実績として登録
                            shipment_data = {
                                'progress_id': order_id,
                                'truck_id': 1,  # デフォルトトラック
                                'shipment_date': date_obj,
                                'shipped_quantity': abs(diff),
                                'driver_name': 'マトリックス入力',
                                'actual_departure_time': None,
                                'actual_arrival_time': None,
                                'notes': 'マトリックスから直接入力'
                            }
                            
                            if diff > 0:
                                self.service.create_shipment_record(shipment_data)
                                changes_made = True
        
        return changes_made

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
        st.header("📦 出荷実績一覧")
        
        # フィルター
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            filter_start = st.date_input(
                "出荷日（開始）",
                value=date.today() - timedelta(days=7),
                key="shipment_start_filter"
            )
        
        with col_f2:
            filter_end = st.date_input(
                "出荷日（終了）",
                value=date.today(),
                key="shipment_end_filter"
            )
        
        try:
            shipment_df = self.service.get_shipment_records()
            
            if not shipment_df.empty:
                # 日付フィルター適用
                shipment_df['shipment_date'] = pd.to_datetime(shipment_df['shipment_date']).dt.date
                filtered_df = shipment_df[
                    (shipment_df['shipment_date'] >= filter_start) &
                    (shipment_df['shipment_date'] <= filter_end)
                ]
                
                if not filtered_df.empty:
                    # 表示用データフレーム
                    display_cols = ['shipment_date', 'order_id', 'product_code', 'product_name', 
                                  'truck_name', 'shipped_quantity', 'driver_name']
                    
                    # カラムが存在するかチェック
                    available_cols = [col for col in display_cols if col in filtered_df.columns]
                    
                    if 'num_containers' in filtered_df.columns:
                        available_cols.append('num_containers')
                    
                    display_df = filtered_df[available_cols].copy()
                    
                    # カラム名を日本語に
                    column_mapping = {
                        'shipment_date': '出荷日',
                        'order_id': 'オーダーID',
                        'product_code': '製品コード',
                        'product_name': '製品名',
                        'truck_name': 'トラック',
                        'shipped_quantity': '出荷数量',
                        'num_containers': '容器数',
                        'driver_name': 'ドライバー'
                    }
                    
                    display_df.columns = [column_mapping.get(col, col) for col in display_df.columns]
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "出荷日": st.column_config.DateColumn("出荷日", format="YYYY-MM-DD"),
                        }
                    )
                    
                    # 統計情報
                    st.subheader("📊 出荷統計")
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    
                    with col_stat1:
                        total_shipments = len(filtered_df)
                        st.metric("総出荷回数", f"{total_shipments}回")
                    
                    with col_stat2:
                        total_quantity = filtered_df['shipped_quantity'].sum()
                        st.metric("総出荷数量", f"{total_quantity:,.0f}個")
                    
                    with col_stat3:
                        unique_products = filtered_df['product_id'].nunique()
                        st.metric("出荷製品種類", f"{unique_products}種")
                else:
                    st.info("指定期間内の出荷実績がありません")
            else:
                st.info("出荷実績がありません")
        
        except Exception as e:
            st.error(f"出荷実績取得エラー: {e}")