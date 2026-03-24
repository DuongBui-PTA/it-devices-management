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
if "type_filter_allocation" not in st.session_state:
    st.session_state.type_filter_allocation = []
if "type_filter_technical" not in st.session_state:
    st.session_state.type_filter_technical = []
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
            "allocation_type": c.get("allocation_type", "—"),
            "technical_function": c.get("technical_function", "—"),
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

def add_type(payload: dict):
    ok = create_device_category(payload)

    if ok:
        st.success("✅ Thêm loại thiết bị thành công!")
        reload_categories()

def update_type(type_id: int, payload: dict):
    ok = update_device_category(type_id, payload)

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
@st.dialog("📄 Chi tiết loại thiết bị", width="medium")
def type_detail_popup(type_obj: dict):
    used = type_usage_count(type_obj.get("id"))
    alloc_type = type_obj.get("allocation_type") or "—"
    tech_func = type_obj.get("technical_function") or "—"

    st.markdown(
        f"""  
        **Mã:** {type_obj.get('code')}  
        **Tên:** {type_obj.get('name')}  
        **Nghiệp vụ cấp phát:** {alloc_type}  
        **Chức năng kỹ thuật:** {tech_func}  
        **Số lượng đang dùng:** {used} thiết bị  
        **Ghi chú:** {type_obj.get('note') or '—'}
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✏️ Sửa", type="primary", width='stretch'):
            # Gán object cần sửa vào biến Trigger
            st.session_state.trigger_edit_category = type_obj
            # Rerun để đóng popup Chi tiết hiện tại
            st.rerun()
    with c2:
        if st.button("Đóng", width='stretch'):
            st.rerun()

@st.dialog("🗑️ Xác nhận xóa loại thiết bị", width="small")
def type_confirm_delete_popup(type_obj: dict):
    used = type_usage_count(type_obj.get("id"))
    alloc_type = type_obj.get("allocation_type") or "—"
    tech_func = type_obj.get("technical_function") or "—"

    if used > 0:
        st.error("⛔ Không thể xóa loại thiết bị này vì đang được sử dụng.")
        st.markdown(
            f"""
            **Mã:** {type_obj.get('code')} | **Tên:** {type_obj.get('name')}  
            **Loại cấp phát:** {alloc_type}
            **Chức năng kỹ thuật:** {tech_func}  
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
        **Mã:** {type_obj.get('code')} | **Tên:** {type_obj.get('name')}  
        **Loại cấp phát:** {alloc_type}
        **Chức năng kỹ thuật:** {tech_func}
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
# Form area (Add/Edit) - SỬA THÀNH POPUP
# =========================
@st.dialog("📝 Cập nhật Loại thiết bị", width="medium")
def show_type_form_popup(mode="add", type_obj=None):
    st.subheader("➕ Thêm loại thiết bị" if mode == "add" else "✏️ Chỉnh sửa loại thiết bị")

    alloc_options = ['Cá nhân', 'Phòng ban/Dùng chung', 'Vật tư tiêu hao']
    tech_options = [
        'Thiết bị người dùng cuối (Laptop, PC...)', 
        'Thiết bị ngoại vi (Màn hình, Chuột...)', 
        'Thiết bị mạng (Router, Switch...)', 
        'Thiết bị văn phòng (Máy in, Scanner...)', 
        'Hạ tầng & Máy chủ (Server, UPS...)',
        'Khác'
    ]

    with st.form(key="type_form"):
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("Mã loại thiết bị *", value=(type_obj.get("code") if type_obj else ""))
            name = st.text_input("Tên loại thiết bị *", value=(type_obj.get("name") if type_obj else ""))
            def_alloc = type_obj.get("allocation_type") if type_obj and type_obj.get("allocation_type") else "Cá nhân"
            alloc_idx = alloc_options.index(def_alloc) if def_alloc in alloc_options else 0
            allocation_type = st.selectbox("Nghiệp vụ cấp phát", options=alloc_options, index=alloc_idx)
        with col2:
            def_tech = type_obj.get("technical_function") if type_obj and type_obj.get("technical_function") else tech_options[0]
            technical_function = st.selectbox("Chức năng kỹ thuật", options=tech_options, index=tech_options.index(def_tech) if def_tech in tech_options else 0)
            note = st.text_area("Ghi chú (tùy chọn)", value=(type_obj.get("note") if type_obj else ""), height=70)

        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("💾 Lưu", type="primary", width='stretch')
        cancelled = c2.form_submit_button("❌ Hủy", width='stretch')

        if submitted:
            code_clean = normalize(code)
            name_clean = normalize(name)

            if not code_clean or not name_clean:
                st.error("⚠️ Vui lòng nhập đủ trường bắt buộc (*).")
                st.stop()

            payload = {
                "code": code_clean,
                "name": name_clean,
                "allocation_type": allocation_type,
                "technical_function": technical_function,
                "note": note
            }

            if mode == "add":
                if code_exists(code_clean):
                    st.error("⚠️ Mã loại thiết bị đã tồn tại.")
                    st.stop()
                if name_exists(name_clean):
                    st.error("⚠️ Tên loại thiết bị đã tồn tại.")
                    st.stop()
                
                add_type(payload)
                st.rerun()

            else:
                tid = type_obj.get("id")
                if code_exists(code_clean, exclude_id=tid):
                    st.error("⚠️ Mã loại thiết bị đã tồn tại.")
                    st.stop()
                if name_exists(name_clean, exclude_id=tid):
                    st.error("⚠️ Tên loại thiết bị đã tồn tại.")
                    st.stop()
                
                update_type(tid, payload)
                st.rerun()

        if cancelled:
            st.rerun()

# =========================
# UI
# =========================
st.title("💻 Quản lý loại thiết bị")
st.markdown("---")

# ---------- Filters ----------
def clear_type_filters():
    st.session_state.type_filter_q = ""
    st.session_state.type_filter_used = "Tất cả"
    st.session_state.type_filter_allocation = []
    st.session_state.type_filter_technical = []

st.subheader("🔍 Bộ lọc")

# Lấy các giá trị duy nhất từ dữ liệu để làm Options cho dropdown
all_allocs = sorted(list(set([t.get("allocation_type") for t in st.session_state.device_categories if t.get("allocation_type") and t.get("allocation_type") != "—"])))
all_techs = sorted(list(set([t.get("technical_function") for t in st.session_state.device_categories if t.get("technical_function") and t.get("technical_function") != "—"])))

# Dòng 1: Tìm kiếm & Trạng thái số lượng
c1, c2 = st.columns([2, 1.2])
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

# Dòng 2: Phân loại cấp phát, Nhóm kỹ thuật & Nút xóa
c3, c4, c5 = st.columns([1.5, 1.5, 0.6], vertical_alignment="bottom")
with c3:
    st.multiselect("Nghiệp vụ cấp phát", options=all_allocs, key="type_filter_allocation")
with c4:
    st.multiselect("Nhóm kỹ thuật", options=all_techs, key="type_filter_technical")
with c5:
    st.button("🔄 Xóa bộ lọc", width='stretch', on_click=clear_type_filters)

# apply filters
q = normalize(st.session_state.type_filter_q).lower()
filtered_types = []
for t in st.session_state.device_categories:
    if not t.get("is_active", True):
        continue

    # 1. Lọc theo trạng thái số lượng
    used = type_usage_count(t.get("id"))
    ok_used = True
    if st.session_state.type_filter_used == "Có thiết bị":
        ok_used = used > 0
    elif st.session_state.type_filter_used == "Trống":
        ok_used = used == 0

    # 2. Lọc theo Text (Mã, tên, ghi chú)
    hay = " ".join([
        normalize(t.get("code")).lower(),
        normalize(t.get("name")).lower(),
        normalize(t.get("note")).lower()
    ])
    ok_q = (q in hay) if q else True

    # 3. Lọc theo Nghiệp vụ cấp phát (MỚI)
    ok_alloc = True
    if st.session_state.type_filter_allocation:
        ok_alloc = t.get("allocation_type") in st.session_state.type_filter_allocation

    # 4. Lọc theo Nhóm kỹ thuật (MỚI)
    ok_tech = True
    if st.session_state.type_filter_technical:
        ok_tech = t.get("technical_function") in st.session_state.type_filter_technical

    # NẾU THỎA MÃN TẤT CẢ CÁC ĐIỀU KIỆN TRÊN THÌ MỚI LẤY
    if ok_used and ok_q and ok_alloc and ok_tech:
        filtered_types.append(t)

st.markdown("---")

# Add button
bar1, bar2 = st.columns([10, 1.2])
with bar1:
    st.subheader(f"📋 Danh sách loại thiết bị ({len(filtered_types)} loại)")
with bar2:
    if st.button("➕ Thêm loại", type="primary", width='stretch'):
        show_type_form_popup("add")

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
            "Loại cấp phát": t.get("allocation_type"),
            "Nhóm kỹ thuật": t.get("technical_function"),
            "Số lượng": used,
            "Ghi chú": t.get("note") if normalize(t.get("note")) else "—",
            "original_obj": t  # Giữ lại object gốc để truyền vào các popup
        })

    df = pd.DataFrame(df_data)

    # BẮT TRIGGER ĐỂ MỞ POPUP SỬA TỪ BÊN NGOÀI
    if st.session_state.get("trigger_edit_category"):
        t_obj = st.session_state.trigger_edit_category
        # Xóa biến trigger ngay lập tức để tránh mở lại vòng lặp
        st.session_state.trigger_edit_category = None
        # Gọi mở popup Sửa
        show_type_form_popup("edit", t_obj)
    
    # Chỉ trích xuất các cột cần hiển thị lên bảng
    display_df = df[["Mã", "Tên", "Loại cấp phát", "Nhóm kỹ thuật", "Số lượng", "Ghi chú"]]

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
            show_type_form_popup("edit", t_obj)

        # Nút xóa tự động bị khóa nếu đang có thiết bị sử dụng
        if a3.button("🗑️ Xóa", disabled=(used_count > 0), width='stretch'):
            type_confirm_delete_popup(t_obj)

        with a4:
            st.button("❌ Bỏ chọn", key=f"unselect_btn_{tid}", width='stretch', on_click=clear_category_selection)