# pages/device_category_management.py

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.auth import AuthManager
from services.device_category_services import (
    get_device_categories,
    create_device_category,
    update_device_category,
    delete_device_category,
    count_devices_group_by_category,
)

st.set_page_config(page_title="Quản lý loại thiết bị", page_icon="💻", layout="wide")

# ==========================================
# BẮT BUỘC ĐĂNG NHẬP
# ==========================================
auth_manager = AuthManager()
auth_manager.require_auth()

if "type_filter_q" not in st.session_state:
    st.session_state.type_filter_q = ""
if "type_filter_used" not in st.session_state:
    st.session_state.type_filter_used = "Tất cả"
if "type_show_form" not in st.session_state:
    st.session_state.type_show_form = False
if "type_show_detail" not in st.session_state:
    st.session_state.type_show_detail = False
if "type_confirm_delete" not in st.session_state:
    st.session_state.type_confirm_delete = None
if "selected_type_id" not in st.session_state:
    st.session_state.selected_type_id = None
if "category_device_count" not in st.session_state:
    st.session_state.category_device_count = count_devices_group_by_category()
if "category_df_key" not in st.session_state:
    st.session_state.category_df_key = 0

def clear_category_selection():
    st.session_state.category_df_key += 1

def load_device_categories_from_db():
    categories = get_device_categories()

    st.session_state.device_categories = [
        {
            "id": c["category_id"],
            "code": c["category_code"],
            "name": c["category_name"],
            "note": c["notes"],
            "is_active": not c["delete_flag"]
        }
        for c in categories
    ]

if "device_categories" not in st.session_state:
    load_device_categories_from_db()

def reload_categories():
    st.session_state.category_device_count = count_devices_group_by_category()
    st.session_state.type_show_form = False
    st.session_state.type_show_detail = False
    st.session_state.type_confirm_delete = None
    st.session_state.selected_type_id = None
    load_device_categories_from_db()
    st.rerun()

def reset_popups():
    st.session_state.type_show_detail = False
    st.session_state.type_confirm_delete = None

def get_type_by_id(type_id: int):
    return next((t for t in st.session_state.device_categories if t.get("id") == type_id), None)

def normalize(s: str) -> str:
    return (s or "").strip()

def type_usage_count(category_id: int) -> int:
    return st.session_state.category_device_count.get(category_id, 0)

def can_delete_type(type_obj: dict) -> bool:
    return type_usage_count(type_obj["id"]) == 0

def code_exists(code: str, exclude_id=None) -> bool:
    c = normalize(code).lower()
    for t in st.session_state.device_categories:
        if exclude_id is not None and t.get("id") == exclude_id:
            continue
        if normalize(t.get("code")).lower() == c and c:
            return True
    return False

def name_exists(name: str, exclude_id=None) -> bool:
    n = normalize(name).lower()
    for t in st.session_state.device_categories:
        if exclude_id is not None and t.get("id") == exclude_id:
            continue
        if normalize(t.get("name")).lower() == n and n:
            return True
    return False

def add_type(code: str, name: str, note: str):
    ok = create_device_category({
        "code": code,
        "name": name,
        "note": note
    })

    if ok:
        st.success("✅ Thêm loại thiết bị thành công!")
        reload_categories()

def update_type(type_id: int, code: str, name: str, note: str):
    ok = update_device_category(type_id, {
        "code": code,
        "name": name,
        "note": note
    })

    if ok:
        st.success("✅ Cập nhật loại thiết bị thành công!")
        reload_categories()

def delete_type(type_id: int):
    t = get_type_by_id(type_id)
    if not t:
        st.error("Không tìm thấy loại thiết bị.")
        return

    ok = delete_device_category(type_id)
    if ok:
        st.success("✅ Đã ngưng sử dụng loại thiết bị.")
        reload_categories()

