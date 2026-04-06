# Lite Digital Human

这是一个面向本地高性能 demo 的数字人项目骨架。当前已经打通“文本 -> TTS -> 口型合成 -> 最终编码 -> Web 控制台”的闭环，后续会继续把真实的 `LiveTalking` / `MuseTalk` / `Wav2Lip` / `CosyVoice` 能力接进来。

## 当前状态

- 任务链路已经拆成三段：`TTS`、`口型合成`、`最终编码`
- `CosyVoice`、`MuseTalk`、`Wav2Lip` 都已经预留成可插拔适配层
- 在没有真实模型时，项目仍然可以回退到当前的本地 demo 预览
- Web 控制台已经可以提交文案、查看阶段、查看后端选择和预览结果
- `scripts/cosyvoice_bridge.py` 已经提供了真实 `CosyVoice` 的桥接入口

## 当前后端选择逻辑

- TTS 优先级：`CosyVoice` -> Windows 系统语音 -> 合成兜底
- 口型合成优先级：`MuseTalk` -> `Wav2Lip` -> 本地 demo 预览
- 最终输出会统一经过 `FFmpeg` 做音频封装和视频输出

## 目录约定

```text
lite-digital-human/
  backend/
  web/
  scripts/
  assets/
  models/
  outputs/
```

## 运行方式

### 方式 1: 直接跑本地开发服务器

```powershell
python -m backend.dev_server
```

然后打开：

```text
http://127.0.0.1:8000
```

### 方式 2: 跑冒烟测试

```powershell
python scripts/smoke_demo.py
```

### 方式 3: 后续切到 FastAPI

先安装依赖：

```powershell
pip install -r requirements.txt
```

然后运行：

```powershell
python -m backend.main
```

## 真实 CosyVoice 接入

当前项目已经内置了一个真实 CosyVoice 的桥接脚本：[scripts/cosyvoice_bridge.py](D:/work_place/lite-digital-human/scripts/cosyvoice_bridge.py)。

推荐准备方式如下：

- 将官方 CosyVoice 仓库放到 `models/CosyVoice`
- 将官方 `pretrained_models` 权重目录放到 `models/CosyVoice/pretrained_models`
- 保证仓库里能找到 `cosyvoice/cli/cosyvoice.py` 或 `example.py`
- 让权重目录下至少有一个可识别的模型目录，例如 `CosyVoice-300M-SFT`、`CosyVoice-300M-Instruct`、`CosyVoice2-0.5B` 或 `Fun-CosyVoice3-0.5B`

默认情况下，TTS 后端会按下面顺序选择：

1. 你手动指定的 `DHD_COSYVOICE_CMD`
2. 项目内置的真实 CosyVoice 桥接脚本
3. 官方仓库里的本地脚本（如果你自己指定了 `DHD_COSYVOICE_SCRIPT`）
4. Windows 系统语音
5. 合成兜底

### 常用环境变量

- `DHD_COSYVOICE_DIR`：CosyVoice 仓库根目录，默认是 `models/CosyVoice`
- `DHD_COSYVOICE_WEIGHTS_DIR`：CosyVoice 权重目录
- `DHD_COSYVOICE_MODE`：`auto`、`sft` 或 `zero_shot`
- `DHD_COSYVOICE_MODEL_KIND`：模型家族提示，例如 `cosyvoice` 或 `cosyvoice2`
- `DHD_COSYVOICE_SPK_ID`：SFT 模式使用的说话人，默认是 `中文女`
- `DHD_COSYVOICE_PROMPT_TEXT`：零样本模式的参考文本
- `DHD_COSYVOICE_PROMPT_WAV`：零样本模式的参考音频
- `DHD_COSYVOICE_TEXT_FRONTEND`：是否启用 CosyVoice 文本前端，默认是 `1`

### 桥接脚本直接运行示例

