# 更新记录

本文档记录项目的阶段性变化，方便后续追踪实现进展。

## [未发布]

### 新增

- 新增本地优先的数字人项目骨架。
- 新增零依赖开发服务器，可在不安装 FastAPI 的情况下直接运行 demo。
- 新增 FastAPI 入口，方便后续切换到更标准的 Web API 方案。
- 新增任务管理层，负责记录任务状态、耗时、输出路径和 manifest。
- 新增 TTS 适配层，包含 Windows 语音合成后端和合成兜底后端。
- 新增基于 `ffmpeg` 的本地预览视频生成器。
- 新增浏览器控制台，用于提交文案、查看任务状态和预览结果。
- 新增冒烟测试脚本，用于验证本地端到端链路。
- 新增项目基础目录：`assets/`、`models/`、`outputs/`、`scripts/`。

### 变更

- 将仓库从空壳状态改造成可运行的 demo 骨架。
- 更新了 README，使其与当前本地优先实现保持一致。
- 调整了服务入口，使其同时兼容 `python -m ...` 和直接执行文件两种启动方式。

### 验证

- `python -m py_compile models\CosyVoice\cosyvoice\cli\frontend.py models\CosyVoice\cosyvoice\cli\cosyvoice.py scripts\cosyvoice_bridge.py backend\tts.py` 通过。
- `python scripts\cosyvoice_bridge.py --repo-dir models\CosyVoice --weights-dir models\CosyVoice\pretrained_models\CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs\cosyvoice-check.wav` 通过。
- `python scripts\smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"` 通过。

### 说明

- 本次版本基于 `0.0.1` 基线继续追加，历史记录保持不删不改。
## 0.0.3

### 新增

- 新增真实 `CosyVoice` 桥接脚本 `scripts/cosyvoice_bridge.py`，可直接调用官方推理类并将流式输出写成标准 wav。
- 新增 CosyVoice 仓库与权重目录发现逻辑，支持 `models/CosyVoice` + `pretrained_models` 的本地布局。
- 新增 `sft` 与 `zero_shot` 两种 CosyVoice 运行模式的桥接参数约定。
- 新增 CosyVoice 真实后端优先级，只有在仓库和权重都可用时才会覆盖 demo 兜底。

### 变更

- 调整 TTS 后端选择顺序，优先使用真实 CosyVoice 桥接，再回退到其他路径。
- 更新运行时注册表，补充 CosyVoice 资源发现与状态摘要。
- 更新 README 和 TODO，补充 CosyVoice 官方仓库、权重目录和环境变量约定。

### 验证

- 语法检查通过。
- 现有冒烟测试仍保持可跑通。
- 在未配置真实 CosyVoice 仓库和权重的情况下，系统仍会自动回退到既有 demo 路径。

### 说明

- 这次版本基于 `0.0.2` 继续递增，历史记录保持只增不改。
- 真实 CosyVoice 需要你在本地放入官方仓库和权重后才能完成最终跑通验证。

## 0.0.4

### 新增

- `scripts/cosyvoice_bridge.py` 进一步补强了真实 CosyVoice 推理入口，对 `CosyVoice` / `CosyVoice2` 的常见构造参数做了兼容回退，提升不同版本仓库的可接入性。
- 真实 CosyVoice 接入路径继续保持“仓库 + 权重目录”双发现机制，便于在本地直接放入官方代码和 `pretrained_models` 后运行。

### 变更

- CosyVoice 桥接脚本在初始化模型时，会优先尝试官方常见参数组合，再回退到默认构造，减少版本差异带来的启动失败。
- 文档同步补充了当前桥接脚本的兼容策略，方便后续把真实权重接入本地环境。

### 验证

- `python -c "import glob, py_compile; ..."` 语法编译通过。
- `python scripts\smoke_demo.py` 冒烟测试继续通过，现有 demo 回退链路未受影响。

### 说明

- 本文件继续遵守“只增不改”的规则，历史版本内容保持不动。

## 0.0.5

### 新增

- ?????? ModelScope ??? `CosyVoice-300M-SFT` ?????? `models/CosyVoice/pretrained_models/CosyVoice-300M-SFT`?????????
- 真实 CosyVoice 接入链路现在具备“仓库 + 权重”双本地准备条件，后续可以直接做真实合成验证。

### 变更

- 文档中的 CosyVoice 状态更新为已完成仓库克隆和权重下载，只保留真实合成验证作为下一步。

### 验证

- `git lfs fetch origin --all` 成功拉取了 13 个 LFS 对象。
- `git lfs checkout` 成功把权重文件写回工作区。

### 说明

