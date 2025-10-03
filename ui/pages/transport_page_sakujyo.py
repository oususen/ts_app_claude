# app/ui/pages/transport_page.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict
from ui.components.forms import FormComponents
from ui.components.tables import TableComponents

class TransportPage:
    """配送便計画ページ - トラック積載計画の作成画面"""
    
    def __init__(self, transport_service):
        self.service = transport_service
        self.tables = TableComponents()
    
    def show(self):
        """ページ表示"""
        st.title("🚚 配送便計画")
        st.write("オーダー情報から自動的にトラック積載計画を作成します。")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📦 積載計画作成", "📊 計画確認", "🧰 容器管理", "🚛 トラック管理"])
        
        with tab1:
            self._show_loading_planning()
        with tab2:
            self._show_plan_view()
        with tab3:
            self._show_container_management()
        with tab4:
            self._show_truck_management()
    
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
                    
                    # セッションに保存
                    st.session_state['loading_plan'] = result
                    
                    # サマリー表示
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
                    
                    # 積載できなかったタスクを表示
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
                    
                    # 計画確認タブへ移動を促す
                    st.info("詳細は「📊 計画確認」タブでご確認ください")
                    
                    # 保存ボタン
                    st.markdown("---")
                    col_save1, col_save2 = st.columns([3, 1])
                    
                    with col_save1:
                        plan_name = st.text_input(
                            "計画名",
                            value=f"積載計画_{start_date.strftime('%Y%m%d')}",
                            help="この計画に名前を付けて保存します"
                        )
                    
                    with col_save2:
                        st.write("")
                        st.write("")
                        if st.button("💾 計画を保存", type="primary", use_container_width=True):
                            try:
                                plan_id = self.service.save_loading_plan(result, plan_name)
                                st.success(f"✅ 計画を保存しました (ID: {plan_id})")
                                st.session_state['saved_plan_id'] = plan_id
                            except Exception as e:
                                st.error(f"保存エラー: {e}")
                    
                except Exception as e:
                    st.error(f"積載計画作成エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    def _show_plan_view(self):
        """計画確認"""
        st.header("📊 積載計画確認")
        
        # タブ: 現在の計画 / 保存済み計画
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
        
        # 表示形式選択
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
        """保存済み計画一覧"""
        st.subheader("保存済み積載計画")
        
        try:
            plans = self.service.get_all_loading_plans()
            
            if not plans:
                st.info("保存された積載計画がありません")
                return
            
            # 計画リスト表示
            plans_df = pd.DataFrame([{
                'ID': p['id'],
                '計画名': p['plan_name'],
                '開始日': p['start_date'],
                '終了日': p['end_date'],
                '日数': p['total_days'],
                '便数': p['total_trips'],
                'ステータス': p['status'],
                '作成日時': p['created_at'].strftime('%Y-%m-%d %H:%M') if hasattr(p['created_at'], 'strftime') else str(p['created_at'])
            } for p in plans])
            
            st.dataframe(plans_df, use_container_width=True, hide_index=True)
            
            # 計画選択
            st.markdown("---")
            plan_options = {f"{p['plan_name']} (ID: {p['id']})": p['id'] for p in plans}
            selected_plan = st.selectbox("計画を選択", options=list(plan_options.keys()))
            
            if selected_plan:
                plan_id = plan_options[selected_plan]
                
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button("📂 計画を読み込む", use_container_width=True):
                        with st.spinner("計画を読み込み中..."):
                            plan_data = self.service.get_loading_plan(plan_id)
                            if plan_data:
                                st.success("計画を読み込みました")
                                self._display_saved_plan(plan_data)
                            else:
                                st.error("計画の読み込みに失敗しました")
                
                with col_btn2:
                    if st.button("📥 Excelエクスポート", use_container_width=True):
                        st.info("Excel出力機能は実装予定です")
                
                with col_btn3:
                    if st.button("🗑️ 計画を削除", type="secondary", use_container_width=True):
                        if st.session_state.get(f"confirm_delete_plan_{plan_id}", False):
                            if self.service.delete_loading_plan(plan_id):
                                st.success("計画を削除しました")
                                st.rerun()
                            else:
                                st.error("削除に失敗しました")
                        else:
                            st.session_state[f"confirm_delete_plan_{plan_id}"] = True
                            st.warning("もう一度クリックすると削除されます")
        
        except Exception as e:
            st.error(f"保存済み計画取得エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _display_saved_plan(self, plan_data: Dict):
        """保存済み計画を表示"""
        st.subheader("計画詳細")
        
        header = plan_data['header']
        
        # ヘッダー情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("計画期間", f"{header['total_days']}日")
        with col2:
            st.metric("総便数", header['total_trips'])
        with col3:
            st.metric("ステータス", header['status'])
        with col4:
            warning_count = len(plan_data.get('warnings', []))
            st.metric("警告数", warning_count)
        
        # 明細表示
        st.subheader("積載明細")
        details = plan_data['details']
        
        if details:
            details_df = pd.DataFrame([{
                '積載日': d['loading_date'],
                'トラック': d['truck_name'],
                '製品コード': d['product_code'],
                '製品名': d['product_name'],
                '容器数': d['num_containers'],
                '合計数量': d['total_quantity'],
                '納期': d['delivery_date'],
                '前倒し': '✅' if d['is_advanced'] else '',
                '体積率': f"{d['volume_utilization']}%" if d['volume_utilization'] else '',
                '重量率': f"{d['weight_utilization']}%" if d['weight_utilization'] else ''
            } for d in details])
            
            st.dataframe(details_df, use_container_width=True, hide_index=True)
        else:
            st.info("明細データがありません")
        
        # 警告表示
        if plan_data.get('warnings'):
            st.subheader("警告一覧")
            warnings_df = pd.DataFrame([{
                '日付': w['warning_date'],
                'タイプ': w['warning_type'],
                'メッセージ': w['warning_message']
            } for w in plan_data['warnings']])
            st.dataframe(warnings_df, use_container_width=True, hide_index=True)
        
        # 積載不可アイテム
        if plan_data.get('unloaded'):
            st.subheader("積載不可アイテム")
            unloaded_df = pd.DataFrame([{
                '製品コード': u['product_code'],
                '製品名': u['product_name'],
                '容器数': u['num_containers'],
                '合計数量': u['total_quantity'],
                '納期': u['delivery_date'],
                '理由': u['reason']
            } for u in plan_data['unloaded']])
            st.dataframe(unloaded_df, use_container_width=True, hide_index=True)
    
    def _show_daily_view(self, daily_plans):
        """日別表示"""
        
        for date_str in sorted(daily_plans.keys()):
            plan = daily_plans[date_str]
            
            with st.expander(f"📅 {date_str} ({plan['total_trips']}便)", expanded=True):
                
                # 警告表示
                if plan['warnings']:
                    st.warning("⚠️ 警告:")
                    for warning in plan['warnings']:
                        st.write(f"• {warning}")
                
                # トラック別表示
                if not plan['trucks']:
                    st.info("この日の積載予定はありません")
                    continue
                
                for i, truck_plan in enumerate(plan['trucks'], 1):
                    st.markdown(f"**🚛 便 #{i}: {truck_plan['truck_name']}**")
                    
                    # 積載率表示
                    util = truck_plan['utilization']
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        st.metric("体積積載率", f"{util['volume_rate']}%")
                    with col_u2:
                        st.metric("重量積載率", f"{util['weight_rate']}%")
                    
                    # 積載品表示
                    items_df = pd.DataFrame([{
                        '製品コード': item['product_code'],
                        '製品名': item['product_name'],
                        '容器数': item['num_containers'],
                        '合計数量': item['total_quantity'],
                        '納期': item['delivery_date'].strftime('%Y-%m-%d')
                    } for item in truck_plan['loaded_items']])
                    
                    st.dataframe(items_df, use_container_width=True, hide_index=True)
                    st.markdown("---")
    
    def _show_list_view(self, daily_plans):
        """一覧表示"""
        
        all_items = []
        
        for date_str in sorted(daily_plans.keys()):
            plan = daily_plans[date_str]
            
            for truck_plan in plan['trucks']:
                for item in truck_plan['loaded_items']:
                    all_items.append({
                        '積載日': date_str,
                        'トラック': truck_plan['truck_name'],
                        '製品コード': item['product_code'],
                        '製品名': item['product_name'],
                        '容器数': item['num_containers'],
                        '合計数量': item['total_quantity'],
                        '納期': item['delivery_date'].strftime('%Y-%m-%d'),
                        '体積率': f"{truck_plan['utilization']['volume_rate']}%",
                        '重量率': f"{truck_plan['utilization']['weight_rate']}%"
                    })
        
        if all_items:
            df = pd.DataFrame(all_items)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("表示する積載計画がありません")
    
    def _show_container_management(self):
        """容器管理表示"""
        st.header("🧰 容器管理")
        st.write("積載に使用する容器の登録と管理を行います。")

        try:
            # 新規容器登録
            st.subheader("新規容器登録")
            container_data = FormComponents.container_form()

            if container_data:
                success = self.service.create_container(container_data)
                if success:
                    st.success(f"容器 '{container_data['name']}' を登録しました")
                    st.rerun()
                else:
                    st.error("容器登録に失敗しました")

            # 容器一覧表示
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

                        # 更新フォーム
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
                                    value=getattr(container, 'max_stack', 1),
                                    help="積み重ね可能な最大段数"
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

                        # 削除ボタン
                        if st.button("🗑️ 削除", key=f"delete_container_{container.id}"):
                            success = self.service.delete_container(container.id)
                            if success:
                                st.success(f"容器 '{container.name}' を削除しました")
                                st.rerun()
                            else:
                                st.error("容器削除に失敗しました")

                # 統計
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
            import traceback
            st.code(traceback.format_exc())

    def _show_truck_management(self):
        """トラック管理表示"""
        st.header("🚛 トラック管理")
        st.write("積載に使用するトラックの登録と管理を行います。")

        try:
            # 新規トラック登録
            st.subheader("新規トラック登録")
            truck_data = FormComponents.truck_form()

            if truck_data:
                success = self.service.create_truck(truck_data)
                if success:
                    st.success(f"トラック '{truck_data['name']}' を登録しました")
                    st.rerun()
                else:
                    st.error("トラック登録に失敗しました")

            # トラック一覧表示
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

                        # 更新フォーム
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
                                    value=int(truck['arrival_day_offset']),
                                    help="翌日到着なら1、当日到着なら0"
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

                        # 削除ボタン
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
            import traceback
            st.code(traceback.format_exc())
# ui/pages/transport_page.py の計画表示部分

    def display_plan_result(self, plan_result):
        """計画結果を安全に表示"""
        try:
            if not plan_result:
                st.error("計画データがありません")
                return
            
            summary = plan_result.get('summary', {})
            
            # ✅ 安全なキーアクセス
            total_trips = summary.get('total_trips', 0)
            total_days = summary.get('total_days', 0)
            status = summary.get('status', '不明')
            
            st.metric("総便数", total_trips)
            st.metric("計画日数", total_days)
            st.metric("ステータス", status)
            
        except Exception as e:
            st.error(f"計画表示エラー: {e}")