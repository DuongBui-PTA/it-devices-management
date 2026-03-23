import streamlit as st
from datetime import datetime, date
from services.device_services import (
    get_devices,
    get_device_by_id,
    create_device,
    update_device,
    delete_device,
    allocate_device,
    return_device,
)
from services.device_category_services import get_device_categories
from utils.db import get_db_engine

# =========================
# Page config
# =========================
st.set_page_config(page_title="Quản lý Thiết bị IT", page_icon="📋", layout="wide")

# =========================
# Session state
# =========================
st.session_state.setdefault("show_form", False)
st.session_state.setdefault("form_mode", "add")          # add | edit
st.session_state.setdefault("selected_device_id", None)
st.session_state.setdefault("confirm_delete", None)
st.session_state.setdefault("show_detail", False)
st.session_state.setdefault("assign_target", None)

# =========================
# Helpers
# =========================
def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return date.today()

def reset_popups():
    st.session_state.confirm_delete = None
    st.session_state.assign_target = None
    st.session_state.show_detail = False

# =========================
# Load data
# =========================
categories = get_device_categories()
category_map = {c["category_id"]: c for c in categories}

# =========================
# UI
# =========================
st.title("💻 Quản Lý Thiết Bị IT")
st.markdown("---")

# =========================
# Filters
# =========================
st.subheader("🔍 Bộ lọc")

col1, col2 = st.columns(2)
with col1:
    filter_status = st.selectbox(
        "Trạng thái",
        ["Tất cả", "Chưa sử dụng", "Đang sử dụng", "Hỏng", "Bảo trì", "Thanh lý", "Thất lạc"]
    )
with col2:
    filter_category = st.selectbox(
        "Loại thiết bị",
        ["Tất cả"] + [c["category_name"] for c in categories]
    )

filters = {}
if filter_status != "Tất cả":
    filters["status"] = filter_status
if filter_category != "Tất cả":
    cid = next((c["category_id"] for c in categories if c["category_name"] == filter_category), None)
    filters["category_id"] = cid

devices = get_devices(filters)

# =========================
# Add button
# =========================
if st.button("➕ Thêm thiết bị", type="primary"):
    st.session_state.show_form = True
    st.session_state.form_mode = "add"
    st.session_state.selected_device_id = None
    reset_popups()
    st.rerun()

# =========================
# Device Form
# =========================
def show_device_form(mode="add", device=None):
    st.subheader("➕ Thêm thiết bị" if mode == "add" else "✏️ Chỉnh sửa thiết bị")

    category_names = [c["category_name"] for c in categories]
    status_options = ["Chưa sử dụng", "Đang sử dụng", "Hỏng", "Bảo trì", "Thanh lý", "Thất lạc"]

    with st.form("device_form"):
        col1, col2 = st.columns(2)

        with col1:
            device_name = st.text_input("Tên thiết bị *", value=device.get("device_name") if device else "")
            serial = st.text_input("Serial *", value=device.get("serial_number") if device else "")
            category = st.selectbox(
                "Loại thiết bị *",
                category_names,
                index=category_names.index(category_map[device["category_id"]]["category_name"]) if device else 0
            )

        with col2:
            purchase_date = st.date_input(
                "Ngày mua",
                value=parse_date(device["purchase_date"]) if device else date.today()
            )
            warranty_date = st.date_input(
                "Ngày hết bảo hành",
                value=parse_date(device["warranty_date"]) if device else date.today()
            )

        if mode == "add":
            st.selectbox("Trạng thái", status_options, index=0, disabled=True)
            status = "Chưa sử dụng"
        else:
            status = st.selectbox(
                "Trạng thái",
                status_options,
                index=status_options.index(device["status"])
            )

        notes = st.text_area("Ghi chú", value=device.get("notes") if device else "")

        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("💾 Lưu", type="primary", width='stretch')
        cancelled = c2.form_submit_button("❌ Hủy", width='stretch')

        if submitted:
            if not device_name or not serial:
                st.error("⚠️ Vui lòng nhập đầy đủ trường bắt buộc.")
                st.stop()

            category_id = next(c["category_id"] for c in categories if c["category_name"] == category)

            payload = {
                "device_code": serial,
                "device_name": device_name,
                "category_id": category_id,
                "serial_number": serial,
                "purchase_date": purchase_date,
                "warranty_date": warranty_date,
                "status": status,
                "notes": notes,
            }

            ok = (
                create_device(payload)
                if mode == "add"
                else update_device(device["id"], payload)
            )

            if ok:
                st.success("✅ Lưu thiết bị thành công!")
                st.session_state.show_form = False
                st.rerun()

        if cancelled:
            st.session_state.show_form = False
            st.rerun()