- 本次版本基于 `0.0.4` 继续递增，历史记录保持只增不改。

## 0.0.6

### 新增

- 已通过官方 ModelScope 仓库把 `CosyVoice-300M-SFT` 权重拉到本地 `models/CosyVoice/pretrained_models/CosyVoice-300M-SFT`，并确认校准完成。
- 已经进行一次真实 CosyVoice 合成尝试，确认走到了真实推理路径，但目前还缺少 `hyperpyyaml` 等依赖。

### 变更

- 文档中的 P0 进度更新为“权重已继续到位，真实合成等待依赖完善”。

### 验证

- `python scripts\cosyvoice_bridge.py --mode sft ...` 已跑到真实 CosyVoice 初始化，但因 `hyperpyyaml` 未安装而失败。
- 现有 demo 回退链路未受影响。

### 说明

- 本次版本基于 `0.0.5` 继续递增，历史记录保持只增不改。


## 0.0.7

### 新增

- 新增 `pyarrow`、`pyworld`、`lightning`、`diffusers`、`einops`、`conformer` 等最小运行时兼容层，用于在当前本地环境中拉起官方 `CosyVoice` 推理链路。
- 新增 `CosyVoice-300M-SFT` 的本地真实推理验证产物：`outputs/cosyvoice-check.wav`。
- 新增项目内联调验证产物：`outputs/d87a31605989/speech.wav` 与 `outputs/d87a31605989/preview.mp4`。

### 变更

- 重写 `scripts/cosyvoice_bridge.py`，修复脚本损坏问题，并补齐官方仓库、第三方依赖目录、`.mkl_bin` DLL 路径和流式写 wav 的真实桥接逻辑。
- 修正 `backend/tts.py` 中 `DHD_COSYVOICE_SPK_ID` 的默认值，改为留空并由桥接脚本自动优先选择 `中文女`。
- 增强本地 `omegaconf`、`numpy` 与 `Matcha-TTS` 兼容实现，使 `CosyVoice` 初始化可以继续穿过配置层、声码器层和数据管线导入阶段。

### 验证

- `python -m py_compile scripts\cosyvoice_bridge.py backend\ts.py omegaconf.py numpy\__init__.py` 通过。
- `python scripts\cosyvoice_bridge.py --repo-dir models\CosyVoice --weights-dir models\CosyVoice\pretrained_models\CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs\cosyvoice-check.wav` 通过，并生成真实音频文件。
- `python scripts\smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"` 通过，任务后端显示为 `cosyvoice -> demo-preview`。

### 说明

- 本次版本基于 `0.0.6` 继续递增，历史记录保持只增不改。
- 当前 P0 中“将官方 CosyVoice 仓库和权重在本地环境跑通一轮实际验证”已经完成，后续重心转向清理临时兼容层并接入真实 `MuseTalk` / `Wav2Lip`。


## 0.0.8

### 新增

- 将 `CosyVoice` 启动链路中的部分训练/工具依赖改成惰性加载，进一步减少了真实 `sft` 路径对临时兼容层的依赖。
- 删除了不再需要参与启动链路的本地替身：`pyarrow`、`pyworld`、`modelscope`、`tqdm`。

### 变更

- `models/CosyVoice/cosyvoice/dataset/processor.py`、`models/CosyVoice/cosyvoice/utils/file_utils.py`、`models/CosyVoice/cosyvoice/utils/onnx.py` 改成按需导入，避免训练期模块在模型初始化时提前报缺依赖。
- `models/CosyVoice/cosyvoice/cli/cosyvoice.py` 改成可选 `modelscope` / `tqdm` 入口，仓库已存在时不再强依赖下载器和进度条包。
- `models/CosyVoice/cosyvoice/cli/frontend.py` 改成延迟初始化 `onnxruntime`、`inflect`、`whisper`、`torchaudio` 相关能力，真实 `sft` 路径只保留必要加载。

### 验证

- `python -m py_compile models\CosyVoice\cosyvoice\cli\rontend.py models\CosyVoice\cosyvoice\cli\cosyvoice.py scripts\cosyvoice_bridge.py backend\ts.py` 通过。
- `python scripts\cosyvoice_bridge.py --repo-dir models\CosyVoice --weights-dir models\CosyVoice\pretrained_models\CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs\cosyvoice-check.wav` 通过。
- `python scripts\smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"` 通过。

### 说明

- 这轮继续沿用 `0.0.7` 之后的递增规则，历史内容保持只增不改。
- 之前尝试安装官方依赖时仍受到当前环境网络/代理限制，所以上述清理仍以本地代码收敛为主。



## 0.0.9

### 新增

