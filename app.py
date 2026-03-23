import streamlit as st
from utils.auth import AuthManager
import logging
from datetime import datetime
import pandas as pd
from services.device_services import get_devices
from services.device_allocation_services import get_allocations
from services.employee_services import get_employees

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Login",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

auth = AuthManager()

def show_login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Login")
            
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                help="Use your company username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button(
                    "Login",
                    type="primary",
                    width='stretch'
                )
            with col2:
                st.form_submit_button(
                    "Forgot Password?",
                    width='stretch',
                    disabled=True,
                    help="Contact IT support for password reset"
                )
            
            if submit:
                if username and password:
                    success, result = auth.authenticate(username, password)
                    
                    if success:
                        auth.login(result)
                        st.rerun()
                    else:
                        error_msg = result.get("error", "Authentication failed")
                        st.error(f"❌ {error_msg}")
                else:
                    st.warning("⚠️ Please enter both username and password")

def main_app():
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown(f"### 📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
    with col2:
        st.markdown(f"### 👤 Welcome, **{auth.get_user_display_name()}**")
    
    with col3:
        if st.button("🚪 Logout", width='stretch'):
            auth.logout()
            st.rerun()

    st.markdown("---")

    all_devices = get_devices()
    
    total_devices = len(all_devices)
    in_use = sum(1 for d in all_devices if d['status'] == 'Đang sử dụng')
    in_stock = sum(1 for d in all_devices if d['status'] == 'Chưa sử dụng')
    maintenance = sum(1 for d in all_devices if d['status'] == 'Bảo trì')
    broken = sum(1 for d in all_devices if d['status'] == 'Hỏng')
    liquidated = sum(1 for d in all_devices if d['status'] == 'Thanh lý')

    st.subheader("📈 Overview")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Total Devices", total_devices)
    with col2:
        st.metric("In Use", in_use, delta=f"{round(in_use/total_devices*100, 1)}%" if total_devices > 0 else "0%")
    with col3:
        st.metric("Maintenance", maintenance)
    with col4:
        st.metric("Broken", broken)
    with col5:
        st.metric("In Stock", in_stock)
    with col6:
        st.metric("Liquidated", liquidated)
    
    st.markdown("---")
    st.subheader("🏢 Department Details")

    active_allocations = get_allocations({"status": "Đang cấp phát"})
    alloc_map = {a['device_id']: a['employee_id'] for a in active_allocations}
    
    employees = get_employees()
    emp_map = {e['id']: {'name': e['full_name'], 'dept': e['department_name'] or 'Chưa phân bổ'} for e in employees}

    enriched_devices = []
    for d in all_devices:
        emp_id = alloc_map.get(d['id'])
        if emp_id and emp_id in emp_map:
            user_name = emp_map[emp_id]['name']
            dept_name = emp_map[emp_id]['dept']
        else:
            user_name = "-"
            # Thiết bị chưa phân bổ cho nhân viên sẽ thuộc về Kho
            dept_name = "Kho IT (Chưa phân bổ)"
            
        enriched_devices.append({
            'Device Name': d['device_name'],
            'Device Type': d.get('category_name', 'N/A'),
            'User': user_name,
            'Status': d['status'],
            'Department': dept_name
        })

    df = pd.DataFrame(enriched_devices)
    
    if not df.empty:
        departments = df['Department'].unique()
        for dept in sorted(departments):
            dept_df = df[df['Department'] == dept]
            with st.expander(f"{dept} ({len(dept_df)} devices)"):
                display_df = dept_df[['Device Name', 'Device Type', 'User', 'Status']]
                st.dataframe(display_df, width='stretch', hide_index=True)
    else:
        st.info("Hệ thống hiện chưa có dữ liệu thiết bị.")

def main():
    if auth.check_session():
        main_app()
    else:
        show_login_form()

if __name__ == "__main__":
    main()