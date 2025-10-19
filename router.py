# router.py
import os
import asyncio
import base64
import pickle
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from qqmusic_api.login import get_qrcode, check_qrcode, QRLoginType, Credential, QRCodeLoginEvents, check_expired

from nekro_agent.api.core import logger

from .plugin import plugin

plugin_dir = plugin.get_plugin_path()
CREDENTIAL_FILE = plugin_dir / "qqmusic_cred.pkl"
router = APIRouter()

# ... 其他现有代码保持不变 ...

@router.delete("/credential", summary="删除凭证")
async def delete_credential():
    """删除凭证文件"""
    try:
        manager = CredentialManager()
        success = manager.delete_credential()
        if success:
            return {"success": True, "message": "凭证删除成功"}
        else:
            raise HTTPException(status_code=404, detail="凭证文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除凭证失败: {str(e)}")

# ... 其他现有代码保持不变 ...

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

    def delete_credential(self) -> bool:
        """删除凭证文件"""
        try:
            if self.credential_file.exists():
                self.credential_file.unlink()
                self.credential = None
                print("凭证文件已删除")
                return True
            else:
                print("凭证文件不存在")
                return False
        except Exception as e:
            print(f"删除凭证文件失败: {e}")
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