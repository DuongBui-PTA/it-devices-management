import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Cấu hình trang
st.set_page_config(page_title="Dashboard - Quản lý Thiết bị IT", page_icon="📊", layout="wide")

# Khởi tạo session state
if 'devices' not in st.session_state:
    st.session_state.devices = [
        {
            'id': 1, 'name': 'Dell Latitude 5520', 'type': 'Laptop', 'serial': 'DL5520-001',
            'user': 'Nguyễn Văn A', 'department': 'IT', 'purchase_date': '2023-01-15',
            'warranty_date': '2026-01-15', 'status': 'Đang sử dụng',
            'notes': 'Cấu hình: i7, 16GB RAM, 512GB SSD'
        },
        {
            'id': 2, 'name': 'HP EliteBook 840', 'type': 'Laptop', 'serial': 'HP840-002',
            'user': 'Trần Thị B', 'department': 'Kế toán', 'purchase_date': '2023-03-20',
            'warranty_date': '2026-03-20', 'status': 'Đang sử dụng',
            'notes': 'Cấu hình: i5, 8GB RAM, 256GB SSD'
        },
        {
            'id': 3, 'name': 'iPhone 13 Pro', 'type': 'Điện thoại', 'serial': 'IP13P-003',
            'user': 'Lê Văn C', 'department': 'Sales', 'purchase_date': '2022-11-10',
            'warranty_date': '2023-11-10', 'status': 'Bảo trì', 'notes': 'Màu xanh, 256GB'
        },
        {
            'id': 4, 'name': 'MacBook Pro 14', 'type': 'Laptop', 'serial': 'MBP14-004',
            'user': 'Phạm Thị D', 'department': 'Marketing', 'purchase_date': '2023-05-10',
            'warranty_date': '2026-05-10', 'status': 'Đang sử dụng',
            'notes': 'M1 Pro, 16GB RAM, 512GB SSD'
        },
        {
            'id': 5, 'name': 'Samsung Galaxy S23', 'type': 'Điện thoại', 'serial': 'SGS23-005',
            'user': 'Hoàng Văn E', 'department': 'Sales', 'purchase_date': '2023-07-20',
            'warranty_date': '2024-07-20', 'status': 'Đang sử dụng', 'notes': '256GB, màu đen'
        },
        {
            'id': 6, 'name': 'Dell UltraSharp 27', 'type': 'Màn hình', 'serial': 'DUS27-006',
            'user': 'Nguyễn Văn A', 'department': 'IT', 'purchase_date': '2023-02-15',
            'warranty_date': '2026-02-15', 'status': 'Đang sử dụng', 'notes': '4K, 27 inch'
        },
        {
            'id': 7, 'name': 'HP LaserJet Pro', 'type': 'Máy in', 'serial': 'HPLJ-007',
            'user': '', 'department': 'Hành chính', 'purchase_date': '2022-08-10',
            'warranty_date': '2025-08-10', 'status': 'Hỏng', 'notes': 'Cần thay cartridge'
        },
        {
            'id': 8, 'name': 'Cisco Router 2900', 'type': 'Router', 'serial': 'CR2900-008',
            'user': '', 'department': 'IT', 'purchase_date': '2022-03-15',
            'warranty_date': '2025-03-15', 'status': 'Đang sử dụng',
            'notes': 'Router chính của văn phòng'
        }
    ]

st.title("📊 Dashboard - Thống Kê Thiết Bị IT")
st.markdown("---")

# Thống kê tổng quan
total_devices = len(st.session_state.devices)
in_use = len([d for d in st.session_state.devices if d['status'] == 'Đang sử dụng'])
not_used = len([d for d in st.session_state.devices if d['status'] == 'Chưa sử dụng'])
maintenance = len([d for d in st.session_state.devices if d['status'] == 'Bảo trì'])
broken = len([d for d in st.session_state.devices if d['status'] == 'Hỏng'])
retired = len([d for d in st.session_state.devices if d['status'] == 'Thanh lý'])

# Các thẻ thống kê
st.subheader("📈 Tổng Quan")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Tổng Thiết Bị", total_devices)
with col2:
    st.metric("Đang Sử Dụng", in_use, delta=f"{round(in_use/total_devices*100, 1)}%" if total_devices > 0 else "0%")
