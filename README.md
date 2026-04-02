# Lite Digital Human

这是一个面向本地高性能 demo 的数字人项目骨架，先把“文本 -> TTS -> 预览视频 -> Web 控制台”闭环打通，再逐步替换成真实的 `LiveTalking` / `MuseTalk` / `Wav2Lip` / `CosyVoice` 实现。

## 当前版本

- `backend/common.py`：配置、数据结构和基础工具
- `backend/tts.py`：TTS 适配层，优先 Windows 语音合成，失败后走本地合成兜底
- `backend/renderer.py`：用 `ffmpeg` 生成本地预览 mp4
- `backend/manager.py`：任务编排、状态、指标和 manifest
- `backend/dev_server.py`：零依赖本地开发服务器
- `backend/main.py`：后续切换到 FastAPI 的入口
- `web/`：本地控制台
- `scripts/smoke_demo.py`：冒烟测试

## 直接运行

```powershell
python -m backend.dev_server
```

然后打开：

```text
http://127.0.0.1:8000
```

## 冒烟测试

```powershell
python scripts/smoke_demo.py
```

## FastAPI 入口

如果你已经安装了依赖：

```powershell
pip install -r requirements.txt
python -m backend.main
```

## API

- `POST /api/speak`
- `POST /api/stop`
- `GET /api/status?job_id=...`
- `GET /api/jobs`
- `GET /api/metrics`

## 目录

```text
lite-digital-human/
  backend/
  web/
  scripts/
  outputs/
  assets/
  models/
```

## 下一步

1. 把 `CosyVoice` 接成可切换的真实 TTS 后端
2. 把 `MuseTalk` / `Wav2Lip` 接成真实口型驱动后端
3. 把任务状态改成更细的流式进度
4. 再补 OBS / FFmpeg 推流和录制链路
