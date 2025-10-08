# app/ui/pages/transport_page.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict
from ui.components.forms import FormComponents
from ui.components.tables import TableComponents
from services.transport_service import TransportService

class TransportPage:
    """配送便計画ページ - トラック積載計画の作成画面"""
    
    def __init__(self, transport_service):
        self.service = transport_service
        self.tables = TableComponents()
    
    def show(self):
        """ページ表示"""
        st.title("🚚 配送便計画")
        st.write("オーダー情報から自動的にトラック積載計画を作成します。")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📦 積載計画作成",
            "📊 計画確認", 
            "🧰 容器管理", 
            "🚛 トラック管理",
            "🔬 検査対象製品"])
        
        with tab1:
            self._show_loading_planning()
        with tab2:
            self._show_plan_view()
        with tab3:
            self._show_container_management()
        with tab4:
            self._show_truck_management()
        with tab5:
            self._show_inspection_products()# ✅ 新しいメソッド
    def _show_inspection_products(self):
        """検査対象製品（F/$）の注文詳細表示"""
        st.header("🔬 検査対象製品一覧")
        st.write("検査区分が「F」または「$」を含む製品の注文詳細を表示します。")
        
        # 期間フィルター（3日前～2週間後）
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "開始日",
                value=date.today() - timedelta(days=3),
                key="inspection_start_date"
            )
        
        with col2:
            end_date = st.date_input(
                "終了日",
                value=date.today() + timedelta(days=14),
                key="inspection_end_date"
            )
        
        # データ取得
        from sqlalchemy import text
        
        session = self.service.db.get_session()
        
        try:
            query = text("""
                SELECT 
                    dp.delivery_date as 日付,
                    dp.order_id as オーダーID,
                    p.product_code as 製品コード,
                    p.product_name as 製品名,
                    dp.order_quantity as 受注数,
                    dp.planned_quantity as 計画数,
                    dp.shipped_quantity as 出荷済,
                    p.inspection_category as 検査区分,
                    dp.customer_name as 得意先,
                    dp.status as ステータス
                FROM delivery_progress dp
                LEFT JOIN products p ON dp.product_id = p.id
                WHERE dp.delivery_date BETWEEN :start_date AND :end_date
                    AND (p.inspection_category LIKE 'F%' OR p.inspection_category LIKE '%$%')
                    AND dp.status != 'キャンセル'
                ORDER BY dp.delivery_date, p.product_code
            """)
            
            result = session.execute(query, {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            })
            
            rows = result.fetchall()
            
            if rows:
                df = pd.DataFrame(rows, columns=result.keys())
                df['日付'] = pd.to_datetime(df['日付']).dt.date
                
                # サマリー
                st.subheader("📊 サマリー")
                col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
                
                with col_sum1:
                    st.metric("総注文数", len(df))
                # サマリー部分のみ修正
                with col_sum2:
                    # ✅ 修正: Fを含む
                    f_count = len(df[df['検査区分'].str.contains('F', na=False)])
                    st.metric("F含む（最終検査）", f_count)
                with col_sum3:
                    # ✅ 修正: $を含む（正規表現でエスケープ）
                    s_count = len(df[df['検査区分'].str.contains('\\$', regex=True, na=False)])
                    st.metric("$含む（目視検査）", s_count)
                with col_sum4:
                    st.metric("総受注数量", f"{df['受注数'].sum():,}個")
                
                # フィルター
                inspection_filter = st.multiselect(
                    "検査区分",
                    options=['F', '$'],
                    default={},  #['F', '$'],
                    key="inspection_filter"
                )
                
                if inspection_filter:
                    df = df[df['検査区分'].isin(inspection_filter)]
                
                # データ表示
                st.subheader("📋 注文詳細一覧")
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "日付": st.column_config.DateColumn("日付", format="YYYY-MM-DD"),
                    }
                )
                
                # 日付別集計
                st.subheader("📅 日付別集計")
                daily = df.groupby(['日付', '検査区分']).agg({
                    'オーダーID': 'count',
                    '受注数': 'sum'
                }).reset_index()
                daily.columns = ['日付', '検査区分', '注文件数', '合計数量']
                
                st.dataframe(daily, use_container_width=True, hide_index=True)
                
                # CSV出力
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📥 CSV ダウンロード",
                    csv,
                    f"検査対象製品_{start_date}_{end_date}.csv",
                    "text/csv"
                )
            else:
                st.info("指定期間内に検査対象製品（F/$）の注文がありません")
        
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
        finally:
            session.close()

    def _show_loading_planning(self):
        """積載計画作成"""
        st.header("📦 積載計画自動作成")
        
        st.info("""
        **機能説明:**
        - オーダー情報から自動的に積載計画を作成します
        - 納期優先で計画し、積載不可の場合は前倒しで再計算します
        - 前倒し可能な製品のみが平準化の対象となります
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "計画開始日",
                value=date.today() + timedelta(days=3),
                min_value=date.today(),
                help="通常は3稼働日後から開始"
            )
        
        with col2:
            days = st.number_input(
                "計画日数",
                min_value=1,
                max_value=30,
                value=7,
                help="積載計画を作成する日数"
            )
        
        st.markdown("---")
        
        if st.button("🔄 積載計画を作成", type="primary", use_container_width=True):
            with st.spinner("積載計画を計算中..."):
                try:
                    result = self.service.calculate_loading_plan_from_orders(
                        start_date=start_date,
                        days=days
                    )
                    
                    st.session_state['loading_plan'] = result
                    
                    summary = result['summary']
                    
                    st.success("✅ 積載計画を作成しました")
                    
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("計画日数", f"{summary['total_days']}日")
                    with col_b:
                        st.metric("総便数", f"{summary['total_trips']}便")
                    with col_c:
                        st.metric("警告数", summary['total_warnings'])
                    with col_d:
                        status_color = "🟢" if summary['status'] == '正常' else "🟡"
                        st.metric("ステータス", f"{status_color} {summary['status']}")
                    
                    if result['unloaded_tasks']:
                        st.error(f"⚠️ 積載できなかった製品: {len(result['unloaded_tasks'])}件")
                        
                        unloaded_df = pd.DataFrame([{
                            '製品コード': task['product_code'],
                            '製品名': task['product_name'],
                            '容器数': task['num_containers'],
                            '納期': task['delivery_date'].strftime('%Y-%m-%d')
                        } for task in result['unloaded_tasks']])
                        
                        st.dataframe(unloaded_df, use_container_width=True, hide_index=True)
                        
                        st.warning("""
                        **対処方法:**
                        - トラックの追加を検討してください
                        - 製品の前倒し可能フラグを確認してください
                        - 容器・トラックの容量を確認してください
                        """)
                    
                    st.info("詳細は「📊 計画確認」タブでご確認ください")
                    
                except Exception as e:
                    st.error(f"積載計画作成エラー: {e}")
                    
        if 'loading_plan' in st.session_state:
            result = st.session_state['loading_plan']
            
            st.markdown("---")
            st.subheader("💾 計画の保存とエクスポート")
            
            col_export1, col_export2, col_export3 = st.columns(3)
            
            with col_export1:
                st.write("**DBに保存**")
                plan_name = st.text_input(
                    "計画名",
                    value=f"積載計画_{result.get('period', '').split(' ~ ')[0]}",
                    key="plan_name_save"
                )
                
                if st.button("💾 DBに保存", type="primary"):
                    try:
                        plan_id = self.service.save_loading_plan(result, plan_name)
                        st.success(f"✅ 計画を保存しました (ID: {plan_id})")
                        st.session_state['saved_plan_id'] = plan_id
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
            
            with col_export2:
                st.write("**Excel出力**")
                export_format = st.radio(
                    "出力形式",
                    options=['日別', '週別'],
                    horizontal=True,
                    key="export_format"
                )
                
                if st.button("📥 Excelダウンロード", type="secondary"):
                    try:
                        format_key = 'daily' if export_format == '日別' else 'weekly'
                        excel_data = self.service.export_loading_plan_to_excel(result, format_key)
                        
                        filename = f"積載計画_{export_format}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        st.download_button(
                            label="⬇️ ダウンロード",
                            data=excel_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"Excel出力エラー: {e}")
            
            with col_export3:
                st.write("**CSV出力**")
                st.write("")
                
                if st.button("📄 CSVダウンロード", type="secondary"):
                    try:
                        csv_data = self.service.export_loading_plan_to_csv(result)
                        
                        filename = f"積載計画_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        
                        st.download_button(
                            label="⬇️ ダウンロード",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.error(f"CSV出力エラー: {e}")
    
    def _show_plan_view(self):
        """計画確認"""
        st.header("📊 積載計画確認")
        
        view_tab1, view_tab2 = st.tabs(["現在の計画", "保存済み計画"])
        
        with view_tab1:
            self._show_current_plan()
        
        with view_tab2:
            self._show_saved_plans()
    
    def _show_current_plan(self):
        """現在の計画表示"""
        
        if 'loading_plan' not in st.session_state:
            st.info("まず「積載計画作成」タブで計画を作成してください")
            return
        
        result = st.session_state['loading_plan']
        daily_plans = result['daily_plans']
        
        view_type = st.radio(
            "表示形式",
            options=['日別表示', '一覧表示'],
            horizontal=True
        )
        
        if view_type == '日別表示':
            self._show_daily_view(daily_plans)
        else:
            self._show_list_view(daily_plans)
     
    def _show_saved_plans(self):
        """保存済み計画表示"""
        
        try:
            saved_plans = self.service.get_all_loading_plans()
            
            if not saved_plans:
                st.info("保存済みの計画がありません")
                return
            
            # 計画選択UI
            plan_options = {
                f"ID {plan['id']}: {plan['plan_name']} ({plan['summary']['total_days']}日, {plan['summary']['total_trips']}便)": plan['id'] 
                for plan in saved_plans
            }
            
            selected_plan_key = st.selectbox(
                "表示する計画を選択",
                options=list(plan_options.keys())
            )
            
            if selected_plan_key:
                selected_plan_id = plan_options[selected_plan_key]
                
                # ✅ 修正: 選択した計画IDを使って詳細データを取得
                with st.spinner("計画データを読み込み中..."):
                    selected_plan = self.service.get_loading_plan(selected_plan_id)
                
                if selected_plan:
                    self._display_saved_plan(selected_plan)
                else:
                    st.error("選択した計画の詳細データを取得できませんでした")
        
        except Exception as e:
            st.error(f"保存済み計画表示エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
          
    def _display_saved_plan(self, plan_data: Dict):
        """保存済み計画を表形式で表示・編集"""
        try:
            st.subheader("計画詳細")
            
            # ✅ デバッグ: 実際のデータ構造を確認
            # st.write("🔍 デバッグ情報:")
            # st.json({
            #     "plan_data_keys": list(plan_data.keys()) if plan_data else "None",
            #     "has_daily_plans": "daily_plans" in plan_data if plan_data else False,
            #     "daily_plans_type": type(plan_data.get('daily_plans')) if plan_data else "None",
            #     "daily_plans_keys": list(plan_data.get('daily_plans', {}).keys()) if plan_data and plan_data.get('daily_plans') else "None"
            # })
            
            # データ取得
            summary = plan_data.get('summary', {})
            daily_plans = plan_data.get('daily_plans', {})
            unloaded_tasks = plan_data.get('unloaded_tasks', [])
            
            if not daily_plans:
                st.warning("❌ daily_plans データがありません")
                st.info("計画データの構造を確認しています...")
                st.json(plan_data)  # 全データを表示して確認
                return
            
            # サマリー表示
            st.subheader("📊 計画サマリー")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("計画日数", f"{summary.get('total_days', 0)}日")
            with col2:
                st.metric("総便数", summary.get('total_trips', 0))
            with col3:
                st.metric("ステータス", summary.get('status', '不明'))
            with col4:
                period = plan_data.get('period', '期間不明')
                st.metric("計画期間", period)
            
            st.markdown("---")
            
            # # 📊 明細データを表形式で表示
            #st.subheader("📋 積載計画一覧")
            
            # # 全データを1つのDataFrameに変換
            all_plan_data = []
            
            for date_str in sorted(daily_plans.keys()):
                day_plan = daily_plans[date_str]
                st.write(f"📅 日付: {date_str}, トラック数: {len(day_plan.get('trucks', []))}")
                
                for truck_idx, truck in enumerate(day_plan.get('trucks', [])):
                    truck_name = truck.get('truck_name', '不明')
                    utilization = truck.get('utilization', {})
                    
                    st.write(f"  🚛 トラック: {truck_name}, アイテム数: {len(truck.get('loaded_items', []))}")
                    
                    for item_idx, item in enumerate(truck.get('loaded_items', [])):
                        # 納期のフォーマット処理
                        delivery_date = item.get('delivery_date')
                        delivery_date_str = ''
                        if delivery_date:
                            if hasattr(delivery_date, 'strftime'):
                                delivery_date_str = delivery_date.strftime('%Y-%m-%d')
                            elif hasattr(delivery_date, 'date'):
                                delivery_date_str = delivery_date.date().strftime('%Y-%m-%d')
                            else:
                                delivery_date_str = str(delivery_date)
                        
                        all_plan_data.append({
                            '積載日': date_str,
                            'トラック': truck_name,
                            '製品コード': item.get('product_code', ''),
                            '製品名': item.get('product_name', ''),
                            '容器数': item.get('num_containers', 0),
                            '合計数量': item.get('total_quantity', 0),
                            '納期': delivery_date_str,
                            '体積率(%)': utilization.get('volume_rate', 0),
                            '重量率(%)': utilization.get('weight_rate', 0)
                         })
            
            if all_plan_data:
                plan_df = pd.DataFrame(all_plan_data)
                
                st.success(f"✅ 計画データを読み込みました: {len(plan_df)} 行")
                
                # 編集可能なデータエディタ
                st.info("💡 **編集方法:** セルをダブルクリックして値を変更し、「💾 変更を保存」をクリック")
                
                edited_df = st.data_editor(
                    plan_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=['積載日', 'トラック', '体積率(%)', '重量率(%)'],
                    column_config={
                        "積載日": st.column_config.TextColumn("積載日"),
                        "トラック": st.column_config.TextColumn("トラック"),
                        "製品コード": st.column_config.TextColumn("製品コード"),
                        "製品名": st.column_config.TextColumn("製品名"),
                        "容器数": st.column_config.NumberColumn("容器数", min_value=0, step=1),
                        "合計数量": st.column_config.NumberColumn("合計数量", min_value=0, step=1),
                        "納期": st.column_config.TextColumn("納期"),
                        "体積率(%)": st.column_config.NumberColumn("体積率(%)", format="%d%%", disabled=True),
                        "重量率(%)": st.column_config.NumberColumn("重量率(%)", format="%d%%", disabled=True)
                    },
                    key=f"plan_editor_{plan_data.get('id', 'current')}"
                )
                
                # 保存ボタン
                st.markdown("---")
                if st.button("💾 変更を保存", type="primary", key=f"save_{plan_data.get('id', 'current')}"):
                    st.info("保存機能は現在開発中です")
                    # ここに保存処理を実装
                    
            else:
                st.warning("表示する積載計画データがありません")
                
            # 警告表示
            warnings_data = []
            for date_str, day_plan in daily_plans.items():
                for warning in day_plan.get('warnings', []):
                    warnings_data.append({
                        '日付': date_str,
                        '警告内容': warning
                    })
            
            if warnings_data:
                st.subheader("⚠️ 警告一覧")
                warnings_df = pd.DataFrame(warnings_data)
                st.dataframe(warnings_df, use_container_width=True, hide_index=True)
                    
        except Exception as e:
            st.error(f"計画表示エラー: {str(e)}")
            import traceback
            st.code(traceback.format_exc()) 

    def _show_daily_view(self, daily_plans):
        """日別表示"""
        
        for date_str in sorted(daily_plans.keys()):
            plan = daily_plans[date_str]
            
            trucks = plan.get('trucks', [])
            warnings = plan.get('warnings', [])
            total_trips = len(trucks)
            
            with st.expander(f"📅 {date_str} ({total_trips}便)", expanded=True):
                
                if warnings:
                    st.warning("⚠️ 警告:")
                    for warning in warnings:
                        st.write(f"• {warning}")
                
                if not trucks:
                    st.info("この日の積載予定はありません")
                    continue
                
                for i, truck_plan in enumerate(trucks, 1):
                    st.markdown(f"**🚛 便 #{i}: {truck_plan.get('truck_name', 'トラック名不明')}**")
                    
                    util = truck_plan.get('utilization', {})
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        st.metric("体積積載率", f"{util.get('volume_rate', 0)}%")
                    with col_u2:
                        st.metric("重量積載率", f"{util.get('weight_rate', 0)}%")
                    
                    loaded_items = truck_plan.get('loaded_items', [])
                    if loaded_items:
                        items_df = pd.DataFrame([{
                            '製品コード': item.get('product_code', ''),
                            '製品名': item.get('product_name', ''),
                            '容器数': item.get('num_containers', 0),
                            '合計数量': item.get('total_quantity', 0),
                            '納期': item['delivery_date'].strftime('%Y-%m-%d') if 'delivery_date' in item else ''
                        } for item in loaded_items])
                        
                        st.dataframe(items_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("積載品がありません")
                    
                    st.markdown("---")
    
    def _show_list_view(self, daily_plans):
        """一覧表示"""
        
        all_items = []
        
        for date_str in sorted(daily_plans.keys()):
            plan = daily_plans[date_str]
            
            trucks = plan.get('trucks', [])
            
            for truck_plan in trucks:
                loaded_items = truck_plan.get('loaded_items', [])
                truck_name = truck_plan.get('truck_name', 'トラック名不明')
                utilization = truck_plan.get('utilization', {})
                
                for item in loaded_items:
                    delivery_date = item.get('delivery_date')
                    if delivery_date:
                        if hasattr(delivery_date, 'strftime'):
                            delivery_date_str = delivery_date.strftime('%Y-%m-%d')
                        else:
                            delivery_date_str = str(delivery_date)
                    else:
                        delivery_date_str = '-'
                    
                    all_items.append({
                        '積載日': date_str,
                        'トラック': truck_name,
                        '製品コード': item.get('product_code', ''),
                        '製品名': item.get('product_name', ''),
                        '容器数': item.get('num_containers', 0),
                        '合計数量': item.get('total_quantity', 0),
                        '納期': delivery_date_str,
                        '体積率': f"{utilization.get('volume_rate', 0)}%",
                        '重量率': f"{utilization.get('weight_rate', 0)}%"
                    })
        
        if all_items:
            df = pd.DataFrame(all_items)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("表示するデータがありません")

    def _show_container_management(self):
        """容器管理表示"""
        st.header("🧰 容器管理")
        st.write("積載に使用する容器の登録と管理を行います。")

        try:
            st.subheader("新規容器登録")
            container_data = FormComponents.container_form()

            if container_data:
                success = self.service.create_container(container_data)
                if success:
                    st.success(f"容器 '{container_data['name']}' を登録しました")
                    st.rerun()
                else:
                    st.error("容器登録に失敗しました")

            st.subheader("登録済み容器一覧")
            containers = self.service.get_containers()

            if containers:
                for container in containers:
                    with st.expander(f"📦 {container.name} (ID: {container.id})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**寸法:** {container.width} × {container.depth} × {container.height} mm")
                            st.write(f"**体積:** {(container.width * container.depth * container.height) / 1000000000:.3f} m³")
                        
                        with col2:
                            st.write(f"**最大重量:** {container.max_weight} kg")
                            st.write(f"**積重可:** {'✅' if container.stackable else '❌'}")
                            max_stack = getattr(container, 'max_stack', 1)
                            st.write(f"**最大段数:** {max_stack}段")

                        with st.form(f"edit_container_form_{container.id}"):
                            st.write("✏️ 容器情報を編集")

                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                new_name = st.text_input("容器名", value=container.name)
                                new_width = st.number_input("幅 (mm)", min_value=1, value=container.width)
                                new_depth = st.number_input("奥行 (mm)", min_value=1, value=container.depth)
                                new_height = st.number_input("高さ (mm)", min_value=1, value=container.height)
                            
                            with col_b:
                                new_weight = st.number_input("最大重量 (kg)", min_value=0, value=container.max_weight)
                                new_stackable = st.checkbox("積重可", value=bool(container.stackable))
                                new_max_stack = st.number_input(
                                    "最大積み重ね段数", 
                                    min_value=1, 
                                    max_value=10, 
                                    value=getattr(container, 'max_stack', 1)
                                )

                            submitted = st.form_submit_button("更新", type="primary")
                            if submitted:
                                update_data = {
                                    "name": new_name,
                                    "width": new_width,
                                    "depth": new_depth,
                                    "height": new_height,
                                    "max_weight": new_weight,
                                    "stackable": int(new_stackable),
                                    "max_stack": new_max_stack
                                }
                                success = self.service.update_container(container.id, update_data)
                                if success:
                                    st.success(f"✅ 容器 '{container.name}' を更新しました")
                                    st.rerun()
                                else:
                                    st.error("❌ 容器更新に失敗しました")

                        if st.button("🗑️ 削除", key=f"delete_container_{container.id}"):
                            success = self.service.delete_container(container.id)
                            if success:
                                st.success(f"容器 '{container.name}' を削除しました")
                                st.rerun()
                            else:
                                st.error("容器削除に失敗しました")

                st.subheader("容器統計")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("登録容器数", len(containers))
                with col2:
                    avg_volume = sum((c.width * c.depth * c.height) for c in containers) / len(containers) / 1000000000
                    st.metric("平均体積", f"{avg_volume:.2f} m³")
                with col3:
                    avg_weight = sum(c.max_weight for c in containers) / len(containers)
                    st.metric("平均最大重量", f"{avg_weight:.1f} kg")

            else:
                st.info("登録されている容器がありません")

        except Exception as e:
            st.error(f"容器管理エラー: {e}")

    def _show_truck_management(self):
        """トラック管理表示"""
        st.header("🚛 トラック管理")
        st.write("積載に使用するトラックの登録と管理を行います。")

        try:
            st.subheader("新規トラック登録")
            truck_data = FormComponents.truck_form()

            if truck_data:
                success = self.service.create_truck(truck_data)
                if success:
                    st.success(f"トラック '{truck_data['name']}' を登録しました")
                    st.rerun()
                else:
                    st.error("トラック登録に失敗しました")

            st.subheader("登録済みトラック一覧")
            trucks_df = self.service.get_trucks()

            if not trucks_df.empty:
                for _, truck in trucks_df.iterrows():
                    with st.expander(f"🛻 {truck['name']} (ID: {truck['id']})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**荷台寸法:** {truck['width']} × {truck['depth']} × {truck['height']} mm")
                            st.write(f"**最大積載重量:** {truck['max_weight']} kg")
                            volume_m3 = (truck['width'] * truck['depth'] * truck['height']) / 1000000000
                            st.write(f"**荷台容積:** {volume_m3:.2f} m³")
                        
                        with col2:
                            st.write(f"**出発時刻:** {truck['departure_time']}")
                            st.write(f"**到着時刻:** {truck['arrival_time']} (+{truck['arrival_day_offset']}日)")
                            st.write(f"**デフォルト便:** {'✅' if truck['default_use'] else '❌'}")

                        with st.form(f"edit_truck_form_{truck['id']}"):
                            st.write("✏️ トラック情報を編集")

                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                new_name = st.text_input("トラック名", value=truck['name'])
                                new_width = st.number_input("荷台幅 (mm)", min_value=1, value=int(truck['width']))
                                new_depth = st.number_input("荷台奥行 (mm)", min_value=1, value=int(truck['depth']))
                                new_height = st.number_input("荷台高さ (mm)", min_value=1, value=int(truck['height']))
                                new_weight = st.number_input("最大積載重量 (kg)", min_value=1, value=int(truck['max_weight']))
                            
                            with col_b:
                                new_dep = st.time_input("出発時刻", value=truck['departure_time'])
                                new_arr = st.time_input("到着時刻", value=truck['arrival_time'])
                                new_offset = st.number_input(
                                    "到着日オフセット（日）", 
                                    min_value=0, 
                                    max_value=7, 
                                    value=int(truck['arrival_day_offset'])
                                )
                                new_default = st.checkbox("デフォルト便", value=bool(truck['default_use']))

                            submitted = st.form_submit_button("更新", type="primary")
                            if submitted:
                                update_data = {
                                    "name": new_name,
                                    "width": new_width,
                                    "depth": new_depth,
                                    "height": new_height,
                                    "max_weight": new_weight,
                                    "departure_time": new_dep,
                                    "arrival_time": new_arr,
                                    "arrival_day_offset": new_offset,
                                    "default_use": new_default,
                                }
                                success = self.service.update_truck(truck['id'], update_data)
                                if success:
                                    st.success(f"✅ トラック '{truck['name']}' を更新しました")
                                    st.rerun()
                                else:
                                    st.error("❌ トラック更新に失敗しました")

                        if st.button("🗑️ 削除", key=f"delete_truck_{truck['id']}"):
                            success = self.service.delete_truck(truck['id'])
                            if success:
                                st.success(f"トラック '{truck['name']}' を削除しました")
                                st.rerun()
                            else:
                                st.error("トラック削除に失敗しました")

            else:
                st.info("登録されているトラックがありません")

        except Exception as e:
            st.error(f"トラック管理エラー: {e}")