# services/device_services.py

from utils.db import get_db_engine
from sqlalchemy import text, exc
import logging
import streamlit as st
from typing import Dict, Any, List, Optional
from utils.s3_utils import S3Manager
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    s3_manager = S3Manager()
except Exception as e:
    st.error("Unable to connect to file storage service. Please contact support.")
    logger.error(f"S3 initialization failed: {e}")
    st.stop()

def get_devices(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        filters = filters or {}

        query = text("""
            SELECT
                d.id,
                d.device_code,
                d.device_name,
                d.category_id,
                c.category_name,
                d.manufacturer_id,
                COALESCE(m.english_name, m.local_name) AS manufacturer_name,
                d.supplier_id,
                COALESCE(s.english_name, s.local_name) AS supplier_name,
                d.purchased_by_employee_id,
                d.serial_number,
                d.purchase_date,
                d.price,
                d.warranty_date,
                d.system_summary,
                d.status,
                d.location,
                d.notes,
                d.image_url,
                d.image_url_2,
                d.image_url_3,
                d.invoice_url
            FROM devices d
            LEFT JOIN device_categories c ON d.category_id = c.id
            LEFT JOIN companies m ON d.manufacturer_id = m.id AND m.delete_flag = b'0'
            LEFT JOIN companies s ON d.supplier_id = s.id AND s.delete_flag = b'0'
            WHERE 1=1
              AND (:status IS NULL OR d.status = :status)
              AND (:category_id IS NULL OR d.category_id = :category_id)
              AND (:q IS NULL OR
                   LOWER(d.device_code) LIKE :q OR
                   LOWER(d.device_name) LIKE :q OR
                   LOWER(d.serial_number) LIKE :q)
            ORDER BY d.device_name
        """)

        params = {
            "status": filters.get("status"),
            "category_id": filters.get("category_id"),
            "q": f"%{filters['q'].lower()}%" if filters.get("q") else None
        }

        with engine.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [dict(row._mapping) for row in rows]

    except Exception as e:
        logger.error(e)
        st.error("Không thể tải danh sách thiết bị.")
        return []

def get_device_by_id(device_id: int) -> Optional[Dict[str, Any]]:
    try:
        engine = get_db_engine()

        query = text("""
            SELECT
                d.id,
                d.device_code,
                d.device_name,
                d.category_id,
                c.category_name,
                d.manufacturer_id,
                COALESCE(m.english_name, m.local_name) AS manufacturer_name,
                d.supplier_id,
                COALESCE(s.english_name, s.local_name) AS supplier_name,
                d.purchased_by_employee_id,
                d.serial_number,
                d.purchase_date,
                d.price,
                d.warranty_date,
                d.system_summary,
                d.status,
                d.location,
                d.notes,
                d.image_url,
                d.image_url_2,
                d.image_url_3,
                d.invoice_url
            FROM devices d
            LEFT JOIN device_categories c ON d.category_id = c.id
            LEFT JOIN companies m ON d.manufacturer_id = m.id AND m.delete_flag = b'0'
            LEFT JOIN companies s ON d.supplier_id = s.id AND s.delete_flag = b'0'
            WHERE d.id = :id
        """)

        with engine.connect() as conn:
            row = conn.execute(query, {"id": device_id}).fetchone()

        return dict(row._mapping) if row else None

    except Exception as e:
        logger.error(e)
        st.error("Không thể tải thông tin thiết bị.")
        return None

def create_device(data: Dict[str, Any]) -> bool:
    try:
        # Lấy timestamp để tránh trùng lặp tên file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # --- 1. XỬ LÝ UPLOAD 3 ẢNH THIẾT BỊ ---
        image_urls = [None, None, None]
        for i in range(1, 4):
            img_file = data.get(f'img_file_{i}')
            if img_file:
                safe_filename = img_file.name.replace(' ', '_')
                img_key = f"{s3_manager.app_prefix}/devices/images/{timestamp}_{i}_{safe_filename}"
                
                # Đọc bytes từ Streamlit UploadedFile và truyền vào S3Manager
                success, result = s3_manager.upload_file(
                    file_content=img_file.read(),
                    key=img_key,
                    content_type=img_file.type
                )
                if success:
                    image_urls[i-1] = img_key  # Lưu S3 key vào list
                else:
                    logger.error(f"Lỗi upload ảnh thiết bị {i}: {result}")

        # --- 2. XỬ LÝ UPLOAD HÓA ĐƠN ---
        invoice_url = None
        inv_file = data.get('inv_file')
        if inv_file:
            safe_filename = inv_file.name.replace(' ', '_')
            inv_key = f"{s3_manager.app_prefix}/devices/invoices/{timestamp}_{safe_filename}"
            
            success, result = s3_manager.upload_file(
                file_content=inv_file.read(),
                key=inv_key,
                content_type=inv_file.type
            )
            if success:
                invoice_url = inv_key  # Lưu S3 key
            else:
                logger.error(f"Lỗi upload hóa đơn: {result}")

        engine = get_db_engine()

        # Xử lý Serial
        serial = data.get("serial_number", "").strip()
        final_serial = serial if serial else None

        # --- 3. CÂU LỆNH SQL INSERT ---
        query = text("""
            INSERT INTO devices (
                device_code, device_name, category_id, manufacturer_id, supplier_id,
                purchased_by_employee_id, serial_number, purchase_date, price,
                warranty_date, system_summary, status, location, notes,
                image_url, image_url_2, image_url_3, invoice_url
            )
            VALUES (
                :device_code, :device_name, :category_id, :manufacturer_id, :supplier_id,
                :purchased_by_employee_id, :serial_number, :purchase_date, :price,
                :warranty_date, :system_summary, :status, :location, :notes,
                :image_url, :image_url_2, :image_url_3, :invoice_url
            )
        """)
        
        # Loại bỏ các object File của Streamlit ra khỏi dictionary trước khi truyền vào SQLAlchemy
        clean_keys = ['img_file_1', 'img_file_2', 'img_file_3', 'inv_file']
        clean_data = {k: v for k, v in data.items() if k not in clean_keys}
        
        # Gắn các S3 key vừa tạo vào dictionary để map với placeholder trong SQL
        clean_data['serial_number'] = final_serial
        clean_data['image_url'] = image_urls[0]
        clean_data['image_url_2'] = image_urls[1]
        clean_data['image_url_3'] = image_urls[2]
        clean_data['invoice_url'] = invoice_url

        with engine.begin() as conn:
            conn.execute(query, clean_data)

        return True

    except exc.IntegrityError:
        st.error("⚠️ Mã thiết bị hoặc Serial Number đã tồn tại.")
        return False
    except Exception as e:
        logger.error(e)
        st.error("Không thể thêm thiết bị.")
        return False

def update_device(device_id: int, data: Dict[str, Any]) -> bool:
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # --- XỬ LÝ 3 ẢNH THIẾT BỊ ---
        image_urls = [None, None, None]
        for i in range(1, 4):
            img_file = data.get(f'img_file_{i}')
            if img_file:
                safe_filename = img_file.name.replace(' ', '_')
                img_key = f"{s3_manager.app_prefix}/devices/images/{timestamp}_{i}_{safe_filename}"
                success, result = s3_manager.upload_file(img_file.read(), img_key, img_file.type)
                if success:
                    image_urls[i-1] = img_key

        # --- XỬ LÝ HÓA ĐƠN ---
        invoice_url = None
        inv_file = data.get('inv_file')
        if inv_file:
            safe_filename = inv_file.name.replace(' ', '_')
            inv_key = f"{s3_manager.app_prefix}/devices/invoices/{timestamp}_{safe_filename}"
            success, result = s3_manager.upload_file(inv_file.read(), inv_key, inv_file.type)
            if success:
                invoice_url = inv_key

        engine = get_db_engine()
        
        # Xử lý Serial
        serial = data.get("serial_number", "").strip()
        final_serial = serial if serial else None
        
        query = text("""
            UPDATE devices
            SET
                device_code = :device_code,
                device_name = :device_name,
                category_id = :category_id,
                manufacturer_id = :manufacturer_id,
                supplier_id = :supplier_id,
                purchased_by_employee_id = :purchased_by_employee_id,
                serial_number = :serial_number,
                purchase_date = :purchase_date,
                price = :price,
                warranty_date = :warranty_date,
                system_summary = :system_summary,
                status = :status,
                location = :location,
                notes = :notes,
                image_url = COALESCE(:image_url, image_url),
                image_url_2 = COALESCE(:image_url_2, image_url_2),
                image_url_3 = COALESCE(:image_url_3, image_url_3),
                invoice_url = COALESCE(:invoice_url, invoice_url)
            WHERE id = :id
        """)

        # Loại bỏ các file object để tránh lỗi SQL
        clean_keys = ['img_file_1', 'img_file_2', 'img_file_3', 'inv_file']
        clean_data = {k: v for k, v in data.items() if k not in clean_keys}
        
        # --- GÁN LẠI DỮ LIỆU CHUẨN ĐỂ CHẠY SQL ---
        clean_data['id'] = device_id
        clean_data['serial_number'] = final_serial
        clean_data['image_url'] = image_urls[0]
        clean_data['image_url_2'] = image_urls[1]
        clean_data['image_url_3'] = image_urls[2]
        clean_data['invoice_url'] = invoice_url

        with engine.begin() as conn:
            conn.execute(query, clean_data)

        return True

    except Exception as e:
        logger.error(e)
        st.error("Không thể cập nhật thiết bị.")
        return False

def delete_device(device_id: int) -> bool:
    try:
        engine = get_db_engine()

        check = text("""
            SELECT status
            FROM devices
            WHERE id = :id
        """)

        delete = text("""
            DELETE FROM devices
            WHERE id = :id
        """)

        allowed_status = ("Chưa sử dụng", "Hỏng", "Thanh lý", "Thất lạc")

        with engine.begin() as conn:
            status = conn.execute(check, {"id": device_id}).scalar()
            if status not in allowed_status:
                st.warning("⚠️ Không thể xóa thiết bị ở trạng thái hiện tại.")
                return False

            conn.execute(delete, {"id": device_id})

        return True

    except Exception as e:
        logger.error(e)
        st.error("Không thể xóa thiết bị.")
        return False