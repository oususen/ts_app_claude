# app/ui/pages/product_page.py
import streamlit as st
import pandas as pd
from ui.components.forms import FormComponents

class ProductPage:
    """製品管理ページ - 製品の登録・編集・削除"""
    
    def __init__(self, production_service, transport_service):
        self.production_service = production_service
        self.transport_service = transport_service
    
    def show(self):
        """ページ表示"""
        st.title("📦 製品管理")
        st.write("製品の登録・編集・削除、および容器との紐付けを管理します。")
        
        tab1, tab2, tab3 = st.tabs(["📦 製品一覧", "➕ 製品登録", "🔗 製品×容器紐付け"])
        
        with tab1:
            self._show_product_list()
        with tab2:
            self._show_product_registration()
        with tab3:
            self._show_product_container_mapping()
    
    def _get_truck_names_by_ids(self, truck_ids_str):
        """トラックIDの文字列からトラック名のリストを取得"""
        if not truck_ids_str:
            return []
        try:
            trucks_df = self.transport_service.get_trucks()
            if trucks_df.empty:
                return []
            truck_map = dict(zip(trucks_df['id'], trucks_df['name']))
            truck_ids = [int(tid.strip()) for tid in str(truck_ids_str).split(',')]
            return [truck_map.get(tid, f"ID:{tid}") for tid in truck_ids]
        except:
            return []
    
    def _show_product_list(self):
        """製品一覧・編集"""
        st.header("📦 製品一覧")
        
        try:
            products = self.production_service.get_all_products()
            containers = self.transport_service.get_containers()
            trucks_df = self.transport_service.get_trucks()
            
            if not products:
                st.info("登録されている製品がありません")
                return
            
            # 容器マップ作成
            container_map = {c.id: c.name for c in containers} if containers else {}
            
            # 一覧テーブル表示
            st.subheader("登録製品一覧")
            products_df = pd.DataFrame([{
                'ID': p.id,
                '製品コード': p.product_code or '-',
                '製品名': p.product_name or '-',
                '使用容器': container_map.get(p.used_container_id, '-') if p.used_container_id else '-',
                '入り数': p.capacity or 0,
                '検査区分': p.inspection_category or '-',
                'リードタイム': f"{p.lead_time}日" if p.lead_time else '-',
                '前倒可': '✅' if getattr(p, 'can_advance', False) else '❌',
                '使用トラック': ', '.join(self._get_truck_names_by_ids(getattr(p, 'used_truck_ids', None))) or '-'
            } for p in products])
            
            st.dataframe(
                products_df, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # 製品選択UI
            st.subheader("📝 製品詳細編集")
            
            # 製品選択ドロップダウン
            product_options = {f"{p.product_code} - {p.product_name}": p for p in products}
            selected_product_key = st.selectbox(
                "編集する製品を選択",
                options=list(product_options.keys()),
                key="product_selector"
            )
            
            if selected_product_key:
                product = product_options[selected_product_key]
                
                # 詳細編集エリア
                with st.container(border=True):
                    st.subheader(f"🔧 製品編集: {product.product_code}")
                    
                    # 製品情報表示
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**基本情報**")
                        st.write(f"ID: {product.id}")
                        st.write(f"製品コード: {product.product_code or '-'}")
                        st.write(f"製品名: {product.product_name or '-'}")
                        st.write(f"入り数: {product.capacity or 0}")
                        st.write(f"検査区分: {product.inspection_category or '-'}")
                    
                    with col2:
                        st.write("**容器・トラック情報**")
                        st.write(f"使用容器: {container_map.get(product.used_container_id, '-') if product.used_container_id else '-'}")
                        truck_names = self._get_truck_names_by_ids(getattr(product, 'used_truck_ids', None))
                        st.write(f"使用トラック: {', '.join(truck_names) if truck_names else '-'}")
                    
                    with col3:
                        st.write("**納期・制約**")
                        st.write(f"リードタイム: {product.lead_time or 0} 日")
                        st.write(f"固定日数: {product.fixed_point_days or 0} 日")
                        st.write(f"前倒可: {'✅' if getattr(product, 'can_advance', False) else '❌'}")
                    
                    # 更新フォーム
                    with st.form(f"edit_product_form_{product.id}"):
                        st.write("**製品情報を編集**")
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write("**基本情報**")
                            new_product_code = st.text_input(
                                "製品コード", 
                                value=product.product_code or '',
                                key=f"code_{product.id}"
                            )
                            new_product_name = st.text_input(
                                "製品名", 
                                value=product.product_name or '',
                                key=f"name_{product.id}"
                            )
                            new_capacity = st.number_input(
                                "入り数", 
                                min_value=0, 
                                value=int(product.capacity or 0),
                                key=f"capacity_{product.id}"
                            )
                            new_inspection_category = st.selectbox(
                                "検査区分",
                                options=['N', 'F', 'NS', 'FS', 'その他'],
                                index=['N', 'F', 'NS', 'FS', 'その他'].index(product.inspection_category) if product.inspection_category in ['N', 'F', 'NS', 'FS', 'その他'] else 0,
                                key=f"inspection_{product.id}"
                            )
                            
                            new_lead_time = st.number_input(
                                "リードタイム (日)", 
                                min_value=0, 
                                value=int(product.lead_time or 0),
                                key=f"lead_{product.id}"
                            )
                            new_fixed_point_days = st.number_input(
                                "固定日数 (日)", 
                                min_value=0, 
                                value=int(product.fixed_point_days or 0),
                                key=f"fixed_{product.id}"
                            )
                        
                        with col_b:
                            st.write("**容器・トラック設定**")
                            
                            # 使用容器選択
                            container_options = {c.name: c.id for c in containers} if containers else {}
                            current_container_name = container_map.get(product.used_container_id, None)
                            
                            new_used_container = st.selectbox(
                                "使用容器",
                                options=['未設定'] + list(container_options.keys()),
                                index=0 if not current_container_name else list(container_options.keys()).index(current_container_name) + 1 if current_container_name in container_options else 0,
                                key=f"container_{product.id}"
                            )
                            
                            # 使用トラック選択（複数選択）
                            if not trucks_df.empty:
                                truck_options = dict(zip(trucks_df['name'], trucks_df['id']))
                                current_truck_ids = []
                                if hasattr(product, 'used_truck_ids') and product.used_truck_ids:
                                    try:
                                        current_truck_ids = [int(tid.strip()) for tid in str(product.used_truck_ids).split(',')]
                                    except:
                                        current_truck_ids = []
                                
                                # 現在選択中のトラック名を取得
                                truck_name_map = dict(zip(trucks_df['id'], trucks_df['name']))
                                current_truck_names = [truck_name_map.get(tid) for tid in current_truck_ids if tid in truck_name_map.values()]
                                
                                new_used_trucks = st.multiselect(
                                    "使用トラック（複数選択可）",
                                    options=list(truck_options.keys()),
                                    default=current_truck_names,
                                    key=f"trucks_{product.id}"
                                )
                            else:
                                new_used_trucks = []
                                st.info("トラックが登録されていません")
                            
                            new_can_advance = st.checkbox(
                                "前倒可 (平準化対象)", 
                                value=bool(getattr(product, 'can_advance', False)),
                                key=f"advance_{product.id}"
                            )
                        
                        submitted = st.form_submit_button("💾 更新", type="primary")
                        
                        if submitted:
                            # 選択されたトラックIDを取得
                            selected_truck_ids = [truck_options[name] for name in new_used_trucks] if new_used_trucks else []
                            used_truck_ids_str = ','.join(map(str, selected_truck_ids)) if selected_truck_ids else None
                            
                            update_data = {
                                "product_code": new_product_code,
                                "product_name": new_product_name,
                                "capacity": new_capacity,
                                "inspection_category": new_inspection_category,
                                "used_container_id": container_options.get(new_used_container) if new_used_container != '未設定' else None,
                                "lead_time": new_lead_time,
                                "fixed_point_days": new_fixed_point_days,
                                "can_advance": new_can_advance,
                                "used_truck_ids": used_truck_ids_str
                            }
                            success = self.production_service.update_product(product.id, update_data)
                            if success:
                                st.success(f"製品 '{product.product_code}' を更新しました")
                                st.rerun()
                            else:
                                st.error("製品更新に失敗しました")
                    
                    # 削除ボタン
                    col_del1, col_del2 = st.columns([1, 5])
                    with col_del1:
                        if st.button("🗑️ 削除", key=f"delete_product_{product.id}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{product.id}", False):
                                success = self.production_service.delete_product(product.id)
                                if success:
                                    st.success(f"製品 '{product.product_code}' を削除しました")
                                    st.rerun()
                                else:
                                    st.error("製品削除に失敗しました")
                            else:
                                st.session_state[f"confirm_delete_{product.id}"] = True
                                st.warning("もう一度クリックすると削除されます")
            
            # 統計情報
            st.subheader("📊 製品統計")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("登録製品数", len(products))
            with col2:
                can_advance_count = sum(1 for p in products if getattr(p, 'can_advance', False))
                st.metric("前倒可能製品", can_advance_count)
            with col3:
                n_count = sum(1 for p in products if p.inspection_category == 'N')
                st.metric("検査区分N", n_count)
            with col4:
                avg_capacity = sum(p.capacity or 0 for p in products) / len(products) if products else 0
                st.metric("平均入り数", f"{avg_capacity:.0f}")
        
        except Exception as e:
            st.error(f"製品一覧エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _show_product_registration(self):
        """新規製品登録"""
        st.header("➕ 新規製品登録")
        
        try:
            containers = self.transport_service.get_containers()
            trucks_df = self.transport_service.get_trucks()
            product_data = FormComponents.product_form(containers, trucks_df)
            
            if product_data:
                success = self.production_service.create_product(product_data)
                if success:
                    st.success(f"製品 '{product_data['product_name']}' を登録しました")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("製品登録に失敗しました")
        
        except Exception as e:
            st.error(f"製品登録エラー: {e}")
    
    def _show_product_container_mapping(self):
        """製品×容器紐付け管理"""
        st.header("🔗 製品×容器紐付け設定")
        
        st.warning("""
        **この機能は product_container_mapping テーブルが必要です**
        
        以下のSQLを実行してテーブルを作成してください:
        """)
        
        st.code("""
CREATE TABLE product_container_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    container_id INT NOT NULL,
    max_quantity INT DEFAULT 100 COMMENT '容器あたりの最大積載数',
    is_primary TINYINT(1) DEFAULT 0 COMMENT '主要容器フラグ',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (container_id) REFERENCES container_capacity(id) ON DELETE CASCADE,
    UNIQUE KEY unique_product_container (product_id, container_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='製品と容器の紐付けマスタ';
        """, language="sql")
        
        st.info("テーブル作成後、この機能を実装します。")