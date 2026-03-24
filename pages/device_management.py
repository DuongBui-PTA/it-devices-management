# pages/device_management.py

import streamlit as st
import pandas as pd
from datetime import datetime, date

from services.device_services import get_devices, create_device, update_device, delete_device, s3_manager
from services.device_category_services import get_device_categories, create_device_category
from services.device_allocation_services import get_allocations, allocate_device, return_device
from services.employee_services import get_employees, get_companies, get_departments, get_positions
from utils.auth import AuthManager

st.set_page_config(page_title="Quản lý Thiết bị IT", page_icon="💻", layout="wide")

# ==========================================
# BẮT BUỘC ĐĂNG NHẬP
# ==========================================
auth_manager = AuthManager()
auth_manager.require_auth()

# ---------- Quản lý Trạng thái (Session State) ----------
if 'show_form' not in st.session_state:
    st.session_state.show_form = False
if 'form_mode' not in st.session_state:
    st.session_state.form_mode = 'add'
if 'selected_device' not in st.session_state:
    st.session_state.selected_device = None
if "device_df_key" not in st.session_state:
    st.session_state.device_df_key = 0

# Thêm hàm callback để reset bảng
def clear_device_selection():
    st.session_state.device_df_key += 1

# ---------- Fetch Data (TỐI ƯU CACHE) ----------
def load_management_data():
    st.session_state.all_categories = get_device_categories(include_deleted=False)
    st.session_state.all_employees = get_employees({"status": "ACTIVE"})
    st.session_state.all_allocations_history = get_allocations({}) 
    st.session_state.all_depts = get_departments()
    st.session_state.all_positions = get_positions()
    st.session_state.all_companies = get_companies()
    st.session_state.raw_devices = get_devices()

# Chỉ gọi database nếu cache chưa tồn tại
if "dm_data_loaded" not in st.session_state:
    load_management_data()
    st.session_state.dm_data_loaded = True

# Lấy dữ liệu từ cache để sử dụng
all_categories = st.session_state.all_categories
all_employees = st.session_state.all_employees
all_depts = st.session_state.all_depts
all_positions = st.session_state.all_positions
all_companies = st.session_state.all_companies
raw_devices = st.session_state.raw_devices
all_allocations_history = st.session_state.all_allocations_history

# Tạo mapping để truy xuất nhanh
emp_map = {e['id']: e for e in all_employees}
cat_map = {c['category_name']: c['category_id'] for c in all_categories}
comp_map = {c['company_name']: c['id'] for c in all_companies}
emp_name_map = {e['full_name']: e['id'] for e in all_employees}

# Lấy các phiếu Đang cấp phát mới nhất để map vào danh sách thiết bị
alloc_map = {}
for a in all_allocations_history:
    if a['status'] == 'Đang cấp phát':
        if a['device_id'] not in alloc_map:
            alloc_map[a['device_id']] = a

# ---------- Helpers ----------
def can_delete_device(status: str) -> bool:
    allowed = {"Hỏng", "Chưa sử dụng", "Thanh lý", "Thất lạc"}
    return status in allowed

# Enrich thiết bị (Gắn thêm tên người dùng hiện tại vào dữ liệu gốc)
devices = []
for d in raw_devices:
    d_enriched = dict(d)
    alloc = alloc_map.get(d['id'])
    if alloc:
        d_enriched['current_employee_id'] = alloc['employee_id']
        d_enriched['current_department_id'] = alloc.get('department_id')
        d_enriched['current_allocation_id'] = alloc['id']
        
        if alloc['employee_id']:
            # CẤP PHÁT CHO CÁ NHÂN
            emp = emp_map.get(alloc['employee_id'])
            user_name = emp['full_name'] if emp else alloc['employee_name']
            dept_name = emp['department_name'] if emp and emp.get('department_name') else "—"
        elif alloc.get('department_id'):
            # CẤP PHÁT CHO PHÒNG BAN
            user_name = "🏢 Dùng chung"
            dept_name = alloc['department_name']
        else:
            user_name = "—"
            dept_name = "—"
            
        d_enriched['current_user_name'] = user_name
        d_enriched['current_department'] = dept_name
    else:
        d_enriched['current_employee_id'] = None
        d_enriched['current_department_id'] = None
        d_enriched['current_user_name'] = ""
        d_enriched['current_allocation_id'] = None
        d_enriched['current_department'] = ""
        
    devices.append(d_enriched)

