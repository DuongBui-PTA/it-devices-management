# pages/device_maintenance_management.py

import streamlit as st
import pandas as pd
from datetime import date, datetime

from utils.auth import AuthManager
from services.device_allocation_services import get_allocations
from services.device_maintenance_services import get_maintenance_records, create_maintenance_record, update_maintenance_record
from utils.s3_utils import S3Manager

st.set_page_config(page_title="Bảo hành & Sửa chữa", page_icon="🛠️", layout="wide")

# ==========================================
# BẮT BUỘC ĐĂNG NHẬP
# ==========================================
auth_manager = AuthManager()
auth_manager.require_auth()

current_emp_id = st.session_state.get('employee_id')
user_role = st.session_state.get('user_role', 'USER')
username = st.session_state.get('username', '')

try:
    s3_manager = S3Manager()
except Exception:
    pass

# ---------- LOGIC PHÂN QUYỀN ----------
# Chỉ Admin, IT, Manager thấy toàn bộ. User thường chỉ thấy phiếu của mình.
filters = {} if user_role in ['ADMIN', 'MANAGER', 'IT'] else {"employee_id": current_emp_id}

# Quyền Cập nhật tiến độ: Chỉ dành cho ADMIN hoặc user cụ thể là "duong.bui"
can_update_progress = (user_role == 'ADMIN' or username.lower() == 'duong.bui')

if "ticket_df_key" not in st.session_state:
    st.session_state.ticket_df_key = 0

# KHỞI TẠO BIẾN SESSION CHO BỘ LỌC
if "mt_filter_status" not in st.session_state:
    st.session_state.mt_filter_status = []
if "mt_filter_priority" not in st.session_state:
    st.session_state.mt_filter_priority = []
if "mt_filter_requester" not in st.session_state:
    st.session_state.mt_filter_requester = []

def clear_ticket_selection():
    st.session_state.ticket_df_key += 1

def clear_mt_filters():
    st.session_state.mt_filter_status = []
    st.session_state.mt_filter_priority = []
    st.session_state.mt_filter_requester = []

# ---------- FETCH DATA ----------
records = get_maintenance_records(filters)

my_allocations = get_allocations({"employee_id": current_emp_id, "status": "Đang cấp phát"})
my_devices = {
    f"[{a['device_code']}] {a['device_name']}": {"device_id": a['device_id'], "alloc_id": a['id']} 
    for a in my_allocations
}

# ---------- DIALOG: TẠO TICKET MỚI ----------
@st.dialog("🎫 Yêu Cầu Bảo Hành / Sửa Chữa", width="large")
def create_ticket_popup():
    if not my_devices:
        st.warning("⚠️ Bạn hiện không có thiết bị nào đang được cấp phát để báo hỏng.")
        if st.button("Đóng", width='stretch'):
            st.rerun()
        st.stop()

    st.write("Vui lòng điền thông tin sự cố thiết bị của bạn:")
    
    device_label = st.selectbox("Chọn thiết bị gặp sự cố *", options=list(my_devices.keys()))
    title = st.text_input("Tiêu đề yêu cầu (Title) *", placeholder="VD: Hỏng màn hình, Máy khởi động chậm...")
    
    colA, colB = st.columns(2)
    with colA:
        maintenance_type = st.selectbox("Phân loại *", options=["Sửa chữa", "Bảo trì định kỳ", "Thay linh kiện"])
    with colB:
        priority = st.selectbox("Độ ưu tiên *", options=["Thấp", "Trung bình", "Cao", "Nghiêm trọng"], index=1)
        
    problem = st.text_area("Mô tả chi tiết vấn đề *", height=100, placeholder="Cung cấp chi tiết biểu hiện lỗi...")
    due_date = st.date_input("Ngày mong muốn hoàn thành", value=date.today())

    st.markdown("---")
    st.write("📸 **Ảnh sự cố thiết bị** (Tối đa 3 ảnh, tùy chọn)")
    
    col_img1, col_img2, col_img3 = st.columns(3)
    with col_img1: img_1 = st.file_uploader("Ảnh 1", type=["jpg", "png", "jpeg"], key="mt_img_1")
    with col_img2: img_2 = st.file_uploader("Ảnh 2", type=["jpg", "png", "jpeg"], key="mt_img_2")
    with col_img3: img_3 = st.file_uploader("Ảnh 3", type=["jpg", "png", "jpeg"], key="mt_img_3")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Gửi yêu cầu", type="primary", width='stretch'):
            if not title.strip() or not problem.strip():
                st.error("⚠️ Vui lòng điền đầy đủ Tiêu đề và Mô tả chi tiết!")
                st.stop()

            selected_device_info = my_devices[device_label]
            data = {
                "device_id": selected_device_info["device_id"],
                "device_allocations_id": selected_device_info["alloc_id"],
                "employee_id": current_emp_id,
                "title": title.strip(),
                "priority": priority,
                "maintenance_type": maintenance_type,
                "problem_description": problem.strip(),
                "due_date": due_date,
                "status": "Đang xác nhận",
                "img_file_1": img_1,
                "img_file_2": img_2,
                "img_file_3": img_3
            }
            
            if create_maintenance_record(data):
                st.success("✅ Đã gửi yêu cầu sửa chữa thành công!")
                st.rerun()
    with c2:
        if st.button("❌ Hủy", width='stretch'):
            st.rerun()

