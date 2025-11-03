# QQ音乐点歌插件

一个基于 Nekro Agent 框架的 QQ 音乐点歌插件，允许 AI 助手通过 QQ 音乐搜索并发送音乐消息。

## 功能特点

- 智能搜索 QQ 音乐歌曲
- 可配置专辑封面尺寸
- 可选FLAC,MP3_320,MP3_128音质
- 注意:这会影响发送语音的速度！
- 提供Web界面用于生成和管理QQ音乐凭证

## 凭证生成

### 方法一：使用Web界面（推荐）
插件提供了一个Web界面用于生成和管理QQ音乐凭证：
- 启动插件后，访问 http://<服务器ip:NA端口>/plugins/GeQian.order_qqmusic
- 点击"QQ登录"或"微信登录"按钮
- 使用手机扫描二维码完成登录
- 凭证将自动保存
- 请使用VIP账号生成凭证！
### 方法二：外部工具生成
- 生成工具见Releases
- 凭证文件"qqmusic_cred.pkl"
- 请放入插件的配置文件夹:
- /nekro_agent/plugin_data/GeQian.order_qqmusic/qqmusic_cred.pkl
- 请使用VIP账号生成凭证！

## API接口

插件提供以下API接口用于凭证管理：
- `GET /api/get_qrcode/{type}` - 生成登录二维码（type: qq|wx）
- `GET /api/credential/status` - 检查凭证状态
- `POST /api/credential/refresh` - 刷新凭证
- `GET /api/credential/info` - 获取凭证信息

### AI 助手调用

AI 助手可以通过调用 `send_music` 方法来发送音乐：

```python
# 手动使用
/exec send_music("onebot_v11-private_12345678", "晴天")
```

## 技术细节

- 使用 QQ 音乐官方 API 进行搜索和音频获取
- 支持音频格式自动降级（FLAC → MP3_320 → MP3_128）
- 异步处理所有网络请求
- 提供Web界面用于凭证管理

## 版本历史
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

- **作者**：GeQian
- **GitHub**：[https://github.com/tooplick](https://github.com/tooplick)
- **Web页面支持**：运阳
- **GitHub**：[https://github.com/yang208115](https://github.com/yang208115)

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 注意事项

- 请确保遵守 QQ 音乐的使用条款和版权规定
- 凭证文件需要用户自行获取和配置
- 插件仅用于学习和交流目的