# ---------- Dialogs ----------
@st.dialog("➕ Thêm loại thiết bị", width="small")
def add_device_type_popup():
    st.write("Nhập thông tin loại thiết bị mới:")
    code = st.text_input("Mã loại thiết bị *")
    name = st.text_input("Tên loại thiết bị *")
    note = st.text_area("Ghi chú (tùy chọn)", height=80)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Lưu", type="primary", width='stretch'):
            if not code or not name:
                st.error("⚠️ Vui lòng nhập **Mã loại** và **Tên loại**.")
                st.stop()
            
            if create_device_category({"code": code, "name": name, "note": note}):
                st.success("✅ Đã thêm loại thiết bị mới!")
                if "device_categories" in st.session_state: del st.session_state["device_categories"]
                if "category_device_count" in st.session_state: del st.session_state["category_device_count"]
                if "dm_data_loaded" in st.session_state: del st.session_state["dm_data_loaded"]
                st.rerun()
    with c2:
        if st.button("❌ Hủy", width='stretch'):
            st.rerun()

@st.dialog("📄 Chi tiết thiết bị", width="large")
def show_detail_popup(device: dict):
    history = [h for h in all_allocations_history if h['device_id'] == device['id']]
    latest_alloc = history[0] if history else None
    
    alloc_user, alloc_by = '—', '—'
    alloc_date = latest_alloc['allocation_date'] if latest_alloc else '—'
    alloc_ret = latest_alloc['return_date'] if latest_alloc else '—'
    
    is_active = device['status'] == 'Đang sử dụng'
    user_label = "**Người dùng hiện tại:**" if is_active else "**Người dùng (gần nhất):**"

    if latest_alloc:
        if latest_alloc['employee_id']:
            alloc_user = latest_alloc['employee_name']
        if latest_alloc['allocated_by_employee_id']:
            alloc_by = latest_alloc['allocated_by_name']

    purchaser_id = device.get('purchased_by_employee_id')
    purchaser_name = emp_map[purchaser_id]['full_name'] if purchaser_id and purchaser_id in emp_map else '—'
    
    price_val = device.get('price')
    price_str = f"{price_val:,.0f} VNĐ" if price_val else "—"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**ID:** {device['id']} | **Mã TB:** `{device['device_code']}`")
        st.write(f"**Tên thiết bị:** {device['device_name']}")
        st.write(f"**Loại:** {device.get('category_name', '—')}")
        st.write(f"**Serial:** {device.get('serial_number', '—')}")
        st.write(f"**Nhà sản xuất:** {device.get('manufacturer_name', '—')}")
        st.write(f"**Nhà cung cấp:** {device.get('supplier_name', '—')}")
        st.write(f"**Người mua:** {purchaser_name}")
        st.write(f"**Ngày mua:** {device.get('purchase_date', '—')}")
        st.write(f"**Giá mua:** {price_str}")
        st.write(f"**Ngày hết BH:** {device.get('warranty_date', '—')}")

    with col2:
        st.write(f"**Trạng thái:** {device['status']}")
        st.write(f"**Vị trí:** {device.get('location', '—')}")
        st.write(f"{user_label} {alloc_user}")
        st.write(f"**Phòng ban:** {device.get('current_department') or '—'}")
        st.write(f"**Người cấp phát:** {alloc_by}")
        st.write(f"**Ngày cấp phát:** {alloc_date}")
        st.write(f"**Ngày thu hồi:** {alloc_ret}")

    st.markdown("---")
    st.write(f"**Cấu hình thiết bị:** \n{device.get('system_summary') or '—'}")
    st.write(f"**Ghi chú:** \n{device.get('notes', '—')}")

    st.markdown("---")
    
    # Gom 3 ảnh vào một list nếu có giá trị
    images_to_show = []
    for col in ['image_url', 'image_url_2', 'image_url_3']:
        if device.get(col):
            images_to_show.append(device[col])

    has_files = bool(images_to_show) or bool(device.get('invoice_url'))
    
    if has_files:
        st.write("**Tài liệu đính kèm:**")
        
        # Hiển thị Hóa đơn trước
        if device.get('invoice_url'):
            inv_url = s3_manager.get_presigned_url(device['invoice_url'])
            if inv_url:
                st.markdown(f"📎 **[Nhấn vào đây để Tải/Xem Hóa đơn]({inv_url})**")
        else:
            st.info("Không có hóa đơn mua hàng")
            
        # Hiển thị Ảnh thiết bị theo cột
        if images_to_show:
            with st.expander(f"📸 Xem ảnh thiết bị ({len(images_to_show)} ảnh)", expanded=False):
                img_cols = st.columns(len(images_to_show))
                for idx, img_key in enumerate(images_to_show):
                    img_url = s3_manager.get_presigned_url(img_key)
                    if img_url:
                        img_cols[idx].image(img_url, width='stretch')
        else:
            st.info("Không có ảnh thiết bị")

    st.markdown("---")

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("✏️ Sửa", width='stretch'):
            # Gán thiết bị cần sửa vào biến Trigger
            st.session_state.trigger_edit_device = device
            # Rerun để đóng popup Chi tiết
            st.rerun()
    with colB:
        if st.button("Đóng", type="primary", width='stretch'):
            st.rerun()

    st.markdown("---")
    with st.expander("📜 Lịch sử cấp phát", expanded=False):
        if not history:
            st.info("Chưa có lịch sử cấp phát.")
        else:
            df_history = pd.DataFrame(history)
            df_history = df_history[['id', 'employee_name', 'allocation_date', 'return_date', 'status', 'notes']]
            df_history.columns = ['ID Cấp phát', 'Người dùng', 'Ngày cấp', 'Ngày thu hồi', 'Trạng thái', 'Ghi chú']
            st.dataframe(df_history, width='stretch', hide_index=True)

