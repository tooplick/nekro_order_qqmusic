# router.py
import os
import asyncio
import base64
import pickle
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .login import get_qrcode, check_qrcode, check_mobile_qr, QRLoginType, Credential, QRCodeLoginEvents, check_expired

from nekro_agent.api.core import logger

from .plugin import plugin

plugin_dir = plugin.get_plugin_path()
CREDENTIAL_FILE = plugin_dir / "qqmusic_cred.pkl"
router = APIRouter()

# # 挂载静态文件服务
# web_dir = Path(__file__).parent / "web"
# if web_dir.exists():
#     router.mount("/", StaticFiles(directory=web_dir, html=True), name="static")
@router.get("/")
async def webui_index():  
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建web.html的完整路径
    html_path = os.path.join(current_dir, "web", "index.html")
    
    # 返回HTML文件
    return FileResponse(html_path, media_type="text/html")

@router.get("/style.css")
async def webui_style():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建web.html的完整路径
    html_path = os.path.join(current_dir, "web", "style.css")
    
    # 返回HTML文件
    return FileResponse(html_path, media_type="text/css")

@router.get("/script.js")
async def webui():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建web.html的完整路径
    html_path = os.path.join(current_dir, "web", "script.js")
    
    # 返回HTML文件
    return FileResponse(html_path, media_type="text/javascript")



@router.get("/get_qrcode/{qr_type}", summary="二维码登录")
async def qr_login(qr_type: str) -> str:
    """二维码登录"""
    try:
        if qr_type == 'wx':
            qr = await get_qrcode(QRLoginType.WX)
            asyncio.create_task(save_token(qr))
        elif qr_type == 'qq':
            qr = await get_qrcode(QRLoginType.QQ)
            asyncio.create_task(save_token(qr))
        elif qr_type == 'mobile':
            qr = await get_qrcode(QRLoginType.MOBILE)
            asyncio.create_task(save_token_mobile(qr))
        else:
            raise HTTPException(status_code=400, detail="无效的登录类型，仅支持 'wx'、'qq' 或 'mobile'")
        
        logger.info(base64.b64encode(qr.data).decode())
        return base64.b64encode(qr.data).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取二维码失败: {str(e)}")

async def save_token(qr):
    """后台任务：检查二维码状态并保存凭证（QQ/微信登录）"""
    credential = None
    max_attempts = 30  # 最多尝试30次，每次间隔2秒，总计60秒超时
    attempts = 0
    
    try:
        while attempts < max_attempts:
            event, credential = await check_qrcode(qr)
            print(f"二维码状态: {event.name}")
            
            if event == QRCodeLoginEvents.DONE:
                print(f"登录成功! {credential}")
                # 保存凭证
                with CREDENTIAL_FILE.open("wb") as f:
                    pickle.dump(credential, f)
                return credential
            elif event == QRCodeLoginEvents.TIMEOUT:
                print("二维码过期，请重新获取")
                return None
            elif event == QRCodeLoginEvents.REFUSE:
                print("拒绝登录，请重新扫码")
                return None
                
            attempts += 1
            await asyncio.sleep(2)
            
        print("二维码验证超时，请重新获取")
        return None
    except Exception as e:
        print(f"检查二维码状态时发生错误: {e}")
        return None

async def save_token_mobile(qr):
    """后台任务：检查二维码状态并保存凭证（手机客户端登录）"""
    try:
        async for event, credential in check_mobile_qr(qr):
            print(f"手机登录二维码状态: {event.name}")
            
            if event == QRCodeLoginEvents.DONE:
                print(f"手机登录成功! {credential}")
                with CREDENTIAL_FILE.open("wb") as f:
                    pickle.dump(credential, f)
                return credential
            elif event == QRCodeLoginEvents.TIMEOUT:
                print("手机登录二维码过期，请重新获取")
                return None
            elif event == QRCodeLoginEvents.REFUSE:
                print("拒绝手机登录，请重新扫码")
                return None
        
        return None
    except Exception as e:
        print(f"检查手机登录二维码状态时发生错误: {e}")
        return None


@router.get("/credential/status", summary="检查凭证状态")
async def check_credential_status(since_time: float = 0):
    """检查凭证状态
    
    Args:
        since_time: 可选，仅检查在该时间戳之后更新的凭证（用于登录轮询）
    """
    try:
        plugin_dir = plugin.get_plugin_path()
        credential_file = plugin_dir / "qqmusic_cred.pkl"
        
        if not credential_file.exists():
            return {"valid": False, "detail": "凭证文件不存在"}
            
        # 如果指定了时间戳，检查文件修改时间
        if since_time > 0:
            mtime = credential_file.stat().st_mtime
            if mtime <= since_time:
                # 文件未更新（还是旧凭证）
                return {"valid": False, "detail": "等待新凭证生成"}

        async with aiofiles.open(credential_file, "rb") as f:
            credential_content = await f.read()
        
        try:
            cred: Credential = pickle.loads(credential_content)
        except (ModuleNotFoundError, AttributeError, ImportError) as e:
            logger.warning(f"凭证文件已损坏或版本不兼容，自动删除: {e}")
            credential_file.unlink(missing_ok=True)
            return {"valid": False, "detail": "凭证已失效，请重新登录"}

        is_expired = await check_expired(cred)
        
        return {
            "valid": not is_expired,
            "uin": str(cred.str_musicid) if not is_expired else None
        }
    except Exception as e:
        logger.error(f"检查凭证状态失败: {str(e)}")
        return {"valid": False, "error": str(e)}

