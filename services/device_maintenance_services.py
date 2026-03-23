# services/device_maintenance_services.py

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import text
from utils.db import get_db_engine
from utils.s3_utils import S3Manager
import streamlit as st

logger = logging.getLogger(__name__)
try:
    s3_manager = S3Manager()
except Exception as e:
    logger.error(f"S3 initialization failed: {e}")

def upload_maintenance_images(files_content: List[bytes], original_filenames: List[str], maintenance_id: int) -> Tuple[bool, List[str], str]:
    """Upload danh sách ảnh sự cố thiết bị lên S3"""
    uploaded_keys = []
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for idx, (content, filename) in enumerate(zip(files_content, original_filenames)):
            safe_filename = filename.replace(' ', '_')
            # Cấu trúc key nghiệp vụ được định nghĩa tại đây
            img_key = f"{s3_manager.app_prefix}/devices/maintenance/{maintenance_id}/{timestamp}_{idx}_{safe_filename}"
            
            # Gọi tầng hạ tầng để thực hiện
            success, result = s3_manager.upload_file(content, img_key)
            if success:
                uploaded_keys.append(img_key)
            else:
                logger.warning(f"Lỗi upload 1 ảnh sự cố ({img_key}): {result}")

        if not uploaded_keys:
             return False, [], "Không có ảnh nào được upload thành công."
             
        logger.info(f"Đã upload thành công {len(uploaded_keys)} ảnh sự cố cho phiếu {maintenance_id}")
        return True, uploaded_keys, ""

    except Exception as e:
        logger.error(f"Error processing maintenance images for {maintenance_id}: {e}")
        return False, [], str(e)

def get_maintenance_records(filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách các phiếu bảo hành / sửa chữa"""
    try:
        engine = get_db_engine()
        
        query_str = """
            SELECT 
                m.id,
                m.device_id,
                d.device_code,
                d.device_name,
                m.device_allocations_id,
                m.employee_id,
                CONCAT(IFNULL(e.last_name, ''), ' ', IFNULL(e.first_name, '')) AS requester_name,
                m.title,
                m.priority,
                m.maintenance_type,
                m.problem_description,
                m.solution_description,
                m.status,
                m.cost,
                m.due_date,
                m.completion_date,
                m.notes,
                m.image_url_1,   -- BỔ SUNG
                m.image_url_2,   -- BỔ SUNG
                m.image_url_3,   -- BỔ SUNG
                m.created_at
            FROM device_maintenance_records m
            JOIN devices d ON m.device_id = d.id
            LEFT JOIN employees e ON m.employee_id = e.id
            WHERE 1=1
        """
        
        params = {}
        if filters:
            if filters.get("employee_id"):
                query_str += " AND m.employee_id = :employee_id"
                params["employee_id"] = filters["employee_id"]
            if filters.get("status"):
                query_str += " AND m.status = :status"
                params["status"] = filters["status"]
                
        query_str += " ORDER BY m.created_at DESC"
        
        with engine.connect() as conn:
            result = conn.execute(text(query_str), params).mappings().all()
            return [dict(row) for row in result]
            
    except Exception as e:
        logger.error(f"Error fetching maintenance records: {e}")
        return []

def create_maintenance_record(data: Dict[str, Any]) -> bool:
    """Tạo mới một phiếu yêu cầu sửa chữa (Bao gồm upload ảnh lên S3)"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_urls = [None, None, None]
        emp_id = data.get("employee_id", "unknown")
        
        for i in range(1, 4):
            img_file = data.get(f'img_file_{i}')
            if img_file:
                safe_filename = img_file.name.replace(' ', '_')
                img_key = f"{s3_manager.app_prefix}/devices/maintenance/user_{emp_id}/{timestamp}_{i}_{safe_filename}"
                
                success, result = s3_manager.upload_file(
                    file_content=img_file.read(),
                    key=img_key,
                    content_type=img_file.type
                )
                if success:
                    image_urls[i-1] = img_key
                else:
                    logger.error(f"Lỗi upload ảnh sự cố {i}: {result}")

        engine = get_db_engine()
        query = text("""
            INSERT INTO device_maintenance_records (
                device_id, device_allocations_id, employee_id, title, 
                priority, maintenance_type, problem_description, due_date, status,
                image_url_1, image_url_2, image_url_3
            ) VALUES (
                :device_id, :device_allocations_id, :employee_id, :title, 
                :priority, :maintenance_type, :problem_description, :due_date, :status,
                :image_url_1, :image_url_2, :image_url_3
            )
        """)
        
        clean_data = {
            "device_id": data["device_id"],
            "device_allocations_id": data.get("device_allocations_id"),
            "employee_id": data["employee_id"],
            "title": data["title"],
            "priority": data.get("priority"),
            "maintenance_type": data.get("maintenance_type"),
            "problem_description": data.get("problem_description"),
            "due_date": data.get("due_date"),
            "status": data.get("status", "Đang xác nhận"),
            "image_url_1": image_urls[0],
            "image_url_2": image_urls[1],
            "image_url_3": image_urls[2]
        }
        
        with engine.begin() as conn:
            conn.execute(query, clean_data)
            
        return True
        
    except Exception as e:
        logger.error(f"Error creating maintenance record: {e}")
        st.error("Không thể tạo phiếu yêu cầu. Vui lòng kiểm tra lại dữ liệu.")
        return False
    
def update_maintenance_record(record_id: int, data: Dict[str, Any]) -> bool:
    """Cập nhật tiến độ xử lý phiếu bảo hành (Dành cho Admin/IT)"""
    try:
        engine = get_db_engine()
        query = text("""
            UPDATE device_maintenance_records 
            SET 
                status = :status,
                solution_description = :solution_description,
                cost = :cost,
                completion_date = :completion_date
            WHERE id = :id
        """)
        
        # Gắn thêm ID vào payload
        data['id'] = record_id
        
        with engine.begin() as conn:
            conn.execute(query, data)
        return True
        
    except Exception as e:
        logger.error(f"Error updating maintenance record {record_id}: {e}")
        st.error("Không thể cập nhật phiếu yêu cầu. Vui lòng thử lại.")
        return False