with col3:
    st.metric("Bảo Trì", maintenance)
with col4:
    st.metric("Hỏng", broken)
with col5:
    st.metric("Chưa Dùng", not_used)

st.markdown("---")

# Biểu đồ
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("📊 Phân Bố Theo Trạng Thái")
    status_data = pd.DataFrame([
        {'Trạng thái': 'Đang sử dụng', 'Số lượng': in_use},
        {'Trạng thái': 'Chưa sử dụng', 'Số lượng': not_used},
        {'Trạng thái': 'Bảo trì', 'Số lượng': maintenance},
        {'Trạng thái': 'Hỏng', 'Số lượng': broken},
        {'Trạng thái': 'Thanh lý', 'Số lượng': retired}
    ])
    
    fig_status = px.pie(status_data, values='Số lượng', names='Trạng thái',
                       color='Trạng thái',
                       color_discrete_map={
                           'Đang sử dụng': '#28a745',
                           'Chưa sử dụng': '#17a2b8',
                           'Bảo trì': '#ffc107',
                           'Hỏng': '#dc3545',
                           'Thanh lý': '#6c757d'
                       })
    fig_status.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_status, width='stretch')

with col_chart2:
    st.subheader("🏢 Phân Bố Theo Phòng Ban")
    dept_count = {}
    for device in st.session_state.devices:
        dept = device['department']
        dept_count[dept] = dept_count.get(dept, 0) + 1
    
    dept_data = pd.DataFrame([
        {'Phòng ban': k, 'Số lượng': v} for k, v in dept_count.items()
    ])
    
    fig_dept = px.bar(dept_data, x='Phòng ban', y='Số lượng',
                     color='Số lượng',
                     color_continuous_scale='Blues')
    fig_dept.update_layout(showlegend=False)
    st.plotly_chart(fig_dept, width='stretch')

# Biểu đồ loại thiết bị
st.markdown("---")
col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.subheader("💻 Phân Bố Theo Loại Thiết Bị")
    type_count = {}
    for device in st.session_state.devices:
        device_type = device['type']
        type_count[device_type] = type_count.get(device_type, 0) + 1
    
    type_data = pd.DataFrame([
        {'Loại': k, 'Số lượng': v} for k, v in type_count.items()
    ]).sort_values('Số lượng', ascending=True)
    
    fig_type = px.bar(type_data, x='Số lượng', y='Loại',
                     orientation='h',
                     color='Số lượng',
                     color_continuous_scale='Greens')
    fig_type.update_layout(showlegend=False)
    st.plotly_chart(fig_type, width='stretch')

with col_chart4:
    st.subheader("📅 Bảo Hành Sắp Hết")
    today = datetime.now()
    expiring_soon = []
    
    for device in st.session_state.devices:
        warranty_date = datetime.strptime(device['warranty_date'], '%Y-%m-%d')
        days_left = (warranty_date - today).days
        if 0 <= days_left <= 180:
            expiring_soon.append({
                'Thiết bị': device['name'],
                'Ngày hết BH': device['warranty_date'],
                'Còn lại (ngày)': days_left
            })
    
    if expiring_soon:
        df_expiring = pd.DataFrame(expiring_soon).sort_values('Còn lại (ngày)')
        st.dataframe(df_expiring, width='stretch', hide_index=True)
    else:
        st.info("✅ Không có thiết bị nào sắp hết bảo hành trong 6 tháng tới")

# Bảng thiết bị theo phòng ban
st.markdown("---")
st.subheader("📋 Chi Tiết Theo Phòng Ban")

dept_details = {}
for device in st.session_state.devices:
    dept = device['department']
    if dept not in dept_details:
        dept_details[dept] = []
    dept_details[dept].append(device)

for dept, devices in dept_details.items():
    with st.expander(f"🏢 {dept} ({len(devices)} thiết bị)"):
        dept_df = pd.DataFrame(devices)
        dept_df = dept_df[['name', 'type', 'user', 'status']]
        dept_df.columns = ['Tên thiết bị', 'Loại', 'Người dùng', 'Trạng thái']
        st.dataframe(dept_df, width='stretch', hide_index=True)