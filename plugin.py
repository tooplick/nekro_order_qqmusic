import pickle
from pathlib import Path
from urllib.parse import quote
from nekro_agent.api.plugin import dynamic_import_pkg
import httpx
import aiofiles
import json

from nekro_agent.api.plugin import NekroPlugin, SandboxMethodType, ConfigBase
from nekro_agent.api.schemas import AgentCtx

from .search import search_by_type
from .song import get_song_urls, SongFileType
from .login import Credential, check_expired
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, ActionFailed
from typing import Any, Literal, Optional, Dict
from pydantic import Field

plugin = NekroPlugin(
    name="QQ音乐点歌",
    module_name="order_qqmusic",
    description="给予AI助手通过QQ音乐搜索并发送音乐消息的能力",
    version="2.2.0",
    author="GeQian",
    url="https://github.com/tooplick/nekro_order_qqmusic",
)

@plugin.mount_config()
class QQMusicPluginConfig(ConfigBase):
    """QQ音乐插件配置项"""

    use_external_api: bool = Field(
        default=True,
        title="使用外部API获取url",
        description="开启后优先使用外部API，关闭则使用本地凭证。外部API失败时会回退到本地凭证",
    )

    external_api_url: str = Field(
        default="https://api.ygking.top",
        title="外部API地址",
        description="外部QQ音乐API地址，需开启上方开关才生效",
    )

    cover_size: Literal["0", "150", "300", "500", "800"] = Field(
        default="500",
        title="专辑封面尺寸",
        description="选择发送（文字+封面+语音消息）时的封面尺寸，0表示不发送。",
    )
    
    preferred_quality: Literal["FLAC", "MP3_320", "MP3_128"] = Field(
        default="FLAC",
        title="优先音质",
        description="选择歌曲播放的优先音质，如果无法获取将自动降级",
    )
    
    auto_refresh_credential: bool = Field(
        default=True,
        title="自动刷新凭证",
        description="是否在凭证过期时自动刷新凭证",
    )

    enable_json_card: bool = Field(
        default=True,
        title="启用JSON卡片",
        description="使用QQ音乐JSON卡片发送歌曲信息（需API支持）",
    )

    use_external_player: bool = Field(
        default=False,
        title="卡片链接使用外部播放器",
        description="开启后，音乐卡片的主链接将跳转到外部播放器而非QQ音乐官网",
    )

    external_player_url: str = Field(
        default="player.ygking.top",
        title="外部播放器地址",
        description="外部播放器的域名地址",
    )

config: QQMusicPluginConfig = plugin.get_config(QQMusicPluginConfig)

# ========== 外部API功能 ==========

async def search_from_api(keyword: str, num: int = 1) -> list | None:
    """通过外部API搜索歌曲"""
    if not config.external_api_url:
        return None
    
    try:
        api_url = config.external_api_url.rstrip('/')
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_url}/api/search", params={
                "keyword": keyword,
                "type": "song",
                "num": num
            })
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0 and data.get("data", {}).get("list"):
                    print(f"通过外部API搜索成功: {keyword}")
                    return data["data"]["list"]
            print(f"外部API搜索失败: {resp.status_code}")
    except Exception as e:
        print(f"外部API搜索异常: {e}")
    return None

async def get_song_url_from_api(mid: str, quality: str = "128") -> str | None:
    """通过外部API获取歌曲URL"""
    if not config.external_api_url:
        return None
    
    try:
        api_url = config.external_api_url.rstrip('/')
        quality_map = {"FLAC": "flac", "MP3_320": "320", "MP3_128": "128"}
        q = quality_map.get(quality, "128")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_url}/api/song/url", params={
                "mid": mid,
                "quality": q
            })
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    url = data["data"].get(mid)
                    if url:
                        print(f"通过外部API获取歌曲URL成功: {mid}")
                        return url
            print(f"外部API获取URL失败: {resp.status_code}")
    except Exception as e:
        print(f"外部API获取URL异常: {e}")
    return None

# ========== 本地凭证功能 ==========

