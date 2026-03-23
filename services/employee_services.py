# services/employee_services.py

from utils.db import get_db_engine
from sqlalchemy import text, exc
import logging
import streamlit as st
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def get_employees(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        filters = filters or {}

        query = text("""
            SELECT 
                e.id,
                e.first_name,
                e.last_name,
                CONCAT(IFNULL(e.last_name, ''), ' ', IFNULL(e.first_name, '')) AS full_name,
                e.email,
                e.phone,
                e.status,
                e.department_id,
                d.name AS department_name,
                e.position_id,
                p.name AS position_name,
                e.company_id,
                COALESCE(c.english_name, c.local_name) AS company_name
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id AND d.delete_flag = b'0'
            LEFT JOIN positions p ON e.position_id = p.id AND p.delete_flag = b'0'
            LEFT JOIN companies c ON e.company_id = c.id AND c.delete_flag = b'0'
            -- Đổi điều kiện delete_flag của employees sang b'0'
            WHERE e.delete_flag = b'0'
              AND (:status IS NULL OR e.status = :status)
              AND (:department_id IS NULL OR e.department_id = :department_id)
              AND (:q IS NULL OR 
                   LOWER(e.first_name) LIKE :q OR 
                   LOWER(e.last_name) LIKE :q OR 
                   LOWER(e.email) LIKE :q)
            ORDER BY e.first_name
        """)

        params = {
            "status": filters.get("status"),
            "department_id": filters.get("department_id"),
            "q": f"%{filters['q'].lower()}%" if filters.get("q") else None
        }

        with engine.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [dict(row._mapping) for row in rows]

    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        st.error("Không thể tải danh sách nhân viên.")
        return []

def get_employee_by_id(employee_id: int) -> Optional[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        query = text("""
            SELECT 
                e.*,
                d.name AS department_name,
                p.name AS position_name,
                COALESCE(c.english_name, c.local_name) AS company_name
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id AND d.delete_flag = b'0'
            LEFT JOIN positions p ON e.position_id = p.id AND p.delete_flag = b'0'
            LEFT JOIN companies c ON e.company_id = c.id AND c.delete_flag = b'0'
            -- Đổi điều kiện delete_flag sang b'0'
            WHERE e.id = :id AND e.delete_flag = b'0'
        """)

        with engine.connect() as conn:
            row = conn.execute(query, {"id": employee_id}).fetchone()

        return dict(row._mapping) if row else None

    except Exception as e:
        logger.error(f"Error fetching employee detail: {e}")
        st.error("Không thể tải thông tin chi tiết nhân viên.")
        return None

def get_departments() -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        query = text("""
            SELECT id, code, name, description
            FROM departments
            WHERE delete_flag = b'0'
            ORDER BY name
        """)
        
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        return [dict(row._mapping) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching departments: {e}")
        return []

def get_positions() -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        query = text("""
            SELECT id, code, name
            FROM positions
            WHERE delete_flag = b'0'
            ORDER BY name
        """)
        
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        return [dict(row._mapping) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return []

def get_companies() -> List[Dict[str, Any]]:
    try:
        engine = get_db_engine()
        query = text("""
            SELECT 
                id, 
                company_code, 
                english_name, 
                local_name,
                COALESCE(english_name, local_name) AS company_name
            FROM companies
            WHERE delete_flag = b'0'
            ORDER BY COALESCE(english_name, local_name)
        """)
        
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        return [dict(row._mapping) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        return []