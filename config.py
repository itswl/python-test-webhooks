import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置类"""
    
    # 服务器配置
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'
    
    # 安全配置
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'default-secret-key')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/webhook.log'
    
    # 数据存储配置
    DATA_DIR = 'webhooks_data'
    
    # AI 分析和转发配置
    ENABLE_AI_ANALYSIS = os.getenv('ENABLE_AI_ANALYSIS', 'true').lower() == 'true'
    FORWARD_URL = os.getenv('FORWARD_URL', 'http://92.38.131.57:8000/webhook')
    ENABLE_FORWARD = os.getenv('ENABLE_FORWARD', 'true').lower() == 'true'
    
    # JSON 配置
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