async def load_and_refresh_credential() -> Credential | None:
    """加载本地凭证，如果过期则根据配置自动刷新，使用插件持久化目录"""
    try:
        plugin_dir = plugin.get_plugin_path()
        credential_file = plugin_dir / "qqmusic_cred.pkl"

        if not credential_file.exists():
            print("QQ音乐凭证文件不存在")
            return f"凭证文件不存在"

        async with aiofiles.open(credential_file, "rb") as f:
            credential_content = await f.read()
        
        try:
            cred: Credential = pickle.loads(credential_content)
        except (ModuleNotFoundError, AttributeError, ImportError, EOFError):
            print("凭证文件已损坏或版本不兼容，自动删除")
            credential_file.unlink(missing_ok=True)
            return "凭证已损坏，请重新登录"

        is_expired = await check_expired(cred)
        
        if is_expired:
            print("QQ音乐凭证已过期")
            if not config.auto_refresh_credential:
                return f"自动刷新凭证功能已关闭,无法刷新过期凭证"
            
            print("尝试自动刷新...")
            can_refresh = await cred.can_refresh()
            if can_refresh:
                try:
                    await cred.refresh()
                    async with aiofiles.open(credential_file, "wb") as f:
                        await f.write(pickle.dumps(cred))
                    return cred
                except Exception as refresh_error:
                    return f"QQ音乐凭证自动刷新失败: {refresh_error}"
            else:
                return f"QQ音乐凭证不支持刷新"
        else:
            print("QQ音乐凭证加载成功")
            return cred
            
    except Exception as e:
        return f"加载QQ音乐凭证失败"

def get_quality_priority(preferred_quality: str) -> list[SongFileType]:
    """根据优先音质返回音质优先级列表"""
    quality_map = {
        "FLAC": [SongFileType.FLAC, SongFileType.MP3_320, SongFileType.MP3_128],
        "MP3_320": [SongFileType.MP3_320, SongFileType.MP3_128],
        "MP3_128": [SongFileType.MP3_128]
    }
    return quality_map.get(preferred_quality, [SongFileType.MP3_320, SongFileType.MP3_128])

async def get_song_url(song_info: dict, credential: Credential, preferred_quality: str) -> str:
    """根据优先音质获取歌曲下载链接，失败时自动降级"""
    mid = song_info['mid']
    quality_priority = get_quality_priority(preferred_quality)
    quality_names = {
        SongFileType.FLAC: "FLAC无损",
        SongFileType.MP3_320: "MP3高品质",
        SongFileType.MP3_128: "MP3标准"
    }
    last_exception = None
    
    for file_type in quality_priority:
        try:
            urls = await get_song_urls([mid], file_type=file_type, credential=credential)
            url = urls[mid] if isinstance(urls[mid], str) else urls[mid][0]
            if url:
                quality_name = quality_names.get(file_type, str(file_type))
                print(f"使用{quality_name}音质")
                return url
        except Exception as e:
            last_exception = e
            quality_name = quality_names.get(file_type, str(file_type))
            print(f"{quality_name}音质获取失败: {e}")
            continue
    
    raise ValueError(f"无法获取歌曲下载链接，所有音质尝试均失败。最后错误: {last_exception}")

async def download_cover_check(url: str) -> bool:
    """下载并验证封面图片"""
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                content = resp.content
                if len(content) > 1024:
                    if content.startswith(b'\xff\xd8') or content.startswith(b'\x89PNG'):
                        return True
                    else:
                        print(f"封面图片格式无效: {url}")
                else:
                    print(f"封面图片过小: {len(content)} bytes, URL: {url}")
            else:
                print(f"封面下载失败: HTTP {resp.status_code}, URL: {url}")
    except Exception as e:
        print(f"封面下载异常: {e}, URL: {url}")
    return False

def get_cover_url_by_album_mid(mid: str, size: int) -> str:
    return f"https://y.gtimg.cn/music/photo_new/T002R{size}x{size}M000{mid}.jpg"

def get_cover_url_by_vs(vs: str, size: int) -> str:
    return f"https://y.qq.com/music/photo_new/T062R{size}x{size}M000{vs}.jpg"

async def get_valid_cover_url(song_data: Dict[str, Any], size: int = 300) -> Optional[str]:
    """获取并验证有效的封面URL"""
    if size == 0:
        return None
    
    valid_sizes = [150, 300, 500, 800]
    if size not in valid_sizes:
        print(f"无效的封面尺寸: {size}，重置为300")
        size = 300

    # 1. 优先尝试专辑MID
    album_mid = song_data.get('album', {}).get('mid', '')
    if album_mid:
        url = get_cover_url_by_album_mid(album_mid, size)
        if await download_cover_check(url):
            print(f"使用专辑MID封面({size}x{size}): {url}")
            return url

    # 2. 尝试VS值
    vs_values = song_data.get('vs', [])
    if not vs_values:
        print("未找到VS值，且专辑封面不可用")
        return None
    
    candidate_vs = []
    # 收集单个VS值
    for i, vs in enumerate(vs_values):
        if vs and isinstance(vs, str) and len(vs) >= 3 and ',' not in vs:
            candidate_vs.append({'value': vs, 'priority': 1})
    # 收集逗号分隔VS值
    for i, vs in enumerate(vs_values):
        if vs and isinstance(vs, str) and ',' in vs:
            parts = [part.strip() for part in vs.split(',') if part.strip()]
            for part in parts:
                if len(part) >= 3:
                    candidate_vs.append({'value': part, 'priority': 2})

    candidate_vs.sort(key=lambda x: x['priority'])

    for candidate in candidate_vs:
        val = candidate['value']
        url = get_cover_url_by_vs(val, size)
        if await download_cover_check(url):
            print(f"使用VS值封面({size}x{size}): {url}")
            return url

    print("无法获取任何有效的封面URL")
    return None

