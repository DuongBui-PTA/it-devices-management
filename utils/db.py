# utils/db.py

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import logging
from .config import DB_CONFIG, APP_CONFIG

logger = logging.getLogger(__name__)

# Sử dụng @st.cache_resource để chỉ tạo Engine 1 lần duy nhất cho toàn bộ phiên chạy ứng dụng
@st.cache_resource(show_spinner=False)
def get_db_engine():
    """Create and return SQLAlchemy database engine (Cached)"""
    logger.info("🔌 Initializing new database engine connection pool...")

    user = DB_CONFIG["user"]
    password = quote_plus(str(DB_CONFIG["password"]))
    host = DB_CONFIG["host"]
    port = DB_CONFIG["port"]
    database = DB_CONFIG["database"]

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    logger.info(f"🔐 Using SQLAlchemy URL: mysql+pymysql://{user}:***@{host}:{port}/{database}")

    # Lấy thông số cấu hình Pool từ APP_CONFIG (nếu không có thì dùng giá trị mặc định)
    pool_size = APP_CONFIG.get("DB_POOL_SIZE", 5)
    pool_recycle = APP_CONFIG.get("DB_POOL_RECYCLE", 3600)

    # Khởi tạo engine kèm cấu hình Connection Pool an toàn
    engine = create_engine(
        url,
        pool_size=pool_size,         # Số lượng kết nối tối đa được giữ trong pool
        max_overflow=10,             # Số lượng kết nối cho phép vượt quá pool_size khi tải cao
        pool_recycle=pool_recycle,   # Tự động đóng/tái tạo kết nối sau N giây (tránh timeout của MySQL)
        pool_pre_ping=True           # CỰC KỲ QUAN TRỌNG: Kiểm tra kết nối có còn sống không trước khi thực thi query
    )
    
    return engine