- 通过清华镜像和 Clash 代理，成功把 `CosyVoice` 依赖链从临时兼容层迁移到正式包安装。
- 删除了仓库根目录下的大部分同名本地替身，让导入路径回到官方发行版：`numpy`、`omegaconf`、`hyperpyyaml`、`conformer`、`diffusers`、`einops`、`lightning`、`modelscope`、`scipy`、`sympy`、`torchaudio`、`whisper`、`transformers` 等。

### 变更

- 新增并安装了官方依赖：`hydra-core`、`HyperPyYAML`、`omegaconf`、`lightning`、`diffusers`、`einops`、`conformer`、`gdown`、`soundfile`、`librosa`、`inflect`、`modelscope`、`pyarrow`、`pyworld`、`torchaudio`、`onnxruntime`、`transformers`、`openai-whisper` 等。
- 清理了 `scripts/cosyvoice_bridge.py` 中为旧环境准备的 `torch.Tensor.numpy` / `torch.from_numpy` 兼容补丁，只保留必要的 checkpoint 兜底。
- 将 Hugging Face 缓存目录改到项目内，减少默认用户缓存目录的权限和路径问题。

### 验证

- `python -m pip download --no-deps -i https://pypi.tuna.tsinghua.edu.cn/simple hydra-core==1.3.2` 在正确代理配置下可成功下载。
- `python scripts\cosyvoice_bridge.py --repo-dir models\CosyVoice --weights-dir models\CosyVoice\pretrained_models\CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs\cosyvoice-check.wav` 通过。
- `python scripts\smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"` 通过。

### 说明

- 本次版本基于 `0.0.8` 继续递增，历史记录保持只增不改。
- 目前已经不再依赖仓库根目录下的大多数临时替身，后续只需要继续检查少量 vendor 级便利补丁是否还可以进一步收敛。


## 0.1.0

### 新增

- 正式依赖安装已完成，`CosyVoice` 真实链路现在优先使用官方包而不是仓库根目录的本地替身。
- Hugging Face 缓存目录已切到项目内 `.cache/huggingface`，减少默认用户缓存目录带来的环境差异。

### 变更

- `scripts/cosyvoice_bridge.py` 维持最小运行时补丁，仅保留必要的 checkpoint 兜底，不再保留旧环境用的 `torch.Tensor.numpy` / `torch.from_numpy` monkeypatch。
- 仓库根目录的大部分临时兼容层已删除，`CosyVoice` 启动路径回到官方发行版和正式依赖。
- `models/CosyVoice` 里的少量 vendor 级便利补丁仍保留，但已经不再阻塞真实 `sft` 推理与项目内联调。

### 验证

- `python -m py_compile scripts\cosyvoice_bridge.py backend\tts.py backend\manager.py backend\runtime.py backend\external.py backend\encoder.py backend\lipsync.py models\CosyVoice\cosyvoice\cli\frontend.py models\CosyVoice\cosyvoice\cli\cosyvoice.py models\CosyVoice\cosyvoice\dataset\processor.py models\CosyVoice\cosyvoice\utils\file_utils.py models\CosyVoice\cosyvoice\utils\onnx.py` 通过。
- `python -c "import hydra, hyperpyyaml, omegaconf, lightning, diffusers, einops, conformer, pyarrow, pyworld, onnxruntime, whisper, torchaudio, transformers, modelscope, inflect; print('imports-ok')"` 通过。
- `python scripts\cosyvoice_bridge.py --repo-dir models\CosyVoice --weights-dir models\CosyVoice\pretrained_models\CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs\cosyvoice-check.wav` 通过。
- `python scripts\smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"` 通过。

### 说明

- 本次版本基于 `0.0.9` 继续递增，历史记录保持只增不改。
- 当前项目状态已经从“临时兼容层驱动”切到“正式依赖驱动”，后续重心可以转向真实 `MuseTalk` / `Wav2Lip` 接入。


## 0.1.1

### 新增

- 本次复测确认，真实 `CosyVoice` 合成链路和项目内联调链路在当前工作区继续通过。

### 验证

- `python scripts\cosyvoice_bridge.py --repo-dir models\CosyVoice --weights-dir models\CosyVoice\pretrained_models\CosyVoice-300M-SFT --mode sft --text "你好，这是一次真实 CosyVoice 合成测试。" --out outputs\cosyvoice-check-docs.wav` 通过。
- `python scripts\smoke_demo.py --text "你好，这是项目内真实 CosyVoice 联调测试。"` 通过。

### 说明

- 本次版本基于 `0.1.0` 继续递增，历史记录保持只增不改。
- 当前可继续沿着真实 `MuseTalk` / `Wav2Lip` 接入方向推进。