@st.dialog("🗑️ Xác nhận xóa", width="small")
def confirm_delete_popup(device: dict):
    if not can_delete_device(device['status']):
        st.error("⛔ Chỉ được phép xóa thiết bị có trạng thái **Hỏng, Chưa sử dụng, Thanh lý, Thất lạc**.")
        if st.button("❌ Đóng", width='stretch'):
            st.rerun()
        return

    st.warning("Bạn có chắc chắn muốn xóa thiết bị này không?")
    st.markdown(f"**Mã TB:** {device['device_code']} <br> **Tên:** {device['device_name']}", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Xóa", type="primary", width='stretch'):
            if delete_device(device["id"]):
                st.success("✅ Xóa thiết bị thành công!")
                if "dm_data_loaded" in st.session_state: del st.session_state["dm_data_loaded"]
                st.rerun()
    with c2:
        if st.button("❌ Hủy", width='stretch'):
            st.rerun()

@st.dialog("👤 Cấp phát / Thu hồi", width="medium") 
def assign_popup(device: dict):
    # Kiểm tra xem thiết bị có đang được cấp phát hay không
    has_owner = bool(device.get("current_allocation_id"))
    mode = st.radio("Chế độ", ["Cấp phát", "Thu hồi"], horizontal=True)

    if mode == "Thu hồi" and not has_owner:
        st.warning("Thiết bị chưa được cấp phát cho ai nên không thể thu hồi.")
        if st.button("❌ Đóng", width='stretch'):
            st.rerun()
        st.stop()

    if mode == "Cấp phát":
        # --- 1. LẤY TRẠNG THÁI HIỆN TẠI ĐỂ GÁN MẶC ĐỊNH ---
        current_emp_id = device.get("current_employee_id")
        current_dept_id = device.get("current_department_id")
        logged_in_emp_id = st.session_state.get("employee_id")
        
        # Nếu đang cấp cho phòng ban thì mặc định chọn radio "Phòng ban"
        default_radio_idx = 1 if current_dept_id and not current_emp_id else 0
        alloc_type = st.radio("Cấp phát cho:", ["Cá nhân", "Phòng ban (Dùng chung)"], index=default_radio_idx, horizontal=True)
        
        # --- 2. TẠO DANH SÁCH OPTIONS ---
        # Load danh sách Nhân sự
        emp_options = {"(Chọn nhân sự)": None} 
        for e in all_employees:
            emp_options[e["full_name"]] = e["id"]
        emp_names = list(emp_options.keys())
        
        # Load danh sách Phòng ban
        dept_options = {"(Chọn phòng ban)": None}
        for d in all_depts:
            dept_options[d["name"]] = d["id"]
        dept_names = list(dept_options.keys())
        
        # --- 3. TÍNH TOÁN VỊ TRÍ (INDEX) MẶC ĐỊNH CHO CÁC DROPDOWN ---
        # 3.1. Người sử dụng mặc định (người đang giữ thiết bị)
        default_user_idx = 0
        if current_emp_id:
            curr_user_name = next((name for name, eid in emp_options.items() if eid == current_emp_id), None)
            if curr_user_name in emp_names:
                default_user_idx = emp_names.index(curr_user_name)

        # 3.2. Phòng ban mặc định (phòng đang giữ thiết bị)
        default_dept_idx = 0
        if current_dept_id:
            curr_dept_name = next((name for name, did in dept_options.items() if did == current_dept_id), None)
            if curr_dept_name in dept_names:
                default_dept_idx = dept_names.index(curr_dept_name)
                
        # 3.3. Người thực hiện cấp phát mặc định (Tài khoản đang đăng nhập)
        allocator_options = [name for name in emp_names if name != "(Chọn nhân sự)"]
        allocator_default_idx = 0
        if logged_in_emp_id:
            logged_in_name = next((name for name, eid in emp_options.items() if eid == logged_in_emp_id), None)
            if logged_in_name in allocator_options:
                allocator_default_idx = allocator_options.index(logged_in_name)
        
        # --- 4. HIỂN THỊ UI ---
        selected_name = "(Chọn nhân sự)"
        selected_dept = "(Chọn phòng ban)"
        
        if alloc_type == "Cá nhân":
            selected_name = st.selectbox("Người sử dụng *", options=emp_names, index=default_user_idx)
        else:
            selected_dept = st.selectbox("Phòng ban nhận *", options=dept_names, index=default_dept_idx)

        allocated_by_name = st.selectbox("Người thực hiện cấp phát *", options=allocator_options, index=allocator_default_idx)
        
        assigned_dt = st.date_input("Ngày cấp phát", value=date.today())
        note = st.text_area("Ghi chú (tùy chọn)", height=80)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Xác nhận cấp phát", type="primary", width='stretch'):
                
                user_id_to_save = None
                dept_id_to_save = None

                # VALIDATE DỮ LIỆU
                if alloc_type == "Cá nhân":
                    if selected_name == "(Chọn nhân sự)":
                        st.error("⚠️ Vui lòng chọn Người sử dụng thiết bị!")
                        st.stop()
                    user_id_to_save = emp_options[selected_name]
                else:
                    if selected_dept == "(Chọn phòng ban)":
                        st.error("⚠️ Vui lòng chọn Phòng ban nhận thiết bị!")
                        st.stop()
                    dept_id_to_save = dept_options[selected_dept]

                alloc_id_to_save = emp_options.get(allocated_by_name)

                if has_owner and device.get("current_allocation_id"):
                    return_device(device["current_allocation_id"], device["id"], assigned_dt, "Tự động thu hồi do cấp phát mới.")
                
                # GÓI PAYLOAD GỬI XUỐNG SERVICE
                alloc_data = {
                    "device_id": device["id"],
                    "employee_id": user_id_to_save,
                    "department_id": dept_id_to_save,
                    "allocated_by_employee_id": alloc_id_to_save,
                    "allocation_date": assigned_dt,
                    "notes": note.strip()
                }
                
                if allocate_device(alloc_data):
                    st.success("✅ Cấp phát thành công!")
                    if "dm_data_loaded" in st.session_state: del st.session_state["dm_data_loaded"]
                    st.rerun()
        with c2:
            if st.button("❌ Hủy", width='stretch'):
                st.rerun()
    else:
        # Code phần Thu hồi giữ nguyên...
        st.warning("Thu hồi sẽ chuyển trạng thái thiết bị về **Chưa sử dụng**.")
        st.markdown(f"**Đang cấp phát cho:** {device['current_user_name']}")

        returned_dt = st.date_input("Ngày thu hồi", value=date.today())
        note = st.text_area("Ghi chú thu hồi (tùy chọn)", height=80)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🧾 Xác nhận thu hồi", type="primary", width='stretch'):
                if return_device(device["current_allocation_id"], device["id"], returned_dt, note):
                    st.success("✅ Thu hồi thành công!")
                    if "dm_data_loaded" in st.session_state: del st.session_state["dm_data_loaded"]
                    st.rerun()
        with c2:
            if st.button("❌ Hủy", width='stretch'):
                st.rerun()

# ---------- Form Thêm / Sửa Thiết Bị ----------
@st.dialog("💻 Thông tin Thiết bị", width="large")
def show_device_form_popup(mode='add', device=None):
    cat_names = list(cat_map.keys())
    if not cat_names: cat_names = ["(Chưa có loại thiết bị)"]
    cat_names.append("Khác (Thêm mới...)")

    comp_names = list(comp_map.keys())
    if not comp_names: comp_names = ["(Chưa có dữ liệu Công ty)"]
    emp_names = ["(Trống)"] + list(emp_name_map.keys())

    status_options = ["Chưa sử dụng", "Đang sử dụng", "Hỏng", "Bảo trì", "Thanh lý", "Thất lạc"]

    st.subheader("➕ Thêm Thiết Bị Mới" if mode == 'add' else "✏️ Chỉnh Sửa Thiết Bị")
    
    default_cat = device.get('category_name') if device else cat_names[0]
    default_idx = cat_names.index(default_cat) if default_cat in cat_names else 0
    type_key = f"cat_select_{mode}_{device['id'] if device else 'new'}"

    selected_cat_name = st.selectbox("Loại thiết bị *", options=cat_names, index=default_idx, key=type_key)

    new_cat_code = ""
    new_cat_name = ""
    new_cat_notes = ""
    new_cat_alloc = "Cá nhân"
    new_cat_tech = "Thiết bị người dùng cuối (Laptop, PC...)"
    if selected_cat_name == "Khác (Thêm mới...)":
        st.info("💡 Bạn đang chọn tạo Loại thiết bị mới. Vui lòng nhập thông tin bên dưới:")
        # Hàng 1: Mã và Tên
        c_new1, c_new2 = st.columns(2)
        with c_new1: 
            new_cat_code = st.text_input("Mã loại thiết bị mới *", key=f"new_cat_code_{mode}")
        with c_new2: 
            new_cat_name = st.text_input("Tên loại thiết bị mới *", key=f"new_cat_name_{mode}")
            
        # Hàng 2: Phân loại cấp phát và Chức năng kỹ thuật
        c_new3, c_new4 = st.columns(2)
        
        # Danh sách tùy chọn giống hệt bên trang device_category_management
        alloc_options = ['Cá nhân', 'Phòng ban/Dùng chung', 'Vật tư tiêu hao']
        tech_options = [
            'Thiết bị người dùng cuối (Laptop, PC...)', 
            'Thiết bị ngoại vi (Màn hình, Chuột...)', 
            'Thiết bị mạng (Router, Switch...)', 
            'Thiết bị văn phòng (Máy in, Scanner...)', 
            'Hạ tầng & Máy chủ (Server, UPS...)',
            'Khác'
        ]
        
        with c_new3:
            new_cat_alloc = st.selectbox("Nghiệp vụ cấp phát", options=alloc_options, key=f"new_cat_alloc_{mode}")
        with c_new4:
            new_cat_tech = st.selectbox("Chức năng kỹ thuật", options=tech_options, key=f"new_cat_tech_{mode}")

        # Hàng 3: Ghi chú
        new_cat_notes = st.text_input("Ghi chú loại thiết bị mới", key=f"new_cat_notes_{mode}")

    with st.form(key='device_form'):
        col1, col2, col3 = st.columns(3)
        with col1:
            code = st.text_input("Mã thiết bị *", value=device.get('device_code', '') if device else "")
        with col2:
            name = st.text_input("Tên thiết bị *", value=device.get('device_name', '') if device else "")
        with col3:
            serial = st.text_input("Số serial *", value=device.get('serial_number', '') if device else "")

        col_nsx, col_ncc = st.columns(2)
        with col_nsx:
            m_def = device.get('manufacturer_name') if device else None
            m_idx = comp_names.index(m_def) if m_def in comp_names else 0
            manufacturer = st.selectbox("Nhà sản xuất *", options=comp_names, index=m_idx)
        with col_ncc:
            s_def = device.get('supplier_name') if device else None
            s_idx = comp_names.index(s_def) if s_def in comp_names else 0
            supplier = st.selectbox("Nhà cung cấp *", options=comp_names, index=s_idx)

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            p_def_id = device.get('purchased_by_employee_id') if device else None
            p_def_name = next((e['full_name'] for e in all_employees if e['id'] == p_def_id), "(Trống)")
            p_idx = emp_names.index(p_def_name) if p_def_name in emp_names else 0
            purchased_by = st.selectbox("Người mua", options=emp_names, index=p_idx)
        with col_p2:
            def parse_date(d_str): return d_str if d_str else date.today()
            purchase_date = st.date_input("Ngày mua", value=parse_date(device.get('purchase_date')) if device else date.today())
        with col_p3:
            price = st.number_input("Giá mua (VNĐ)", min_value=0.0, value=float(device.get('price') or 0.0) if device else 0.0, step=100000.0)

        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            warranty_date = st.date_input("Ngày hết bảo hành", value=parse_date(device.get('warranty_date')) if device else date.today())
        with col_w2:
            if mode == "add":
                status = st.selectbox("Trạng thái *", ["Chưa sử dụng"], disabled=True)
            else:
                s_idx = status_options.index(device.get("status", "Chưa sử dụng")) if device.get("status") in status_options else 0
                status = st.selectbox("Trạng thái *", status_options, index=s_idx)
        with col_w3:
            location = st.text_input("Vị trí thiết bị", value=device.get('location', '') if device else "")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            system_summary = st.text_area("Cấu hình thiết bị", value=device.get('system_summary', '') if device else "", height=80)
        with col_t2:
            notes = st.text_area("Ghi chú", value=device.get('notes', '') if device else "", height=80)

        st.markdown("---")
        st.write("📸 **Ảnh thiết bị** (Tối đa 3 ảnh, tùy chọn)")
        col_img1, col_img2, col_img3 = st.columns(3)
        with col_img1:
            img_file_1 = st.file_uploader("Ảnh 1", type=["jpg", "png", "jpeg"], key=f"img1_{mode}")
        with col_img2:
            img_file_2 = st.file_uploader("Ảnh 2", type=["jpg", "png", "jpeg"], key=f"img2_{mode}")
        with col_img3:
            img_file_3 = st.file_uploader("Ảnh 3", type=["jpg", "png", "jpeg"], key=f"img3_{mode}")

        st.write("🧾 **Hóa đơn mua hàng**")
        purchase_invoice = st.file_uploader("Upload hóa đơn (Tùy chọn)", type=["pdf", "jpg", "png", "jpeg"])

        col_submit, col_cancel = st.columns(2)
        submitted = col_submit.form_submit_button("💾 Lưu", type="primary", width='stretch')
        cancelled = col_cancel.form_submit_button("❌ Hủy", type="secondary", width='stretch')

        if submitted:
            # --- XỬ LÝ LOẠI THIẾT BỊ TRƯỚC ---
            final_cat_id = None
            if selected_cat_name == "Khác (Thêm mới...)":
                if not new_cat_code or not new_cat_name:
                    st.error("⚠️ Vui lòng nhập đầy đủ Mã và Tên cho Loại thiết bị mới ở phía trên.")
                    st.stop()

                payload_new_cat = {
                    "code": new_cat_code, 
                    "name": new_cat_name, 
                    "allocation_type": new_cat_alloc,     # <--- Giá trị mới từ giao diện
                    "technical_function": new_cat_tech,   # <--- Giá trị mới từ giao diện
                    "note": new_cat_notes
                }
                
                # Gọi service tạo Danh mục mới
                if not create_device_category(payload_new_cat):
                    st.stop()
                
                # Cập nhật lại cache và lấy ID của loại thiết bị vừa tạo
                load_management_data()
                updated_cat_map = {c['category_name']: c['category_id'] for c in st.session_state.all_categories}
                final_cat_id = updated_cat_map.get(new_cat_name)
            else:
                final_cat_id = cat_map.get(selected_cat_name)

            # --- KIỂM TRA THÔNG TIN THIẾT BỊ ---
            if not code or not name or not serial:
                st.error("⚠️ Vui lòng điền các trường bắt buộc (*)")
                st.stop()
            if not comp_map.get(manufacturer) or not comp_map.get(supplier):
                st.error("⚠️ Vui lòng chọn NSX và NCC.")
                st.stop()

            device_data = {
                'device_code': code,
                'device_name': name,
                'category_id': final_cat_id,
                'serial_number': serial,
                'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                'warranty_date': warranty_date.strftime('%Y-%m-%d'),
                'status': status,
                'notes': notes,
                'manufacturer_id': comp_map.get(manufacturer),
                'supplier_id': comp_map.get(supplier),
                'purchased_by_employee_id': emp_name_map.get(purchased_by) if purchased_by != "(Trống)" else None,
                'price': price,
                'system_summary': system_summary,
                'location': location,
                'img_file_1': img_file_1,
                'img_file_2': img_file_2,
                'img_file_3': img_file_3,
                'inv_file': purchase_invoice
            }

            if mode == 'add':
                if create_device(device_data):
                    st.success("✅ Thêm thành công!")
                    if "dm_data_loaded" in st.session_state: del st.session_state["dm_data_loaded"]
                    st.rerun()
            else:
                if update_device(device['id'], device_data):
                    st.success("✅ Cập nhật thành công!")
                    if "dm_data_loaded" in st.session_state: del st.session_state["dm_data_loaded"]
                    st.rerun()

        if cancelled:
            st.rerun()

# ---------- Main View ----------
st.title("💻 Quản Lý Thiết Bị IT")
st.markdown("---")
st.subheader("🔍 Bộ Lọc")

def clear_device_filters():
    st.session_state.filter_type = []
    st.session_state.filter_status = []
    st.session_state.filter_department = []

all_types = sorted(list(set([d.get('category_name') or 'N/A' for d in devices])))
all_status = sorted(list(set([d['status'] for d in devices])))
all_dept = sorted(list(set([d.get('current_department') or 'N/A' for d in devices])))

col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1], vertical_alignment="bottom")
with col_f1: st.multiselect("Loại thiết bị", options=all_types, key="filter_type")
with col_f2: st.multiselect("Trạng thái", options=all_status, key="filter_status")
with col_f3: st.multiselect("Phòng ban", options=all_dept, key="filter_department")
with col_f4:
    st.button("🔄 Xóa bộ lọc", width='stretch', on_click=clear_device_filters)

