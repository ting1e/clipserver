import json
import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from wsgidav.fs_dav_provider import FilesystemProvider, FileResource
from config import Config
from models import SessionLocal, ClipboardHistory


class MonitoredFileResource(FileResource):
    """
    继承 FileResource，在 SyncClipboard.json 写入完成时记录到数据库
    """
    
    def end_write(self, *, with_errors):
        """重写 end_write 方法，添加写入完成回调"""
        # 调用父类方法
        super().end_write(with_errors=with_errors)
        
        if with_errors:
            print(f"[ClipboardDAV] SyncClipboard.json 写入时发生错误")
            return
            
        print(f"[ClipboardDAV] SyncClipboard.json 写入完成")
        self._on_clipboard_updated()
    
    def _on_clipboard_updated(self):
        """当 SyncClipboard.json 更新时的回调"""
        try:
            # _file_path 是字符串类型，需要转换为 Path 对象
            file_path = Path(self._file_path)
            
            # 读取 JSON 文件
            if not file_path.exists():
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            clip_type = data.get("Type", "")
            content = data.get("Clipboard", "")
            filename = data.get("File", "")
            
            # 构建数据库记录
            record = ClipboardHistory(
                type=clip_type,
                content=content if clip_type == "Text" else filename,
                created_at=datetime.now(ZoneInfo(Config.TIMEZONE))
            )
            
            # 如果是文件或图片类型，复制到 history 目录
            if clip_type in ["Image", "File", "Group"] and filename:
                # 使用 Config.FILE_DIR 而非手动拼接
                source_file = Config.FILE_DIR / filename
                if source_file.exists():
                    # 生成唯一文件名（使用时间戳）
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                    history_filename = f"{timestamp}_{filename}"
                    dest_file = Config.HISTORY_DIR / history_filename
                    
                    # 复制文件
                    shutil.copy2(source_file, dest_file)
                    
                    # 记录文件信息
                    record.file_path = str(dest_file.relative_to(Config.DATA_DIR))
                    record.file_size = dest_file.stat().st_size
                    record.file_hash = data.get("Clipboard", "")  # 使用原有的 hash
            
            # 插入数据库
            db = SessionLocal()
            try:
                db.add(record)
                db.commit()
                print(f"[ClipboardDAV] 记录已保存: type={clip_type}, content={content[:50] if content else filename}")
            except Exception as e:
                db.rollback()
                print(f"[ClipboardDAV] 数据库错误: {e}")
            finally:
                db.close()
                
        except Exception as e:
            print(f"[ClipboardDAV] 处理剪贴板更新失败: {e}")


class ClipboardDAVProvider(FilesystemProvider):
    """
    自定义 WebDAV Provider，监听 SyncClipboard.json 文件变化并记录到数据库
    """
    
    def get_resource_inst(self, path, environ):
        """劫持资源获取过程，替换为 MonitoredFileResource"""
        # path 是 WebDAV 路径（如 "/SyncClipboard.json"），需要和文件名比较
        if path == "/SyncClipboard.json" or path == "SyncClipboard.json":
            self._count_get_resource_inst += 1
            fp = self._loc_to_file_path(path, environ)
            # 文件不存在时返回 None，避免 FileResource.__init__ 中 os.stat() 抛出异常
            if not os.path.exists(fp):
                return None
            return MonitoredFileResource(path, environ, fp)
        else:
            return super().get_resource_inst(path, environ)
        
