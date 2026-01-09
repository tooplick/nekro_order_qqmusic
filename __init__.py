from .plugin import plugin
from fastapi import APIRouter
import logging
import os
import sys

# QQMusic API 初始化逻辑
from . import login, search, song

logger = logging.getLogger("qqmusicapi")

# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import WindowsSelectorEventLoopPolicy, set_event_loop_policy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

__all__ = ["plugin", "login", "search", "song"]

@plugin.mount_router()
def create_router() -> APIRouter:
    """创建并配置插件路由"""
    from .router import router
    return router