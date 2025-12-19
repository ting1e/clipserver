from fastapi import FastAPI, Depends, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from a2wsgi import WSGIMiddleware
from models import init_db
from config import Config
from auth import (
    get_current_user, verify_credentials, create_session, 
    delete_session, SESSION_COOKIE_NAME
)
from api.history import router as history_router
from webdav_server import create_webdav_app

# 初始化数据库
init_db()

# 创建 FastAPI 应用
app = FastAPI(
    title="Clipboard History Server",
    description="剪贴板历史记录查看系统（集成 WebDAV 服务端）",
    version="1.0.0"
)

# 登录请求模型
class LoginRequest(BaseModel):
    username: str
    password: str

# 登录 API
@app.post("/api/login")
async def login(request: LoginRequest, response: Response):
    """用户登录"""
    if verify_credentials(request.username, request.password):
        session_id = create_session(request.username)
        response = JSONResponse(content={"message": "登录成功"})
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            max_age=86400,  # 24小时
            samesite="lax"
        )
        return response
    else:
        return JSONResponse(
            status_code=401,
            content={"detail": "用户名或密码错误"}
        )

# 登出 API
@app.post("/api/logout")
async def logout(request: Request, response: Response):
    """用户登出"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        delete_session(session_id)
    response = JSONResponse(content={"message": "已登出"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response

# 检查登录状态
@app.get("/api/check-auth")
async def check_auth(request: Request):
    """检查是否已登录"""
    try:
        username = await get_current_user(request)
        return {"authenticated": True, "username": username}
    except:
        return {"authenticated": False}

# 注册 API 路由（需要认证）
app.include_router(history_router)

# 挂载 WebDAV 服务（通过 a2wsgi 适配）
webdav_app = create_webdav_app()
app.mount("/dav", WSGIMiddleware(webdav_app))

# 根路由重定向
@app.get("/")
async def read_root(request: Request):
    """根路由 - 检查登录状态并重定向"""
    try:
        await get_current_user(request)
        return RedirectResponse(url="/index.html")
    except:
        return RedirectResponse(url="/login.html")

# 健康检查（不需要认证）- 必须在静态文件挂载之前定义
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}

# 挂载静态文件（放在最后，使用根路径）
# 注意：这会捕获所有未匹配的路径，所以必须放在所有路由定义之后
app.mount("/", StaticFiles(directory=str(Config.STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on {Config.HOST}:{Config.PORT}")
    print(f"WebDAV URL: http://{Config.HOST}:{Config.PORT}/dav")
    print(f"Username: {Config.USERNAME}")
    print(f"Password: {'*' * len(Config.PASSWORD)}")
    
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=True
    )