# ---------- DIALOG: CHI TIẾT & CẬP NHẬT TICKET ----------
@st.dialog("📋 Chi tiết Phiếu Yêu Cầu", width="large")
def ticket_detail_popup(ticket: dict):
    # Phần 1: Thông tin Read-only (Mọi người đều thấy)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Mã phiếu:** #{ticket['id']}")
        st.markdown(f"**Thiết bị:** [{ticket['device_code']}] {ticket['device_name']}")
        st.markdown(f"**Người yêu cầu:** {ticket['requester_name']}")
        st.markdown(f"**Tiêu đề:** {ticket['title']}")
        st.markdown(f"**Loại:** {ticket['maintenance_type']}")
        
    with col2:
        st.markdown(f"**Độ ưu tiên:** {ticket['priority']}")
        st.markdown(f"**Ngày tạo:** {ticket['created_at'].strftime('%d/%m/%Y %H:%M') if ticket['created_at'] else '—'}")
        st.markdown(f"**Hạn mong muốn:** {ticket['due_date'].strftime('%d/%m/%Y') if ticket['due_date'] else '—'}")
        st.markdown(f"**Ngày hoàn thành:** {ticket['completion_date'].strftime('%d/%m/%Y') if ticket['completion_date'] else '—'}")

    st.markdown("---")
    st.markdown("**Mô tả sự cố:**")
    st.info(ticket['problem_description'] or "Không có mô tả chi tiết.")

    # Render Hình ảnh sự cố (nếu có)
    images_to_show = [ticket.get('image_url_1'), ticket.get('image_url_2'), ticket.get('image_url_3')]
    images_to_show = [img for img in images_to_show if img] # Lọc các giá trị None
    
    if images_to_show:
        with st.expander(f"📸 Ảnh đính kèm: ({len(images_to_show)} ảnh)", expanded=False):
                img_cols = st.columns(len(images_to_show))
                for idx, img_key in enumerate(images_to_show):
                    img_url = s3_manager.get_presigned_url(img_key)
                    if img_url:
                        img_cols[idx].image(img_url, width='stretch')

    st.markdown("---")
    
    # Phần 2: Khối Cập Nhật Tiến Độ
    st.subheader("🛠️ Tiến độ xử lý")
    
    status_options = ['Đang xác nhận', 'Đang xử lý', 'Hoàn thành', 'Đã hủy']
    
    if can_update_progress:
        # Form cho Admin/IT/duong.bui cập nhật
        with st.form(key=f"update_form_{ticket['id']}"):
            curr_status_idx = status_options.index(ticket['status']) if ticket['status'] in status_options else 0
            
            c_stat, c_cost = st.columns(2)
            with c_stat:
                new_status = st.selectbox("Trạng thái *", options=status_options, index=curr_status_idx)
            with c_cost:
                curr_cost = float(ticket['cost']) if ticket['cost'] else 0.0
                new_cost = st.number_input("Chi phí (VNĐ)", min_value=0.0, value=curr_cost, step=50000.0)
                
            new_solution = st.text_area("Hướng xử lý / Kết quả", value=ticket['solution_description'] or "", height=100)
            
            submit_btn = st.form_submit_button("💾 Lưu Cập Nhật", type="primary", width='stretch')
            
            if submit_btn:
                # Nếu trạng thái chuyển sang "Hoàn thành", tự động set ngày hoàn thành là hôm nay
                completion_dt = date.today() if new_status == 'Hoàn thành' else None
                
                update_data = {
                    "status": new_status,
                    "solution_description": new_solution.strip(),
                    "cost": new_cost,
                    "completion_date": completion_dt
                }
                
                if update_maintenance_record(ticket['id'], update_data):
                    st.success("✅ Cập nhật tiến độ thành công!")
                    st.rerun()
    else:
        # View Read-only cho User thường
        st.markdown(f"**Trạng thái hiện tại:** `{ticket['status']}`")
        st.markdown(f"**Chi phí báo giá:** {float(ticket['cost']):,.0f} VNĐ" if ticket['cost'] else "**Chi phí:** Chưa có")
        st.markdown("**Hướng xử lý từ IT:**")
        st.success(ticket['solution_description'] or "IT đang kiểm tra và chưa cập nhật hướng xử lý.")

    if st.button("Đóng hộp thoại", width='stretch'):
        st.rerun()

