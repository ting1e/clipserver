from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

Base = declarative_base()

class ClipboardHistory(Base):
    """剪贴板历史记录模型"""
    __tablename__ = "clipboard_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False, index=True)  # Text/Image/File/Group
    content = Column(Text)  # 文本内容或文件名
    file_path = Column(String(500))  # 文件在 history 目录中的路径
    file_hash = Column(String(64))  # 文件哈希值
    file_size = Column(Integer)  # 文件大小（字节）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    extra_data = Column(Text)  # JSON 格式的额外元数据（改名避免与 metadata 冲突）
    
    # 组合索引，优化常见查询
    __table_args__ = (
        Index('idx_created_type', 'created_at', 'type'),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra_data": self.extra_data
        }

# 创建数据库引擎
engine = create_engine(
    f"sqlite:///{Config.DB_PATH}",
    connect_args={"check_same_thread": False}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