@router.post("/credential/refresh", summary="刷新凭证")
async def refresh_credential():
    """刷新凭证"""
    manager = CredentialManager()
    try:
        if not manager.load_credential():
            raise HTTPException(status_code=404, detail="未找到凭证文件")
            
        # 确保凭证已加载
        if manager.credential is None:
            raise HTTPException(status_code=400, detail="凭证加载失败")
            
        is_expired = await check_expired(manager.credential)
        can_refresh = await manager.credential.can_refresh()
        
        if not can_refresh:
            raise HTTPException(status_code=400, detail="此凭证不支持刷新")
            
        await manager.credential.refresh()
        if manager.save_credential():
            return {"success": True, "message": "凭证刷新成功"}
        else:
            raise HTTPException(status_code=500, detail="凭证刷新成功但保存失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新凭证失败: {str(e)}")

@router.get("/credential/info", summary="获取凭证信息")
async def get_credential_info():
    """获取凭证信息"""
    manager = CredentialManager()
    if not manager.load_credential() or manager.credential is None:
        raise HTTPException(status_code=404, detail="未找到凭证文件")
    
    # 返回凭证的基本信息，隐藏敏感信息
    cred_dict = manager.credential.__dict__
    info = {}
    for key, value in cred_dict.items():
        if key.lower() in ['token', 'refresh_token', 'cookie']:
            # 敏感信息，只显示部分
            if value and len(str(value)) > 10:
                info[key] = f"{str(value)[:10]}..."
            else:
                info[key] = str(value)
        else:
            info[key] = str(value)
    
    return info

@router.get("/remove", summary="删除本地凭证")
async def remove_credential():
    """删除本地凭证文件"""
    try:
        plugin_dir = plugin.get_plugin_path()
        credential_file = plugin_dir / "qqmusic_cred.pkl"
        
        if not credential_file.exists():
            message = "凭证文件不存在"
            success = False
        else:
            credential_file.unlink()
            logger.info("本地凭证已删除")
            message = "凭证已删除"
            success = True
        
        # 返回简洁的 HTML 页面
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>删除凭证</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, sans-serif; background: #1a1a1a; color: #e0e0e0; min-height: 100vh; display: flex; justify-content: center; align-items: center; }}
        .container {{ text-align: center; padding: 40px; }}
        .icon {{ font-size: 4rem; margin-bottom: 20px; }}
        .message {{ font-size: 1.5rem; margin-bottom: 30px; }}
        a {{ color: #31c27c; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <p class="message">{message}</p>
        <a href="./">← 返回</a>
    </div>
</body>
</html>"""
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"删除凭证失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除凭证失败: {str(e)}")

class CredentialManager:
    """凭证管理器"""

    def __init__(self, credential_file: Path = CREDENTIAL_FILE):
        self.credential_file = credential_file
        self.credential: Optional[Credential] = None

    def load_credential(self) -> Optional[Credential]:
        """加载本地凭证"""
        if not self.credential_file.exists():
            print("未找到凭证文件，请先运行登录程序")
            return None

        try:
            with self.credential_file.open("rb") as f:
                cred = pickle.load(f)
            self.credential = cred
            return cred
        except Exception as e:
            print(f"加载凭证失败: {e}")
            return None

    def save_credential(self) -> bool:
        """保存凭证到文件"""
        if not self.credential:
            print("没有可保存的凭证")
            return False

        try:
            with self.credential_file.open("wb") as f:
                pickle.dump(self.credential, f)
            print("凭证已保存")
            return True
        except Exception as e:
            print(f"保存凭证失败: {e}")
            return False

    async def check_status(self) -> bool:
        """检查凭证状态"""
        if not self.load_credential() or self.credential is None:
            return False

        try:
            # 检查是否过期
            is_expired = await check_expired(self.credential)
            
            # 检查是否可以刷新
            can_refresh = await self.credential.can_refresh()
            
            print(f"凭证状态 - 是否过期: {is_expired}, 可刷新: {can_refresh}")
            
            if hasattr(self.credential, 'musicid'):
                print(f"用户ID: {self.credential.musicid}")

            return not is_expired
        except Exception as e:
            print(f"检查凭证状态时发生错误: {e}")
            return False