# ---------- MAIN VIEW ----------
st.title("🛠️ Quản Lý Bảo Hành & Sửa Chữa")
st.markdown("---")

st.subheader("🔍 Bộ Lọc")

# Trích xuất các giá trị duy nhất từ dữ liệu gốc để làm options cho bộ lọc
all_status = sorted(list(set([r['status'] for r in records if r['status']])))
all_priorities = sorted(list(set([r['priority'] for r in records if r['priority']])))
all_requesters = sorted(list(set([r['requester_name'] for r in records if r['requester_name']])))

col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1], vertical_alignment="bottom")
with col_f1: 
    st.multiselect("Trạng thái", options=all_status, key="mt_filter_status")
with col_f2: 
    st.multiselect("Độ ưu tiên", options=all_priorities, key="mt_filter_priority")
with col_f3: 
    # Nếu là user thường, dropdown này chỉ có tên của họ. Nếu là Admin, sẽ có tên toàn bộ nv đã tạo phiếu.
    st.multiselect("Người yêu cầu", options=all_requesters, key="mt_filter_requester")
with col_f4:
    st.button("🔄 Xóa bộ lọc", width='stretch', on_click=clear_mt_filters)

# --- 2. ÁP DỤNG LOGIC LỌC DỮ LIỆU ---
filtered_records = records.copy()

if st.session_state.mt_filter_status: 
    filtered_records = [r for r in filtered_records if r['status'] in st.session_state.mt_filter_status]
    
if st.session_state.mt_filter_priority: 
    filtered_records = [r for r in filtered_records if r['priority'] in st.session_state.mt_filter_priority]
    
if st.session_state.mt_filter_requester: 
    filtered_records = [r for r in filtered_records if r['requester_name'] in st.session_state.mt_filter_requester]

st.markdown("---")

col_title, col_btn = st.columns([8.5, 1.5], vertical_alignment="bottom")
with col_title:
    st.subheader(f"📋 Danh sách phiếu yêu cầu ({len(records)} phiếu)")
with col_btn:
    if st.button("➕ Báo Cáo Sự Cố", type="primary", width='stretch'):
        create_ticket_popup()

st.markdown("<br>", unsafe_allow_html=True)

# Hiển thị Bảng dữ liệu bằng Native DataFrame (Tối ưu chống Lag)
if not records:
    st.info("Chưa có phiếu yêu cầu bảo hành / sửa chữa nào.")
else:
    df = pd.DataFrame(records)
    
    # Enrich data cho DataFrame
    df['Thiết bị'] = df['device_code'] + " - " + df['device_name']
    df['Ngày Tạo'] = pd.to_datetime(df['created_at']).dt.strftime('%d/%m/%Y %H:%M')
    
    display_df = df[['Thiết bị', 'requester_name', 'title', 'priority', 'status', 'Ngày Tạo']].copy()
    display_df.columns = ['Thiết bị', 'Người Yêu Cầu', 'Sự cố', 'Ưu Tiên', 'Trạng Thái', 'Ngày Tạo']
    
    st.write("👉 **Nhấn vào một dòng bất kỳ trong bảng để xem chi tiết hoặc cập nhật tiến độ.**")
    
    selection = st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"ticket_table_{st.session_state.ticket_df_key}"
    )

    # Hiển thị Thanh công cụ (Action Toolbar) khi click chọn 1 dòng
    selected_rows = selection.selection.rows
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_ticket = records[selected_idx]
        
        st.markdown("---")
        c1, c2, c3 = st.columns([6, 2, 2], vertical_alignment="center")
        with c1:
            st.markdown(f"🛠️ **Thao tác với phiếu:** `#{selected_ticket['id']} - {selected_ticket['title']}`")
        with c2:
            btn_label = "👁️ Cập Nhật Tiến Độ" if can_update_progress else "👁️ Xem Chi Tiết"
            if st.button(btn_label, type="primary", width='stretch'):
                ticket_detail_popup(selected_ticket)
        with c3:
            st.button("❌ Bỏ chọn", width='stretch', on_click=clear_ticket_selection)