```powershell
python scripts/cosyvoice_bridge.py \
  --repo-dir D:\work_place\lite-digital-human\models\CosyVoice \
  --weights-dir D:\work_place\lite-digital-human\models\CosyVoice\pretrained_models\CosyVoice-300M-SFT \
  --mode sft \
  --spk-id 中文女 \
  --text "你好，欢迎来到本地数字人 Demo。" \
  --out D:\work_place\lite-digital-human\outputs\cosyvoice-test.wav
```

如果你有零样本音色素材，可以改成：

```powershell
python scripts/cosyvoice_bridge.py \
  --repo-dir D:\work_place\lite-digital-human\models\CosyVoice \
  --weights-dir D:\work_place\lite-digital-human\models\CosyVoice\pretrained_models\CosyVoice-300M-SFT \
  --mode zero_shot \
  --prompt-text "这是一段参考文本。" \
  --prompt-wav D:\work_place\lite-digital-human\assets\prompt.wav \
  --text "现在开始说目标文案。" \
  --out D:\work_place\lite-digital-human\outputs\cosyvoice-zero-shot.wav
```

## API

- `POST /api/speak`
- `POST /api/stop`
- `GET /api/status?job_id=...`
- `GET /api/jobs`
- `GET /api/metrics`

## 当前 P0 进展

- 已完成模型路径发现与基础配置层
- 已完成 `CosyVoice` 的真实桥接脚本和权重发现逻辑
- 已完成 `MuseTalk` / `Wav2Lip` 的可插拔适配骨架
- 已完成 `TTS / 口型合成 / 最终编码` 三阶段任务生命周期
- 接下来重点是把真实模型权重放进本地环境并跑通一轮实际验证

## 后续方向

1. 把 `CosyVoice` 在真实权重环境里跑通并固化参数
2. 把 `MuseTalk` / `Wav2Lip` 接成真实口型驱动后端
3. 把任务状态改成更细的流式进度
4. 再补 OBS / FFmpeg 推流和录制链路

### 补充说明

- `scripts/cosyvoice_bridge.py` 现在会优先尝试官方 CosyVoice 常见的模型构造参数组合，再回退到默认构造，方便不同版本仓库和权重目录直接对接。
- 当前项目已经把真实 CosyVoice 的接入路径和本地 demo 回退路径分开了：只要本地放入官方仓库与权重，TTS 后端就会优先走真实推理。


### 当前状态补充

- `models/CosyVoice` 已经克隆官方仓库。
- `models/CosyVoice/pretrained_models/CosyVoice-300M-SFT` 已经下载并完成 LFS checkout。
- 下一步是先补全 CosyVoice 的 Python 依赖，然后再做一次真实合成验证。


### 现状说明

- 已经拉到 CosyVoice 官方仓库和 `CosyVoice-300M-SFT` 权重。
- 已经尝试真实 CosyVoice 合成，但还需要补全 `hyperpyyaml` 等 Python 依赖。


## 最新进展（0.0.7）

- 已在本地真实跑通官方 `CosyVoice-300M-SFT` 的 `sft` 推理，不再只是桥接骨架。
- `scripts/cosyvoice_bridge.py` 已可直接产出真实语音文件：`outputs/cosyvoice-check.wav`。
- 项目内联调也已验证通过：`scripts/smoke_demo.py` 会优先命中真实 `CosyVoice`，然后继续走本地 `demo-preview` 视频兜底。
- 当前项目状态可以概括为：`真实 CosyVoice TTS` 已接通，`真实 MuseTalk / Wav2Lip` 仍待接入。

### 当前推荐验证命令

```powershell
python scripts/cosyvoice_bridge.py --repo-dir models/CosyVoice --weights-dir models/CosyVoice/pretrained_models/CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs/cosyvoice-check.wav
```

```powershell
python scripts/smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"
```

### 当前已知说明

