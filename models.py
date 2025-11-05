"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

Base = declarative_base()


class WebhookEvent(Base):
    """Webhook 事件模型"""
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False, index=True)
    client_ip = Column(String(50))
    timestamp = Column(DateTime, nullable=False, default=datetime.now, index=True)
    
    # 原始数据
    raw_payload = Column(Text)
    headers = Column(JSON)
    parsed_data = Column(JSON)
    
    # AI 分析结果
    ai_analysis = Column(JSON)
    importance = Column(String(20), index=True)  # high, medium, low
    
    # 转发状态
    forward_status = Column(String(20))  # success, failed, skipped
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'source': self.source,
            'client_ip': self.client_ip,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'raw_payload': self.raw_payload,
            'headers': self.headers,
            'parsed_data': self.parsed_data,
            'ai_analysis': self.ai_analysis,
            'importance': self.importance,
            'forward_status': self.forward_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# 数据库连接
def get_engine():
    """获取数据库引擎"""
    database_url = Config.DATABASE_URL
    return create_engine(database_url, echo=False, pool_pre_ping=True)


def get_session():
    """获取数据库会话"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """初始化数据库表"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("数据库表初始化完成")


if __name__ == '__main__':
    init_db()
