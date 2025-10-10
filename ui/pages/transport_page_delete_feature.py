# transport_page.pyに追加するコード

# _display_saved_planメソッド内のエクスポートセクションの後に追加:

"""
            # 削除ボタン
            st.markdown("---")
            st.subheader("🗑️ 計画の削除")
            
            col_delete1, col_delete2 = st.columns([3, 1])
            
            with col_delete1:
                st.warning(f"⚠️ 計画「{plan_data.get('plan_name', '無題')}」を削除しますか？この操作は取り消せません。")
            
            with col_delete2:
                if st.button("🗑️ 削除", type="secondary", use_container_width=True, key=f"delete_{plan_data.get('id')}"):
                    if self._confirm_and_delete_plan(plan_data.get('id'), plan_data.get('plan_name', '無題')):
                        st.success("✅ 計画を削除しました")
                        st.rerun()
"""

# ファイルの最後に追加するメソッド:

def _confirm_and_delete_plan(self, plan_id: int, plan_name: str) -> bool:
    """計画削除の確認と実行"""
    try:
        # 削除実行
        success = self.service.delete_loading_plan(plan_id)
        
        if success:
            return True
        else:
            st.error("❌ 削除に失敗しました")
            return False
            
    except Exception as e:
        st.error(f"削除エラー: {e}")
        return False