# =========================
# Dialogs
# =========================
@st.dialog("📄 Chi tiết loại thiết bị", width="small")
def type_detail_popup(type_obj: dict):
    used = type_usage_count(type_obj.get("id"))
    st.markdown(
        f"""  
        **Mã:** {type_obj.get('code')}  
        **Tên:** {type_obj.get('name')}  
        **Số lượng:** {used} thiết bị  
        **Ghi chú:** {type_obj.get('note') or '—'}
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✏️ Sửa", type="primary", width='stretch'):
            st.session_state.type_show_detail = False
            st.session_state.type_show_form = True
            st.session_state.type_form_mode = "edit"
            st.session_state.selected_type_id = type_obj.get("id")
            st.rerun()
    with c2:
        if st.button("Đóng", width='stretch'):
            reset_popups()
            st.rerun()

@st.dialog("🗑️ Xác nhận xóa loại thiết bị", width="small")
def type_confirm_delete_popup(type_obj: dict):
    used = type_usage_count(type_obj.get("id"))

    if used > 0:
        st.error("⛔ Không thể xóa loại thiết bị này vì đang được sử dụng.")
        st.markdown(
            f"""
            **Mã:** {type_obj.get('code')}  
            **Tên:** {type_obj.get('name')}  
            **Số lượng:** {used} thiết bị
            """
        )
        if st.button("❌ Đóng", width='stretch'):
            reset_popups()
            st.rerun()
        return

    st.warning("Bạn có chắc chắn muốn xóa loại thiết bị này không?")
    st.markdown(
        f"""
        **Mã:** {type_obj.get('code')}  
        **Tên:** {type_obj.get('name')}
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Xóa", type="primary", width='stretch'):
            delete_type(type_obj.get("id"))
    with c2:
        if st.button("❌ Hủy", width='stretch'):
            reset_popups()
            st.rerun()

# =========================
# Form area (Add/Edit)
# =========================
def show_type_form(mode="add", type_obj=None):
    st.subheader("➕ Thêm loại thiết bị" if mode == "add" else "✏️ Chỉnh sửa loại thiết bị")

    with st.form(key="type_form"):
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("Mã loại thiết bị *", value=(type_obj.get("code") if type_obj else ""))
            name = st.text_input("Tên loại thiết bị *", value=(type_obj.get("name") if type_obj else ""))
        with col2:
            note = st.text_area("Ghi chú (tùy chọn)", value=(type_obj.get("note") if type_obj else ""), height=90)

        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("💾 Lưu", type="primary", width='stretch')
        cancelled = c2.form_submit_button("❌ Hủy", width='stretch')

        if submitted:
            code_clean = normalize(code)
            name_clean = normalize(name)

            if not code_clean or not name_clean:
                st.error("⚠️ Vui lòng nhập đủ trường bắt buộc (*).")
                st.stop()

            if mode == "add":
                if code_exists(code_clean):
                    st.error("⚠️ Mã loại thiết bị đã tồn tại.")
                    st.stop()
                if name_exists(name_clean):
                    st.error("⚠️ Tên loại thiết bị đã tồn tại.")
                    st.stop()
                add_type(code_clean, name_clean, note)

            else:
                tid = type_obj.get("id")
                if code_exists(code_clean, exclude_id=tid):
                    st.error("⚠️ Mã loại thiết bị đã tồn tại.")
                    st.stop()
                if name_exists(name_clean, exclude_id=tid):
                    st.error("⚠️ Tên loại thiết bị đã tồn tại.")
                    st.stop()
                update_type(tid, code_clean, name_clean, note)

        if cancelled:
            st.session_state.type_show_form = False
            st.session_state.selected_type_id = None
            st.session_state.type_confirm_delete = None
            st.session_state.type_show_detail = False
            st.rerun()

# =========================
# UI
# =========================
st.title("Device Type Management")
st.markdown("---")

# ---------- Filters ----------
st.subheader("🔍 Bộ lọc")
def clear_type_filters():
    st.session_state.type_filter_q = ""
    st.session_state.type_filter_used = "Tất cả"
c1, c2, c3 = st.columns([2.2, 1.3, 1.5], vertical_alignment="bottom")
with c1:
    st.text_input(
        "Tìm theo mã / tên / ghi chú",
        placeholder="VD: T001, Laptop, Router...",
        key="type_filter_q" 
    )
with c2:
    st.selectbox(
        "Trạng thái số lượng",
        ["Tất cả", "Có thiết bị", "Trống"],
        key="type_filter_used"
    )
with c3:
    st.button("🔄 Xóa bộ lọc", width='stretch', on_click=clear_type_filters)

# apply filters
q = normalize(st.session_state.type_filter_q).lower()
filtered_types = []
for t in st.session_state.device_categories:
    if not t.get("is_active", True):
        continue

    used = type_usage_count(t.get("id"))
    ok_used = True
    if st.session_state.type_filter_used == "Có thiết bị":
        ok_used = used > 0
    elif st.session_state.type_filter_used == "Trống":
        ok_used = used == 0

    hay = " ".join([
        normalize(t.get("code")).lower(),
        normalize(t.get("name")).lower(),
        normalize(t.get("note")).lower()
    ])
    ok_q = (q in hay) if q else True

    if ok_used and ok_q:
        filtered_types.append(t)

st.markdown("---")

# Add button
bar1, bar2 = st.columns([10, 1.2])
with bar1:
    st.subheader(f"📋 Danh sách loại thiết bị ({len(filtered_types)} loại)")
with bar2:
    if st.button("➕ Thêm loại", type="primary", width='stretch'):
        st.session_state.type_show_form = True
        st.session_state.type_form_mode = "add"
        st.session_state.selected_type_id = None
        st.session_state.type_confirm_delete = None
        st.session_state.type_show_detail = False
        st.rerun()

# Form area
if st.session_state.type_show_form:
    st.markdown("---")
    if st.session_state.type_form_mode == "add":
        show_type_form("add")
    else:
        t = get_type_by_id(st.session_state.selected_type_id)
        if not t:
            st.warning("Không tìm thấy loại thiết bị để sửa.")
            st.session_state.type_show_form = False
            st.rerun()
        show_type_form("edit", t)

st.markdown("---")

# Render Bảng bằng DataFrame
if not filtered_types:
    st.info("Không có loại thiết bị nào phù hợp bộ lọc.")
else:
    # 1. Chuẩn bị dữ liệu cho DataFrame
    df_data = []
    for t in filtered_types:
        used = type_usage_count(t.get("id"))
        df_data.append({
            "Mã": t.get("code"),
            "Tên": t.get("name"),
            "Số lượng": used,
            "Ghi chú": t.get("note") if normalize(t.get("note")) else "—",
            "original_obj": t  # Giữ lại object gốc để truyền vào các popup
        })

    df = pd.DataFrame(df_data)
    
    # Chỉ trích xuất các cột cần hiển thị lên bảng
    display_df = df[["Mã", "Tên", "Số lượng", "Ghi chú"]]

    st.write("👉 **Nhấn vào một dòng bất kỳ trong bảng để xem các thao tác (Xem, Sửa, Xóa).**")

    # 2. Render bảng siêu mượt
    selection = st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"category_table_{st.session_state.category_df_key}"
    )

    # 3. Action Toolbar (Hiển thị khi click chọn 1 dòng)
    selected_rows = selection.selection.rows
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_item = df_data[selected_idx]
        
        # Trích xuất dữ liệu gốc
        t_obj = selected_item["original_obj"]
        tid = t_obj.get("id")
        used_count = selected_item["Số lượng"]

        st.markdown("---")
        st.markdown(f"🛠️ **Đang thao tác với:** `{t_obj.get('code')} - {t_obj.get('name')}`")

        # Chia cột cho các nút bấm
        a1, a2, a3, a4, _ = st.columns([1.5, 1.5, 1.5, 1.5, 4])

        if a1.button("👁️ Xem chi tiết", type="primary", width='stretch'):
            type_detail_popup(t_obj)

        if a2.button("✏️ Sửa", width='stretch'):
            st.session_state.type_show_form = True
            st.session_state.type_form_mode = "edit"
            st.session_state.selected_type_id = tid
            st.session_state.type_confirm_delete = None
            st.session_state.type_show_detail = False
            st.rerun()

        # Nút xóa tự động bị khóa nếu đang có thiết bị sử dụng
        if a3.button("🗑️ Xóa", disabled=(used_count > 0), width='stretch'):
            type_confirm_delete_popup(t_obj)

        with a4:
            st.button("❌ Bỏ chọn", key=f"unselect_btn_{tid}", width='stretch', on_click=clear_category_selection)