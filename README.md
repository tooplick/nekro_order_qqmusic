# QQ音乐点歌插件

一个基于 [Nekro Agent](https://github.com/KroMiose/nekro-agent) 框架的 QQ 音乐点歌插件，允许 AI 助手通过 QQ 音乐搜索并发送音乐消息。

## 功能特点

- 智能搜索 QQ 音乐歌曲
- **支持外部API** 
   - (默认: `https://api.ygking.top`)
- 可配置专辑封面尺寸
- 可选FLAC,MP3_320,MP3_128音质
- 提供Web界面用于生成和管理QQ音乐凭证

## 使用模式

### 外部API模式 (推荐)
配置 `external_api_url` 后，插件将优先使用外部API进行搜索和获取歌曲URL，无需本地凭证。

### 本地凭证模式：
[点此登录！！](../plugins/GeQian.order_qqmusic)  
将 `external_api_url` 留空，或外部API不可用时自动回退到本地凭证。

## 凭证生成 (本地模式)

### 使用Web界面
- 访问 `http://<服务器ip:NA端口>/plugins/GeQian.order_qqmusic`
- 选择登录方式，扫码完成登录
- 凭证将自动保存
- 请使用VIP账号生成凭证!

## API接口

插件提供以下API接口用于凭证管理：
- `GET /api/get_qrcode/{type}` - 生成登录二维码（type: qq|wx|mobile）
- `GET /api/credential/status` - 检查凭证状态
- `POST /api/credential/refresh` - 刷新凭证
- `GET /api/credential/info` - 获取凭证信息

### Bot 调用

```python
# 手动使用
/exec send_music("onebot_v11-private_12345678", "晴天")
```

### 外部API部署

详情见：[tooplick/qq-music-api](https://github.com/tooplick/qq-music-api)

## 版本历史

- v2.2.0: 新增外部API支持
  - 支持通过外部API搜索和获取歌曲URL
  - 凭证优先级: 外部API > 本地凭证
- v2.1.1: 优化和添加功能
  - 迁移API库至本地
  - 新增支持手机客户端登录
  - 更新Web界面
  - 优化登录逻辑
- v2.1.0: 功能更新
  - 新增发送音乐卡片
- v2.0.6: 小更新
  - 修复无专辑歌曲获取封面失败
- v2.0.5: 小更新
  - 新增自动刷新凭证
  - 更改插件为Agent方法
- v2.0.4：优化设置
  - 新增封面开关
- v2.0.3：更加人性化
  - 添加Web界面用于凭证管理
- v2.0.2：第一次更新
  - 修复歌曲名称显示问题
  - 添加音质选项：FLAC、MP3_320、MP3_128
- v2.0.1：初始发布版本
  - 基础音乐搜索和发送功能
  - 可配置专辑封面尺寸

## 作者信息

- **作者**：[搁浅](https://github.com/tooplick)
- **Web页面支持**：[运阳](https://github.com/yang208115)

## 许可证

本代码遵循 [GPL-3.0 License](https://github.com/tooplick/nekro_order_qqmusic/blob/main/LICENSE) 协议

## 注意事项
- 请确保遵守 QQ 音乐的使用条款和版权规定
- 插件仅用于学习和交流目的