async def get_signed_ark_card(song_info: dict, real_cover_url: str, real_music_url: str) -> Optional[str]:
    """通过API获取签名的QQ音乐JSON Ark卡片数据"""
    try:
        mid = song_info['mid']
        title = song_info['title']
        singer = song_info['singer'][0]['name']
        
        # 根据配置生成跳转 URL
        jump_url = build_jump_url(mid, title, singer, real_cover_url, real_music_url)
        
        data = {
            "url": real_music_url,
            "jump": jump_url,
            "song": title,
            "singer": singer,
            "cover": real_cover_url if real_cover_url else "",
            "format": "qq"
        }
        
        api_url = "https://oiapi.net/api/QQMusicJSONArk"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(api_url, data=data)
            if resp.status_code == 200:
                resp_json = resp.json()
                if resp_json.get("code") == 1 and resp_json.get("message"):
                    return resp_json["message"]
                else:
                    print(f"获取Ark卡片失败: {resp_json}")
            else:
                print(f"Ark API请求失败: {resp.status_code}")
    except Exception as e:
        print(f"获取Ark卡片出错: {e}")
    return None


def clean_text(text: str) -> str:
    """清理文本中的无效 Unicode 字符（如私用区字符、代理对、控制字符等）"""
    if not text:
        return text
    
    cleaned = []
    for char in text:
        code = ord(char)
        # 移除私用区字符
        if (0xE000 <= code <= 0xF8FF or 
            0xF0000 <= code <= 0xFFFFD or
            0x100000 <= code <= 0x10FFFD):
            continue
        # 移除代理对字符
        if 0xD800 <= code <= 0xDFFF:
            continue
        # 移除控制字符
        if code <= 0x1F or code == 0x7F:
            continue
        cleaned.append(char)
    return ''.join(cleaned)


def build_jump_url(
    song_mid: str,
    song_name: str,
    artist: str,
    cover_url: str,
    music_url: str
) -> str:
    """根据配置生成跳转 URL"""
    if config.use_external_player:
        # 使用外部播放器
        base_url = config.external_player_url.rstrip("/")
        if not base_url or len(base_url) > 200 or any(ord(c) > 127 for c in base_url):
            print(f"检测到异常的外部播放器 URL 配置: {base_url}，已回退到默认")
            base_url = "player.ygking.top"

        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"
        
        # 清理无效字符并构建 URL 参数
        clean_title = clean_text(str(song_name))
        clean_artist = clean_text(str(artist))
        
        try:
            quoted_title = quote(quote(clean_title, encoding='utf-8', safe=''), safe='')
            quoted_artist = quote(quote(clean_artist, encoding='utf-8', safe=''), safe='')
            quoted_cover = quote(str(cover_url), encoding='utf-8', safe='')
            quoted_audio = quote(str(music_url), encoding='utf-8', safe='')
            quoted_detail = quote(f'https://y.qq.com/n/ryqq/songDetail/{song_mid}', encoding='utf-8', safe='')
        except Exception as e:
            print(f"URL 参数编码失败: {e}")
            return f"https://y.qq.com/n/ryqq/songDetail/{song_mid}"

        params = [
            f"title={quoted_title}",
            f"artist={quoted_artist}",
            f"cover={quoted_cover}",
            f"audio={quoted_audio}",
            f"detail={quoted_detail}"
        ]
        return f"{base_url}/?{'&'.join(params)}"
    else:
        # 使用QQ音乐官网
        return f"https://y.qq.com/n/ryqq/songDetail/{song_mid}"

def parse_chat_key(chat_key: str) -> tuple[str, int]:
    if "_" not in chat_key:
        raise ValueError(f"无效的 chat_key: {chat_key}")
    adapter_id, old_chat_key = chat_key.split("-", 1)
    chat_type, target_id = old_chat_key.split("_", 1)
    if not target_id.isdigit() or chat_type not in ("private", "group"):
        raise ValueError(f"chat_key 格式错误: {chat_key}")
    return chat_type, int(target_id)

