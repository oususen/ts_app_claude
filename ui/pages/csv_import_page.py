# app/ui/pages/csv_import_page.py
import streamlit as st
import pandas as pd
from datetime import datetime,date, timedelta
from services.csv_import_service import CSVImportService

class CSVImportPage:
    """CSV受注インポートページ"""
    
    def __init__(self, db_manager):
        self.import_service = CSVImportService(db_manager)
    
    def show(self):
        """ページ表示"""
        st.title("📥 受注CSVインポート")
        st.write("お客様からのCSVファイルを読み込み、生産指示データとして登録します。")
        
        tab1, tab2, tab3 = st.tabs(["📤 ファイルアップロード", "📊 インポート履歴", "ℹ️ 使い方"])
        
        with tab1:
            self._show_upload_form()
        with tab2:
            self._show_import_history()
        with tab3:
            self._show_instructions()
    
    def _show_upload_form(self):
        """アップロードフォーム表示"""
        st.header("📤 CSVファイルアップロード")
        
        st.info("""
        **対応フォーマット:**
        - エンコーディング: Shift-JIS
        - レコード識別: V2（日付）、V3（数量）
        - 必須カラム: データＮＯ、品番、検査区分、スタート月度など
        """)
        
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "CSVファイルを選択",
            type=['csv'],
            help="Shift-JIS形式のCSVファイルをアップロードしてください"
        )
        
        if uploaded_file is not None:
            # プレビュー表示
            try:
                df_preview = pd.read_csv(uploaded_file, encoding='shift_jis', nrows=10)
                uploaded_file.seek(0)
                
                st.subheader("📋 プレビュー（先頭10行）")
                st.dataframe(df_preview, use_container_width=True)
                
                # レコード識別の確認
                v2_count = len(df_preview[df_preview['レコード識別'] == 'V2'])
                v3_count = len(df_preview[df_preview['レコード識別'] == 'V3'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("総行数", len(df_preview))
                with col2:
                    st.metric("V2行（日付）", v2_count)
                with col3:
                    st.metric("V3行（数量）", v3_count)
                
                st.markdown("---")
                
                # インポートオプション
                st.subheader("⚙️ インポートオプション")
                
                col_opt1, col_opt2 = st.columns(2)
                
                with col_opt1:
                    update_mode = st.radio(
                        "更新モード",
                        options=['追加', '上書き'],
                        help="追加: 既存データに追加 / 上書き: 既存データを削除して新規登録"
                    )
                
                with col_opt2:
                    create_progress = st.checkbox(
                        "納入進度も同時作成",
                        value=True,
                        help="生産指示データから納入進度データも自動生成します"
                    )
                
                # インポート実行ボタン
                st.markdown("---")
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                
                with col_btn1:
                    if st.button("🔄 インポート実行", type="primary", use_container_width=True):
                        with st.spinner("データをインポート中..."):
                            try:
                                uploaded_file.seek(0)
                                
                                success, message = self.import_service.import_csv_data(
                                    uploaded_file,
                                    update_mode=(update_mode == '上書き'),
                                    create_progress=create_progress
                                )
                                
                                if success:
                                    st.success(f"✅ {message}")
                                    st.balloons()
                                    
                                    self._log_import_history(uploaded_file.name, message)
                                    #検査対象製品を表示
                                    self._show_inspection_products_after_import()
                                    
                                    st.info("💡 「配送便計画」ページでデータを確認してください")
                                else:
                                    st.error(f"❌ {message}")
                            
                            except Exception as e:
                                st.error(f"予期しないエラー: {e}")
                
                with col_btn2:
                    if st.button("🗑️ キャンセル", use_container_width=True):
                        st.rerun()
                
            except Exception as e:
                st.error(f"ファイル読み込みエラー: {e}")
                st.info("ファイルがShift-JIS形式であることを確認してください")
    def _show_inspection_products_after_import(self):
        """インポート後に検査対象製品（F/$含む）を表示"""
        from sqlalchemy import text
        from datetime import date, timedelta
        
        session = self.import_service.db.get_session()
        
        try:
            # 当日～2週間後
            today = date.today() - timedelta(days=5)  # 過去5日分も確認
            end_date = today + timedelta(days=14)
            
            query = text("""
                SELECT 
                    dp.delivery_date as 日付,
                    dp.order_id as オーダーID,
                    p.product_code as 製品コード,
                    p.product_name as 製品名,
                    dp.order_quantity as 受注数,
                    p.inspection_category as 検査区分
                FROM delivery_progress dp
                LEFT JOIN products p ON dp.product_id = p.id
                WHERE dp.delivery_date BETWEEN :start_date AND :end_date
                    AND (p.inspection_category LIKE '%F%' OR p.inspection_category LIKE '%$%')
                ORDER BY dp.delivery_date, p.product_code
            """)
            
            result = session.execute(query, {
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            })
            
            rows = result.fetchall()
            
            if rows:
                st.warning("⚠️ 検査対象製品（F/$含む）が含まれています")
                
                df = pd.DataFrame(rows, columns=result.keys())
                df['日付'] = pd.to_datetime(df['日付']).dt.date
                
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                with col_sum1:
                    f_count = len(df[df['検査区分'].str.contains('F', na=False)])
                    st.metric("F含む（最終検査）", f_count)
                with col_sum2:
                    s_count = len(df[df['検査区分'].str.contains('\\$', regex=True, na=False)])
                    st.metric("$含む（目視検査）", s_count)
                with col_sum3:
                    st.metric("総数量", f"{df['受注数'].sum():,}個")
                
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "日付": st.column_config.DateColumn("日付", format="YYYY-MM-DD"),
                    }
                )
        
        except Exception as e:
            st.error(f"検査対象製品確認エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            session.close()        
    
    def _show_import_history(self):
        """インポート履歴表示"""
        st.header("📊 インポート履歴")
        
        try:
            history = self.import_service.get_import_history()
            
            if history:
                history_df = pd.DataFrame(history)
                
                st.dataframe(
                    history_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "import_date": st.column_config.DatetimeColumn(
                            "インポート日時",
                            format="YYYY-MM-DD HH:mm:ss"
                        ),
                    }
                )
            else:
                st.info("インポート履歴がありません")
        
        except Exception as e:
            st.error(f"履歴取得エラー: {e}")
    
    def _show_instructions(self):
        """使い方表示"""
        st.header("ℹ️ 使い方")
        
        st.markdown("""
        ## 📋 CSVファイルのフォーマット
        
        ### 必須カラム
        - **レコード識別**: V2（日付行）、V3（数量行）
        - **データＮＯ**: 製品識別番号
        - **品番**: 製品コード
        - **検査区分**: N, NS, FS, F など
        - **スタート月度**: YYYYMM形式
        
        ### データ構造
        1. **V2行**: 各日付の生産指示日
        2. **V3行**: 各日付の生産指示数量
        
        ### インポート手順
        1. CSVファイルをアップロード
        2. プレビューで内容を確認
        3. インポートオプションを選択
        4. 「インポート実行」ボタンをクリック
        
        ## ⚠️ 注意事項
        
        - ファイルは **Shift-JIS** エンコーディングである必要があります
        - ⚠️上書きモードでは既存データが削除されます(使用禁止)
        - 大量データの場合は時間がかかることがあります
        
        ## 🔗 関連機能
        
        - インポート後は「納入進度」ページで進捗を確認できます
        - 「配送便計画」で自動的に積載計画が作成されます
        """)
    
    def _log_import_history(self, filename: str, message: str):
        """インポート履歴を記録"""
        try:
            self.import_service.log_import_history(filename, message)
        except Exception as e:
            print(f"履歴記録エラー: {e}")