- 真实 `CosyVoice` 链路目前依赖仓库内的一组本地最小兼容层，目的是先把 P0 本地 demo 跑通。
- 下一步建议优先整理这些兼容层，尽量替换成正式依赖安装方案，降低后续接入 `MuseTalk` / `Wav2Lip` 时的维护成本。


## 最新进展（0.0.8）

- 已继续收敛 `CosyVoice` 的临时兼容层，真实 `sft` 启动不再绑定 `pyarrow`、`pyworld`、`modelscope`、`tqdm`。
- 部分训练/工具链依赖已经改成惰性加载，模型初始化更接近正式依赖优先的方案。
- 真实 `CosyVoice` 和项目内联调都还在保持通过，当前可继续围绕剩余依赖做更细的清理。

### 当前变化

- `pyarrow` / `pyworld` 已从仓库根目录删除。
- `modelscope` / `tqdm` 也已从仓库根目录删除，并由代码中的可选入口替代。
- `onnxruntime` / `inflect` / `whisper` / `torchaudio` 在前端里已改成延迟初始化。

### 当前建议命令

```powershell
python scripts/cosyvoice_bridge.py --repo-dir models/CosyVoice --weights-dir models/CosyVoice/pretrained_models/CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs/cosyvoice-check.wav
```

```powershell
python scripts/smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"
```


## 最新进展（0.0.9）

- 现在 `CosyVoice` 已经优先使用正式依赖，不再依赖仓库根目录那批本地同名替身。
- 真实 `CosyVoice-300M-SFT` `sft` 跑通后，`scripts/smoke_demo.py` 也继续保持通过。
- Hugging Face 缓存已改到项目目录内，减少默认用户缓存目录带来的麻烦。

### 当前变化

- 正式依赖已经通过清华镜像 + Clash 代理安装完成。
- 仓库根目录里的多数临时兼容层已经删除，导入行为回到官方包。
- 现在剩下的主要是少量 vendor 级小补丁，后面还能继续收敛。

### 当前建议命令

```powershell
python scripts/cosyvoice_bridge.py --repo-dir models/CosyVoice --weights-dir models/CosyVoice/pretrained_models/CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs/cosyvoice-check.wav
```

```powershell
python scripts/smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"
```


## 最新进展（0.1.0）

- `CosyVoice` 已经切换到正式依赖驱动，真实 `sft` 和项目内联调都继续通过。
- 仓库根目录里那批临时同名替身已经大幅减少，当前只剩少量 vendor 级便利补丁。
- Hugging Face 缓存已固定在项目目录内，能减少默认用户缓存目录带来的问题。

### 当前变化

- 真实合成验证仍然可直接运行。
- `scripts/cosyvoice_bridge.py` 现在只保留最小的运行时补丁。
- 后续优先事项已经可以明确转向 `MuseTalk` 和 `Wav2Lip`。

### 当前建议命令

```powershell
python scripts/cosyvoice_bridge.py --repo-dir models/CosyVoice --weights-dir models/CosyVoice/pretrained_models/CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs/cosyvoice-check.wav
```

```powershell
python scripts/smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"
```


## 最新进展（0.1.1）

- 我刚刚重新复测了真实 `CosyVoice` 合成链路和项目内联调链路，当前都继续通过。
- 现在可以继续放心沿着真实模型接入方向推进，不需要再依赖仓库根目录的临时同名替身。
- 这次复测没有引入新的临时兼容层，依然保持“正式依赖优先”的状态。

### 当前变化

- `scripts/cosyvoice_bridge.py` 的真实合成命令仍然可直接运行。
- `scripts/smoke_demo.py` 的项目内联调命令仍然可直接运行。
- 后续工作重点仍然是 `MuseTalk` 和 `Wav2Lip`。

### 当前建议命令

```powershell
python scripts/cosyvoice_bridge.py --repo-dir models/CosyVoice --weights-dir models/CosyVoice/pretrained_models/CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs/cosyvoice-check-docs.wav
```

```powershell
python scripts/smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"
```