async def send_message(bot, chat_type: str, target_id: int, message) -> bool:
    try:
        if chat_type == "private":
            await bot.call_api("send_private_msg", user_id=target_id, message=message)
        else:
            await bot.call_api("send_group_msg", group_id=target_id, message=message)
        return True
    except ActionFailed as e:
        print(f"发送消息失败: {e}")
        return False

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="send_music",
    description="搜索 QQ 音乐并发送歌曲信息、专辑封面和语音消息"
)
async def send_music(
        _ctx: AgentCtx,
        chat_key: str,
        keyword: str
) -> str:
    """
    搜索 QQ 音乐歌曲并发送给用户（文字+封面+语音）或音乐卡片

    Args:
        chat_key (str): 会话标识，例如"onebot_v11-private_12345678" 或 "onebot_v11-group_12345678"
        keyword (str): 搜索关键词：歌曲名 歌手名

    Returns:
        str: 发送结果提示信息，例如 "歌曲《xxx》已发送"
    """
    try:
        bot = get_bot()

        use_external = False
        credential = None
        first_song = None
        music_url = None

        # 根据配置决定优先级
        if config.use_external_api and config.external_api_url:
            # 1. 开启外部API时：优先使用外部API
            print(f"优先使用外部API: {config.external_api_url}")
            
            # 1.1 通过外部API搜索
            result = await search_from_api(keyword, num=1)
            if result:
                first_song = result[0]
                mid = first_song.get("mid")
                
                # 1.2 通过外部API获取歌曲URL
                if mid:
                    music_url = await get_song_url_from_api(mid, config.preferred_quality)
                    if music_url:
                        use_external = True
                        print("外部API获取成功")
            
            # 1.3 外部API失败时，回退到本地凭证
            if not first_song or not music_url:
                print("外部API获取失败，回退到本地凭证...")
                credential = await load_and_refresh_credential()
                
                if credential and not isinstance(credential, str):
                    print("本地凭证有效，使用本地模式")
                    result = await search_by_type(keyword=keyword, num=1)
                    if result:
                        first_song = result[0]
                        try:
                            music_url = await get_song_url(first_song, credential, config.preferred_quality)
                        except Exception as e:
                            print(f"本地获取歌曲URL失败: {e}")
                            music_url = None
                else:
                    print(f"本地凭证不可用: {credential}")
        else:
            # 2. 关闭外部API时：直接使用本地凭证
            print("使用本地凭证模式...")
            credential = await load_and_refresh_credential()
            
            if credential and not isinstance(credential, str):
                print("本地凭证有效")
                result = await search_by_type(keyword=keyword, num=1)
                if result:
                    first_song = result[0]
                    try:
                        music_url = await get_song_url(first_song, credential, config.preferred_quality)
                    except Exception as e:
                        print(f"本地获取歌曲URL失败: {e}")
                        music_url = None
            else:
                print(f"本地凭证不可用: {credential}")
        
        # 3. 检查结果

        if not first_song or not music_url:
            return f"无法获取歌曲信息或播放链接"

        singer = first_song["singer"][0]["name"] if first_song.get("singer") else "未知歌手"
        title = first_song.get("title", first_song.get("name", "未知歌曲"))

        # 3. 获取封面 (双轨制：卡片强制500，普通消息遵循配置)
        
        # 3.1 获取卡片专用封面 (固定500)
        card_cover_url = None
        if config.enable_json_card:
            card_cover_url = await get_valid_cover_url(first_song, size=500)
        
        # 3.2 获取普通消息专用封面 (遵循用户配置)
        config_size = int(config.cover_size)
        msg_cover_url = None
        
        if config_size > 0:
            if config_size == 500 and card_cover_url:
                msg_cover_url = card_cover_url
            else:
                msg_cover_url = await get_valid_cover_url(first_song, size=config_size)

        # 4. 解析发送目标
        chat_type, target_id = parse_chat_key(chat_key)

        # 6. 尝试发送卡片 (使用 card_cover_url)
        card_sent = False
        if config.enable_json_card:
            print(f"尝试获取并发送JSON卡片: {title}")
            # 这里传入 card_cover_url (800尺寸)
            json_payload = await get_signed_ark_card(first_song, card_cover_url, music_url)
            
            if json_payload:
                json_msg = MessageSegment.json(json_payload)
                if await send_message(bot, chat_type, target_id, json_msg):
                    card_sent = True
                    print("JSON卡片发送成功")
                else:
                    print("JSON卡片发送失败")
            else:
                print("获取JSON卡片数据失败")

        # 7. 结果处理
        if card_sent:
            return f"歌曲《{title}》卡片已发送"
        else:
            # 降级：发送文字 + 图片(使用 msg_cover_url) + 语音
            message_text = f"{title}-{singer}"
            await send_message(bot, chat_type, target_id, message_text)

            if msg_cover_url:
                cover_msg = MessageSegment.image(msg_cover_url)
                await send_message(bot, chat_type, target_id, cover_msg)

            voice_msg = MessageSegment.record(file=music_url)
            await send_message(bot, chat_type, target_id, voice_msg)
            
            return f"歌曲《{title}》已以(文字+封面+语音)方式发送"

    except Exception as e:
        return f"发送音乐消息失败: {e}"

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    print("QQ音乐插件资源已清理")