# =========================
# Show form
# =========================
if st.session_state.show_form:
    device = None
    if st.session_state.form_mode == "edit":
        device = get_device_by_id(st.session_state.selected_device_id)
        if not device:
            st.error("Không tìm thấy thiết bị.")
            st.session_state.show_form = False
            st.rerun()
    show_device_form(st.session_state.form_mode, device)
    st.markdown("---")

# =========================
# Table
# =========================
st.subheader(f"📋 Danh sách thiết bị ({len(devices)} thiết bị)")

h1, h2, h3, h4, h5 = st.columns([1, 2.5, 1.5, 1.5, 2])
h1.markdown("**ID**")
h2.markdown("**Tên thiết bị**")
h3.markdown("**Loại**")
h4.markdown("**Trạng thái**")
h5.markdown("**Thao tác**")

for d in devices:
    c1, c2, c3, c4, c5 = st.columns([1, 2.5, 1.5, 1.5, 2])

    c1.write(d["id"])
    c2.write(d["device_name"])
    c3.write(category_map[d["category_id"]]["category_name"] if d["category_id"] else "—")
    c4.write(d["status"])

    a1, a2, a3, a4 = c5.columns(4)

    if a1.button("👁️", key=f"view_{d['id']}"):
        st.session_state.selected_device_id = d["id"]
        st.session_state.show_detail = True
        reset_popups()
        st.rerun()

    if a2.button("✏️", key=f"edit_{d['id']}"):
        st.session_state.selected_device_id = d["id"]
        st.session_state.form_mode = "edit"
        st.session_state.show_form = True
        reset_popups()
        st.rerun()

    if a3.button("👤", key=f"assign_{d['id']}"):
        st.session_state.assign_target = d["id"]
        reset_popups()
        st.rerun()

    if a4.button("🗑️", key=f"del_{d['id']}"):
        st.session_state.confirm_delete = d["id"]
        reset_popups()
        st.rerun()

# =========================
# Dialogs
# =========================
@st.dialog("🗑️ Xác nhận xóa", on_dismiss=reset_popups)
def confirm_delete_popup(device):
    st.warning("Bạn có chắc chắn muốn xóa thiết bị này?")
    st.write(f"**Tên:** {device['device_name']}")
    if st.button("🗑️ Xóa", type="primary"):
        if delete_device(device["id"]):
            st.success("✅ Đã xóa thiết bị.")
            st.session_state.confirm_delete = None
            st.rerun()
    if st.button("❌ Hủy"):
        st.session_state.confirm_delete = None
        st.rerun()

@st.dialog("👤 Cấp phát / Thu hồi", on_dismiss=reset_popups)
def assign_popup(device):
    st.write("Chức năng cấp phát / thu hồi xử lý qua DB.")
    if st.button("Thu hồi"):
        if return_device(device["id"]):
            st.success("✅ Thu hồi thành công.")
            st.session_state.assign_target = None
            st.rerun()

@st.dialog("📄 Chi tiết thiết bị", on_dismiss=reset_popups)
def detail_popup(device):
    st.write(f"**Tên:** {device['device_name']}")
    st.write(f"**Serial:** {device['serial_number']}")
    st.write(f"**Trạng thái:** {device['status']}")
    if st.button("Đóng"):
        st.session_state.show_detail = False
        st.rerun()

# =========================
# Open one dialog
# =========================
if st.session_state.confirm_delete:
    dev = get_device_by_id(st.session_state.confirm_delete)
    if dev:
        confirm_delete_popup(dev)
        st.stop()

if st.session_state.assign_target:
    dev = get_device_by_id(st.session_state.assign_target)
    if dev:
        assign_popup(dev)
        st.stop()

if st.session_state.show_detail and st.session_state.selected_device_id:
    dev = get_device_by_id(st.session_state.selected_device_id)
    if dev:
        detail_popup(dev)
        st.stop()