filtered_devices = devices.copy()
if st.session_state.get("filter_type"): 
    filtered_devices = [d for d in filtered_devices if (d.get('category_name') or 'N/A') in st.session_state.filter_type]
if st.session_state.get("filter_status"): 
    filtered_devices = [d for d in filtered_devices if d['status'] in st.session_state.filter_status]
if st.session_state.get("filter_department"): 
    filtered_devices = [d for d in filtered_devices if (d.get('current_department') or 'N/A') in st.session_state.filter_department]

st.markdown("---")

bar1, bar2 = st.columns([10, 1.2])
with bar1:
    st.subheader(f"📋 Danh Sách Thiết Bị ({len(filtered_devices)} thiết bị)")
with bar2:
    if st.button("➕ Thêm Mới", type="primary", width='stretch'):
        show_device_form_popup('add')

# --- Bảng danh sách ---
if not filtered_devices:
    st.info("Không có thiết bị nào phù hợp với bộ lọc.")
else:
    # 1. Chuyển đổi dữ liệu sang Pandas DataFrame để render siêu tốc
    df = pd.DataFrame(filtered_devices)
    
    # Chỉ chọn các cột cần hiển thị và đổi tên cho đẹp
    display_df = df[['device_code', 'device_name', 'category_name', 'current_user_name', 'current_department', 'status', 'location']].copy()
    display_df.columns = ['Mã TB', 'Tên thiết bị', 'Loại', 'Người dùng', 'Phòng ban', 'Trạng thái', 'Vị trí']
    
    # Xử lý các giá trị None/NaN để bảng không hiển thị lỗi
    display_df.fillna("—", inplace=True)

    # BẮT TRIGGER ĐỂ MỞ POPUP SỬA TỪ BÊN NGOÀI
    if st.session_state.get("trigger_edit_device"):
        d_obj = st.session_state.trigger_edit_device
        # Xóa biến trigger ngay lập tức
        st.session_state.trigger_edit_device = None
        # Mở popup Sửa
        show_device_form_popup('edit', d_obj)

    st.write("👉 **Nhấn vào một dòng bất kỳ trong bảng để xem các thao tác (Xem, Sửa, Cấp phát, Xóa).**")

    # 2. Render bảng bằng st.dataframe (Hỗ trợ cuộn, sắp xếp, tải hàng vạn dòng không lag)
    selection = st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"device_table_{st.session_state.device_df_key}"
    )

    # 3. Hiển thị thanh công cụ thao tác (Action Toolbar) ở DƯỚI bảng khi có dòng được chọn
    selected_rows = selection.selection.rows
    if selected_rows:
        # Lấy thông tin thiết bị từ index của dòng được chọn
        selected_idx = selected_rows[0]
        selected_device = filtered_devices[selected_idx]
        
        st.markdown("---")
        st.markdown(f"🛠️ **Đang thao tác với:** `{selected_device['device_code']} - {selected_device['device_name']}`")
        
        # Tạo hàng nút bấm gọn gàng
        a1, a2, a3, a4, a5, _ = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 2.5]) 
        
        if a1.button("👁️ Xem chi tiết", type="primary", width='stretch'): 
            show_detail_popup(selected_device) 
            
        if a2.button("✏️ Sửa", width='stretch'):
            show_device_form_popup('edit', selected_device)
            
        if a3.button("👤 Cấp phát/Thu hồi", width='stretch'): 
            assign_popup(selected_device) 
            
        if a4.button("🗑️ Xóa", disabled=not can_delete_device(selected_device['status']), width='stretch'): 
            confirm_delete_popup(selected_device)

        with a5:
            st.button("❌ Bỏ chọn", width='stretch', on_click=clear_device_selection)