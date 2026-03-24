import streamlit as st
import pandas as pd
from datetime import datetime
import logging

from utils.auth import AuthManager
from services.device_services import get_devices
from services.device_allocation_services import get_allocations
from services.employee_services import get_employees
from services.device_maintenance_services import get_maintenance_records

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="IT Asset Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

auth = AuthManager()

def show_login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Đăng nhập hệ thống")
            
            username = st.text_input(
                "Tên đăng nhập",
                placeholder="Nhập username của bạn",
            )
            
            password = st.text_input(
                "Mật khẩu",
                type="password",
                placeholder="Nhập mật khẩu"
            )
            
            c1, c2 = st.columns(2)
            with c1:
                submit = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
            with c2:
                st.form_submit_button("Quên mật khẩu?", disabled=True, use_container_width=True, help="Liên hệ IT để reset mật khẩu")
            
            if submit:
                if username and password:
                    success, result = auth.authenticate(username, password)
                    if success:
                        auth.login(result)
                        st.rerun()
                    else:
                        error_msg = result.get("error", "Đăng nhập thất bại")
                        st.error(f"❌ {error_msg}")
                else:
                    st.warning("⚠️ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu")

def main_app():
    # --- HEADER ---
    col1, col2, col3 = st.columns([2, 2, 1], vertical_alignment="center")
    with col1:
        st.markdown(f"### 📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    with col2:
        st.markdown(f"### 👤 Xin chào, **{auth.get_user_display_name()}**")
    with col3:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            auth.logout()
            st.rerun()

    st.markdown("---")

    # --- TẢI & CHUẨN BỊ DỮ LIỆU ---
    all_devices = get_devices()
    active_allocations = get_allocations({"status": "Đang cấp phát"})
    employees = get_employees()
    maintenance_records = get_maintenance_records()

    # Map dữ liệu để query nhanh
    alloc_map = {a['device_id']: a for a in active_allocations}
    emp_map = {e['id']: e for e in employees}

    # Enrich data: Gắn thông tin phòng ban, người dùng, giá trị cho thiết bị
    enriched_devices = []
    total_asset_value = 0.0

    for d in all_devices:
        alloc = alloc_map.get(d['id'])
        dept_name = "Kho IT (Chưa phân bổ)"
        user_name = "—"
        alloc_type = "—"
        price = float(d.get('price') or 0)
        total_asset_value += price

        if alloc:
            if alloc.get('employee_id'):
                emp = emp_map.get(alloc['employee_id'])
                user_name = emp['full_name'] if emp else "Unknown"
                dept_name = emp['department_name'] if emp and emp.get('department_name') else "Khác"
                alloc_type = "Cá nhân"
            elif alloc.get('department_id'):
                user_name = "🏢 Dùng chung"
                dept_name = alloc.get('department_name', "Unknown")
                alloc_type = "Phòng ban"

        enriched_devices.append({
            'Tên thiết bị': d['device_name'],
            'Mã TB': d['device_code'],
            'Danh mục': d.get('category_name', 'Chưa phân loại'),
            'Trạng thái': d['status'],
            'Phòng ban': dept_name,
            'Người dùng': user_name,
            'Loại cấp phát': alloc_type,
            'Giá trị': price
        })

    df_devices = pd.DataFrame(enriched_devices)

    # --- KHỐI 1: TỔNG QUAN (METRICS) ---
    st.subheader("📈 Tổng quan tài sản")
    
    total_devices = len(all_devices)
    in_use = sum(1 for d in all_devices if d['status'] == 'Đang sử dụng')
    in_stock = sum(1 for d in all_devices if d['status'] == 'Chưa sử dụng')
    maintenance = sum(1 for d in all_devices if d['status'] == 'Bảo trì')
    broken = sum(1 for d in all_devices if d['status'] == 'Hỏng')
    liquidated = sum(1 for d in all_devices if d['status'] == 'Thanh lý')

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Tổng thiết bị", total_devices)
    m2.metric("Đang sử dụng", in_use, f"{round(in_use/total_devices*100, 1)}%" if total_devices else "0%")
    m3.metric("Trong kho", in_stock)
    m4.metric("Đang bảo trì", maintenance)
    m5.metric("Hỏng", broken)
    m6.metric("Tổng giá trị (VNĐ)", f"{total_asset_value:,.0f}")
    
    st.markdown("---")

    if df_devices.empty:
        st.info("Hệ thống hiện chưa có dữ liệu thiết bị.")
        return

    # --- KHỐI 2: BẢNG TỔNG HỢP & SỰ CỐ ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("📊 **Thống kê theo Danh mục**")
        cat_counts = df_devices['Danh mục'].value_counts().reset_index()
        cat_counts.columns = ['Danh mục thiết bị', 'Số lượng']
        st.dataframe(cat_counts, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("🛠️ **Phiếu sửa chữa cần xử lý**")
        pending_tickets = [r for r in maintenance_records if r['status'] in ['Đang xác nhận', 'Đang xử lý']]
        
        if pending_tickets:
            df_tickets = pd.DataFrame(pending_tickets)
            df_tickets['Thiết bị'] = df_tickets['device_code']
            df_tickets['Ngày tạo'] = pd.to_datetime(df_tickets['created_at']).dt.strftime('%d/%m')
            
            display_tickets = df_tickets[['Thiết bị', 'title', 'priority', 'status', 'Ngày tạo']]
            display_tickets.columns = ['Mã TB', 'Sự cố', 'Ưu tiên', 'Trạng thái', 'Ngày']
            
            st.dataframe(display_tickets, use_container_width=True, hide_index=True)
        else:
            st.success("Không có phiếu sửa chữa nào đang tồn đọng.")

    st.markdown("---")

    # --- KHỐI 3: TRA CỨU CHI TIẾT THEO PHÒNG BAN ---
    st.subheader("🔍 Tra cứu chi tiết phân bổ")
    departments = sorted(df_devices['Phòng ban'].unique())
    
    selected_dept_view = st.selectbox("Chọn phòng ban để xem danh sách thiết bị:", options=departments)
    
    dept_df = df_devices[df_devices['Phòng ban'] == selected_dept_view]
    display_dept_df = dept_df[['Mã TB', 'Tên thiết bị', 'Danh mục', 'Người dùng', 'Loại cấp phát', 'Trạng thái']]
    
    st.markdown(f"**Tổng số:** `{len(dept_df)}` thiết bị")
    st.dataframe(display_dept_df, use_container_width=True, hide_index=True)

def main():
    if auth.check_session():
        main_app()
    else:
        show_login_form()

if __name__ == "__main__":
    main()