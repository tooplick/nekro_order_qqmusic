# QQ音乐点歌插件

一个基于 Nekro Agent 框架的 QQ 音乐点歌插件，允许 AI 助手通过 QQ 音乐搜索并发送音乐消息。

## 功能特点

- 智能搜索 QQ 音乐歌曲
- 可配置专辑封面尺寸
- 可选FLAC,MP3_320,MP3_128音质
- 注意:这会影响发送语音的速度！

## 凭证生成

- 目前没有添加登录生成凭证的功能
- 所以需要从外部环境生成
- 生成工具见Releases
- 凭证文件"qqmusic_cred.pkl"
- 请放入插件的配置文件夹:
- /nekro_agent/plugin_data/GeQian.order_qqmusic/qqmusic_cred.pkl
- 请使用VIP账号生成凭证！

### AI 助手调用

AI 助手可以通过调用 `send_music` 方法来发送音乐：

```python
# 手动使用
/exec send_music("adapter-group_123456", "周杰伦 晴天")
```

## 技术细节

- 使用 QQ 音乐官方 API 进行搜索和音频获取
- 支持音频格式自动降级（FLAC → MP3_320 → MP3_128）
- 异步处理所有网络请求

## 版本历史
- v2.0.2：第一次更新
  - 修复歌曲名称显示问题
  - 添加音质选项：FLAC、MP3_320、MP3_128
- v2.0.1：初始发布版本
  - 基础音乐搜索和发送功能
  - 可配置专辑封面尺寸

## 作者信息

- **作者**：GeQian
- **GitHub**：[https://github.com/tooplick/nekro_order_qqmusic](https://github.com/tooplick/nekro_order_qqmusic)

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 注意事项

- 请确保遵守 QQ 音乐的使用条款和版权规定
- 凭证文件需要用户自行获取和配置
- 插件仅用于学习和交流目的
