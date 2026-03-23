# services/device_allocation_services.py

from utils.db import get_db_engine
from sqlalchemy import text, exc
import logging
import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import date

logger = logging.getLogger(__name__)

def get_allocations(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        filters = filters or {}

        query = text("""
            SELECT 
                da.id,
                da.device_id,
                d.device_code,
                d.device_name,
                da.employee_id,
                CONCAT(IFNULL(e.last_name, ''), ' ', IFNULL(e.first_name, '')) AS employee_name,
                e.email AS employee_email,
                da.allocated_by_employee_id,
                CONCAT(IFNULL(a.last_name, ''), ' ', IFNULL(a.first_name, '')) AS allocated_by_name,
                da.allocation_date,
                da.return_date,
                da.status,
                da.notes
            FROM device_allocations da
            JOIN devices d ON da.device_id = d.id
            -- ĐỔI JOIN THÀNH LEFT JOIN Ở DÒNG DƯỚI NÀY:
            LEFT JOIN employees e ON da.employee_id = e.id AND e.delete_flag = b'0'
            LEFT JOIN employees a ON da.allocated_by_employee_id = a.id
            WHERE 1=1
              AND (:status IS NULL OR da.status = :status)
              AND (:device_id IS NULL OR da.device_id = :device_id)
              AND (:employee_id IS NULL OR da.employee_id = :employee_id)
            ORDER BY da.allocation_date DESC, da.id DESC
        """)

        params = {
            "status": filters.get("status"),
            "device_id": filters.get("device_id"),
            "employee_id": filters.get("employee_id")
        }

        with engine.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [dict(row._mapping) for row in rows]

    except Exception as e:
        logger.error(f"Error fetching allocations: {e}")
        st.error("Không thể tải danh sách cấp phát thiết bị.")
        return []

def allocate_device(data: Dict[str, Any]) -> bool:
    try:
        engine = get_db_engine()

        insert_alloc = text("""
            INSERT INTO device_allocations (
                device_id, 
                employee_id, 
                allocated_by_employee_id, 
                allocation_date, 
                status, 
                notes
            )
            VALUES (
                :device_id, 
                :employee_id, 
                :allocated_by_employee_id, 
                :allocation_date, 
                'Đang cấp phát', 
                :notes
            )
        """)

        update_device = text("""
            UPDATE devices
            SET status = 'Đang sử dụng'
            WHERE id = :device_id AND status = 'Chưa sử dụng'
        """)

        with engine.begin() as conn:
            result = conn.execute(update_device, {"device_id": data["device_id"]})
            if result.rowcount == 0:
                st.warning("⚠️ Thiết bị này không ở trạng thái 'Chưa sử dụng' hoặc không tồn tại.")
                return False

            conn.execute(insert_alloc, {
                "device_id": data["device_id"],
                "employee_id": data["employee_id"],
                "allocated_by_employee_id": data.get("allocated_by_employee_id"),
                "allocation_date": data.get("allocation_date", date.today()),
                "notes": data.get("notes", "")
            })

        return True

    except Exception as e:
        logger.error(f"Error allocating device: {e}")
        st.error("Không thể thực hiện cấp phát thiết bị.")
        return False

def return_device(allocation_id: int, device_id: int, return_date: date, notes: str = "") -> bool:
    try:
        engine = get_db_engine()

        update_alloc = text("""
            UPDATE device_allocations
            SET 
                return_date = :return_date,
                status = 'Đã thu hồi',
                notes = CONCAT(IFNULL(notes, ''), 'Ghi chú thu hồi: ', :notes)
            WHERE id = :allocation_id AND status = 'Đang cấp phát'
        """)

        update_device = text("""
            UPDATE devices
            SET status = 'Chưa sử dụng'
            WHERE id = :device_id
        """)

        with engine.begin() as conn:
            result = conn.execute(update_alloc, {
                "allocation_id": allocation_id,
                "return_date": return_date,
                "notes": notes
            })
            
            if result.rowcount == 0:
                st.warning("⚠️ Bản ghi cấp phát này đã được thu hồi hoặc không tồn tại.")
                return False

            conn.execute(update_device, {"device_id": device_id})

        return True

    except Exception as e:
        logger.error(f"Error returning device: {e}")
        st.error("Không thể thực hiện thu hồi thiết bị.")
        return False

def update_allocation_notes(allocation_id: int, notes: str) -> bool:
    try:
        engine = get_db_engine()
        query = text("""
            UPDATE device_allocations
            SET notes = :notes
            WHERE id = :id
        """)

        with engine.begin() as conn:
            conn.execute(query, {"notes": notes, "id": allocation_id})

        return True
    except Exception as e:
        logger.error(f"Error updating allocation note: {e}")
        st.error("Không thể cập nhật ghi chú.")
        return False