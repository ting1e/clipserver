import secrets
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config import Config

# 会话存储（简单的内存存储）
sessions = {}
SESSION_COOKIE_NAME = "session_id"
SESSION_EXPIRE_HOURS = 24

def create_session(username: str) -> str:
    """创建新会话"""
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "username": username,
        "expires": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
    }
    return session_id

def get_session(session_id: str) -> dict:
    """获取会话信息"""
    if session_id in sessions:
        session = sessions[session_id]
        if datetime.utcnow() < session["expires"]:
            return session
        else:
            # 会话过期，删除
            del sessions[session_id]
    return None

def delete_session(session_id: str):
    """删除会话"""
    if session_id in sessions:
        del sessions[session_id]

def verify_credentials(username: str, password: str) -> bool:
    """验证用户名和密码"""
    correct_username = secrets.compare_digest(username, Config.USERNAME)
    correct_password = secrets.compare_digest(password, Config.PASSWORD)
    return correct_username and correct_password

# HTTP Basic Auth（用于 WebDAV）
security = HTTPBasic()

def get_current_user_basic(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """HTTP Basic Auth 认证（用于 WebDAV 和 API）"""
    if not verify_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

async def get_current_user(request: Request) -> str:
    """获取当前用户（支持会话和 Basic Auth）"""
    # 首先检查会话
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        session = get_session(session_id)
        if session:
            return session["username"]
    
    # 检查 Authorization 头（Basic Auth）
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        import base64
        try:
            credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, password = credentials.split(":", 1)
            if verify_credentials(username, password):
                return username
        except:
            pass
    
    # 未认证
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未登录",
    )

async def require_auth(request: Request) -> str:
    """要求认证（用于页面访问）"""
    try:
        return await get_current_user(request)
    except HTTPException:
        # 未登录，返回 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
