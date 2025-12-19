from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
from models import ClipboardHistory, get_db
from auth import get_current_user
from config import Config

router = APIRouter(prefix="/api", tags=["history"])

@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=10000, description="每页数量"),
    type: Optional[str] = Query(None, description="类型筛选: Text/Image/File/Group"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    favorited: Optional[bool] = Query(None, description="仅显示收藏"),
    start_date: Optional[str] = Query(None, description="开始日期 (ISO格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO格式)"),
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    获取剪贴板历史记录列表
    
    需要认证: 是
    """
    # 构建查询
    query = db.query(ClipboardHistory)
    
    # 类型筛选
    if type:
        query = query.filter(ClipboardHistory.type == type)
    
    # 收藏筛选
    if favorited is not None:
        if favorited:
            # 只显示收藏的：extra_data 包含 "favorited": true（注意可能有空格）
            query = query.filter(
                ClipboardHistory.extra_data.isnot(None),
                or_(
                    ClipboardHistory.extra_data.contains('"favorited":true'),
                    ClipboardHistory.extra_data.contains('"favorited": true')
                )
            )
        else:
            # 只显示未收藏的：extra_data 为 NULL 或不包含 "favorited":true
            query = query.filter(
                or_(
                    ClipboardHistory.extra_data.is_(None),
                    and_(
                        ~ClipboardHistory.extra_data.contains('"favorited":true'),
                        ~ClipboardHistory.extra_data.contains('"favorited": true')
                    )
                )
            )
    
    # 搜索
    if search:
        query = query.filter(
            or_(
                ClipboardHistory.content.contains(search),
                ClipboardHistory.extra_data.contains(search)
            )
        )
    
    # 日期范围筛选
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(ClipboardHistory.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(ClipboardHistory.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    # 计算总数
    total = query.count()
    
    # 排序和分页
    items = query.order_by(desc(ClipboardHistory.created_at))\
                 .offset((page - 1) * page_size)\
                 .limit(page_size)\
                 .all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.to_dict() for item in items]
    }

@router.get("/history/{id}")
async def get_history_item(
    id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    获取单条历史记录详情
    
    需要认证: 是
    """
    item = db.query(ClipboardHistory).filter(ClipboardHistory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return item.to_dict()

@router.get("/file/{id}")
async def get_file(
    id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    获取历史记录中的文件
    
    需要认证: 是
    """
    item = db.query(ClipboardHistory).filter(ClipboardHistory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if not item.file_path:
        raise HTTPException(status_code=404, detail="No file associated with this record")
    
    file_path = Config.DATA_DIR / item.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=item.content,
        media_type="application/octet-stream"
    )

@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    获取统计信息
    
    需要认证: 是
    """
    total_records = db.query(ClipboardHistory).count()
    
    # 按类型统计
    by_type = {}
    for type_name in ["Text", "Image", "File", "Group"]:
        count = db.query(ClipboardHistory).filter(ClipboardHistory.type == type_name).count()
        by_type[type_name] = count
    
    # 获取最新同步时间
    latest = db.query(ClipboardHistory).order_by(desc(ClipboardHistory.created_at)).first()
    latest_sync = latest.created_at.isoformat() if latest else None
    
    return {
        "total_records": total_records,
        "by_type": by_type,
        "latest_sync": latest_sync
    }

@router.get("/info")
async def get_info(username: str = Depends(get_current_user)):
    """
    获取系统信息
    
    需要认证: 是
    """
    return {
        "webdav_url": f"http://localhost:{Config.PORT}/dav",
        "storage_path": str(Config.DATA_DIR),
        "history_path": str(Config.HISTORY_DIR),
        "db_path": str(Config.DB_PATH)
    }

@router.post("/history/{id}/favorite")
async def toggle_favorite(
    id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    切换收藏状态
    
    需要认证: 是
    """
    import json
    
    item = db.query(ClipboardHistory).filter(ClipboardHistory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # 解析 extra_data
    try:
        extra_data = json.loads(item.extra_data) if item.extra_data else {}
    except:
        extra_data = {}
    
    # 切换收藏状态
    is_favorited = extra_data.get('favorited', False)
    extra_data['favorited'] = not is_favorited
    
    # 保存
    item.extra_data = json.dumps(extra_data, ensure_ascii=False)
    db.commit()
    
    return {
        "id": id,
        "favorited": extra_data['favorited']
    }

@router.delete("/history/{id}")
async def delete_history(
    id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    删除单条记录
    
    需要认证: 是
    """
    from config import Config
    import os
    
    item = db.query(ClipboardHistory).filter(ClipboardHistory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # 删除关联文件
    if item.file_path:
        file_path = Config.DATA_DIR / item.file_path
        if file_path.exists():
            try:
                os.remove(file_path)
            except:
                pass
    
    # 删除数据库记录
    db.delete(item)
    db.commit()
    
    return {"message": "Record deleted successfully"}

@router.post("/history/batch-delete")
async def batch_delete_history(
    ids: List[int],
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    """
    批量删除记录
    
    需要认证: 是
    """
    from config import Config
    import os
    
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    items = db.query(ClipboardHistory).filter(ClipboardHistory.id.in_(ids)).all()
    
    deleted_count = 0
    for item in items:
        # 删除关联文件
        if item.file_path:
            file_path = Config.DATA_DIR / item.file_path
            if file_path.exists():
                try:
                    os.remove(file_path)
                except:
                    pass
        
        # 删除数据库记录
        db.delete(item)
        deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully deleted {deleted_count} records",
        "deleted_count": deleted_count
    }
