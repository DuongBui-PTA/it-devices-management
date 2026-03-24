# services/device_category_services.py

from utils.db import get_db_engine
from sqlalchemy import text, exc
import logging
import streamlit as st
from typing import Dict, Any, List, Optional
from utils.s3_utils import S3Manager

logger = logging.getLogger(__name__)

try:
    s3_manager = S3Manager()
except Exception as e:
    st.error("Unable to connect to file storage service. Please contact support.")
    logger.error(f"S3 initialization failed: {e}")
    st.stop()

def get_device_categories(include_deleted: bool = False) -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()

        # Ép kiểu delete_flag sang số nguyên để Python hiểu đúng và sửa điều kiện thành b'0'
        query = text("""
            SELECT
                id,
                category_code,
                category_name,
                allocation_type,
                technical_function,
                CAST(delete_flag AS UNSIGNED) AS is_deleted,
                notes
            FROM device_categories
            WHERE (:include_deleted = 1 OR delete_flag = b'0')
            ORDER BY id
        """)

        with engine.connect() as conn:
            results = conn.execute(query, {
                "include_deleted": 1 if include_deleted else 0
            }).fetchall()

        return [
            {
                "category_id": r.id,
                "category_code": r.category_code,
                "category_name": r.category_name,
                "allocation_type": r.allocation_type,
                "technical_function": r.technical_function,
                "delete_flag": bool(r.is_deleted),
                "notes": r.notes
            }
            for r in results
        ]
    except Exception as e:
        logger.error(e)
        st.error("Không thể tải danh mục thiết bị.")
        return []

def create_device_category(data: Dict[str, Any]) -> bool:
    try:
        engine = get_db_engine()

        query = text("""
            INSERT INTO device_categories (category_code, category_name, allocation_type, technical_function, notes)
            VALUES (:code, :name, :allocation_type, :technical_function, :notes)
        """)

        with engine.begin() as conn:
            conn.execute(query, {
                "code": data["code"],
                "name": data["name"],
                "allocation_type": data.get("allocation_type", "Cá nhân"),
                "technical_function": data.get("technical_function", ""),
                "notes": data.get("note", "")
            })
        return True

    except exc.IntegrityError:
        st.error("⚠️ Mã loại thiết bị đã tồn tại.")
        return False
    except Exception as e:
        logger.error(e)
        st.error("Không thể thêm loại thiết bị.")
        return False

def update_device_category(category_id: int, data: Dict[str, Any]) -> bool:
    try:
        engine = get_db_engine()

        query = text("""
            UPDATE device_categories
            SET category_code = :code,
                category_name = :name,
                allocation_type = :allocation_type,
                technical_function = :technical_function,
                notes = :notes
            WHERE id = :id
        """)

        with engine.begin() as conn:
            conn.execute(query, {
                "id": category_id,
                "code": data["code"],
                "name": data["name"],
                "allocation_type": data.get("allocation_type", "Cá nhân"),
                "technical_function": data.get("technical_function", ""),
                "notes": data.get("note", "")
            })

        return True

    except exc.IntegrityError:
        st.error("⚠️ Mã hoặc tên loại thiết bị đã tồn tại.")
        return False
    except exc.SQLAlchemyError as e:
        logger.error(f"Update device category failed: {e}")
        st.error("Không thể cập nhật loại thiết bị.")
        return False

def delete_device_category(category_id: int) -> bool:
    try:
        engine = get_db_engine()

        check = text("""
            SELECT COUNT(*) FROM devices WHERE category_id = :id
        """)
        update = text("""
            UPDATE device_categories
            SET delete_flag = 1
            WHERE id = :id
        """)

        with engine.begin() as conn:
            used = conn.execute(check, {"id": category_id}).scalar()
            if used > 0:
                st.warning("⚠️ Không thể xóa vì loại thiết bị đang được sử dụng.")
                return False

            conn.execute(update, {"id": category_id})

        return True

    except Exception as e:
        logger.error(e)
        st.error("Không thể xóa loại thiết bị.")
        return False

def count_devices_group_by_category() -> dict[int, int]:
    try:
        engine = get_db_engine()

        query = text("""
            SELECT category_id, COUNT(*) AS total
            FROM devices
            WHERE category_id IS NOT NULL
            GROUP BY category_id
        """)

        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        return {row.category_id: row.total for row in rows}

    except Exception as e:
        logger.error(f"Count devices group by category failed: {e}")
        st.error("Không thể tải thống kê thiết bị theo loại.")
        return {}