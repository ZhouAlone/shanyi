# Shanyi · 闪译

**划词即译，闪截即翻。** Windows 全局划词 + 截图 OCR 翻译工具，一个热键搞定，随按随走。

![shanyi](https://img.shields.io/badge/platform-Windows%2010%2F11-blue) ![deps](https://img.shields.io/badge/dependencies-0-brightgreen) ![license](https://img.shields.io/badge/license-MIT-green)

## ✨ 它解决什么问题

划词翻译工具很多，但大多数要么臃肿（常驻几百 MB），要么只能在特定应用里用。Shanyi 的取舍很简单：

- **全局热键，处处可用** —— 浏览器、PDF、IDE、聊天窗口，只要能选中文字就能译
- **Alt+O 截图 OCR** —— 文字选不中的场景（图片、扫描件、视频字幕）框一下就翻
- **零依赖** —— 纯 Python 标准库（ctypes/tkinter/urllib），无第三方包，内存 ~45MB
- **接入你自己的 AI 服务** —— 任何 OpenAI 兼容端点（vLLM/Ollama/OpenRouter/官方 API 均可）
- **交互细节在线** —— DeepL 风深色弹窗、悬停暂停关闭、拖动跟手、📋 一键复制（✓ 反馈）、剪贴板自动还原

## 💾 安装（普通用户）

> [!TIP]
> 全程不需要安装 Python，不需要任何运行环境。

1. 打开 [Releases 页面](../../releases/latest)
2. 下载 **`Shanyi-win64.zip`**（注意：**不要**下 "Source code"，那是源码压缩包，不是软件）
3. 右键解压到任意位置（比如 `D:\Shanyi\`）
4. 进入解压出的 `Shanyi` 文件夹，**双击 `Shanyi.exe`**
5. 屏幕右下角弹出气泡「Shanyi 已启动」，托盘区出现绿色「闪」字图标 —— 安装成功

> 💡 托盘图标可能收在任务栏右下角的 **^（显示隐藏的图标）** 里，可拖到常驻区。
>
> 💡 想开机自启：`Win+R` 输入 `shell:startup` 回车，把 `Shanyi.exe` 的**快捷方式**放进打开的文件夹。
>
> 💡 完整卸载：托盘右键退出后，删掉整个 `Shanyi` 文件夹 + `%LOCALAPPDATA%\Shanyi` 文件夹，无残留。

## ⚙️ 首次配置（必做一次）

Shanyi 本身不自带翻译引擎，它把文字发给**任意 OpenAI 兼容的接口**完成翻译。所以首次使用要告诉它你的接口在哪：

1. 双击运行一次 Shanyi（自动生成配置文件）
2. 打开配置文件：资源管理器地址栏粘贴 `%LOCALAPPDATA%\Shanyi` 回车，用记事本打开 `config.json`
3. 填三项（以 OpenRouter 为例）：

```json
{
  "cloud": {
    "base_url": "https://openrouter.ai/api/v1",
    "model": "google/gemini-2.0-flash-exp:free",
    "ocr_model": "deepseek-ai/DeepSeek-OCR",
    "api_key": "sk-or-你的密钥",
    "api_key_env": ""
  }
}
```

| 字段 | 填什么 |
|---|---|
| `base_url` | AI 服务地址，以 `/v1` 结尾（OpenAI 官方、OpenRouter、本地 Ollama/vLLM 都行） |
| `model` | 对话模型名（用服务方模型列表里的名字） |
| `api_key` | 该服务的密钥 |
| `api_key_env` | 可选。填环境变量名（如 `MY_KEY`），密钥放环境变量而不是文件里 |

4. 保存，重启 Shanyi（托盘右键退出 → 重新双击）

> [!NOTE]
> 翻译方向自动判断：中文选区 → 译英文；英文选区 → 译中文，无需配置。
>
> OCR 是进阶功能：`ocr_model` 需要服务端部署了视觉模型（如 DeepSeek-OCR）。不配不影响 `Alt+T` 划词翻译。

### 🧠 模型怎么选

翻译是"简单高频"任务，选模型的口诀：**翻译要快不要贵，OCR 必须带眼睛**。

**`model`（翻译模型）——选轻快型对话模型**

翻译是低难度任务，小模型足够，重点看**响应速度**：

| 档位 | 推荐 | 说明 |
|---|---|---|
| 💰 免费/低价 | `gemini-2.0-flash`、`deepseek-chat`、`gpt-4o-mini` | 日常使用性价比最高 |
| 🏠 本地部署 | Ollama 的 `qwen2.5:7b`、`glm4:9b` 等 | 完全离线，速度取决于显卡 |
| ⚠️ 避开 | 推理/思考型模型（o1、R1、带 thinking 的） | 翻译用不上深度思考，又慢又贵，弹窗等半天才出结果 |

**`ocr_model`（OCR 模型）**：

- 必须是**视觉模型**（能看图），且服务端支持 OpenAI `image_url` 格式
- 已验证：`deepseek-ai/DeepSeek-OCR`；其他可选 `qwen2.5-vl` 系列、`gpt-4o-mini` 等
- 没部署视觉模型？留空/不配即可，不影响划词翻译

> [!IMPORTANT]
> 模型名必须与你的服务方模型列表里的名字**一字不差**。填错会在弹窗里报 404/400。
> 验证方法：浏览器打开 `你的base_url/models`（多数服务支持），能看到可用模型清单。


## 🎮 使用

| 按键 | 功能 |
|---|---|
| `Alt+T` | **划词翻译**：选中一段文字 → 按 `Alt+T` → 弹出译文 |
| `Alt+E` | **解释代码/术语**：选中参数名、代码或文档句子 → 中文讲解其作用（编程阅读场景） |
| `Alt+O` | **截图 OCR**：按 `Alt+O` → 框选屏幕区域 → 识别并翻译图中文字 |
| `Ctrl+Alt+X` | 退出（或托盘图标右键 → 退出） |

> 💡 翻译 vs 解释怎么选：看文档想"这句什么意思"用 `Alt+E`（会讲作用和场景）；单纯要译文用 `Alt+T`。解释弹窗带「💡」前缀，一眼区分。

**弹窗交互**：

- 鼠标悬停弹窗 → 暂停自动关闭，从容阅读
- 点 📋 → 复制译文（按钮变 ✓）
- 按住弹窗拖动 → 跟手
- 10 秒无操作自动消失

**常见问题排查**：

| 现象 | 原因与解决 |
|---|---|
| 双击 exe 没反应 | 已有实例在运行（看右下角托盘）。想重开：先托盘右键退出 |
| 报 401 / 403 | API key 错误或过期，检查 `config.json` |
| 报连接失败 | `base_url` 写错（要 `/v1` 结尾），或该服务不在线 |
| Alt+T 没反应 | 个别游戏/管理员权限窗口会拦截全局热键，属系统限制；先点一下普通窗口再试 |
| OCR 识别乱码 | 框选区太小或字太密，框大一点 |
| 双开没反应 | 设计如此：单实例防重复，看托盘 |

## 📋 全部配置项

| 键 | 默认 | 说明 |
|---|---|---|
| `hotkey_translate` | ALT+T | 划词翻译热键 |
| `hotkey_ocr` | ALT+O | 截图 OCR 热键 |
| `hotkey_quit` | CTRL+ALT+X | 退出热键 |
| `popup_seconds` | 10 | 弹窗自动关闭秒数（悬停暂停） |
| `max_chars` | 2000 | 单次翻译选区长度上限 |
| `http_timeout` | 20 | 翻译请求超时（秒） |
| `ocr_min_side` | 64 | 框选区最小边长（过窄自动扩边） |

热键自定义写法（`mods` 支持 CTRL/ALT/SHIFT/WIN 任意组合，`key` 支持字母和 F1~F12）：

```json
"hotkey_translate": {"mods": ["CTRL", "SHIFT"], "key": "T"}
```

## 🔒 隐私与安全

- **数据去向**：选中的文字/截图 → 你配置的 AI 端点 → 译文返回。仅此而已，无遥测、无第三方中转
- **密钥安全**：`config.json` 只在你本机；用 `api_key_env` 可让密钥只存在于环境变量
- **日志**：仅本地 `%LOCALAPPDATA%\Shanyi\shanyi.log`，用于排错

## 🗂 架构

```
main.py      入口：单实例互斥锁 + 装配
config.py    配置加载（%LOCALAPPDATA%\Shanyi\config.json）
winapi.py    ctypes 声明（restype/argtypes 集中管理）
capture.py   剪贴板取词 + GDI 截屏 + 纯 stdlib PNG 编码
api.py       OpenAI 兼容 API 调用（翻译 + OCR）
ui.py        DeepL 风深色弹窗 + 全屏框选遮罩
hotkeys.py   全局热键循环 + 工作线程
tray.py      系统托盘（纯 ctypes Shell_NotifyIconW）
tests.py     纯逻辑单测（PNG 编码/区域扩边/热键解析）
```

源码约 900 行；进程常驻内存 ~45MB（Python 解释器底噪）；无服务进程。

## 🛠️ 开发

```bash
uv sync                        # 开发环境（含 pyinstaller/pyflakes）
uv run python tests.py         # 单测
uv run pyflakes main.py config.py winapi.py capture.py api.py ui.py hotkeys.py tray.py tests.py
uv run pyinstaller shanyi.spec --noconfirm   # 本地打包
```

## 🚀 发布（维护者）

推送 `v*` 标签即触发 GitHub Actions：单测 + Lint → PyInstaller 打包 → 冒烟测试 → 产物附到 Release。

```bash
git tag -a v0.1.1 -m "说明这版改了啥"
git push origin v0.1.1
```

## 📌 已知限制

- 仅 Windows（热键/剪贴板/GDI 均为 Win32 实现）
- 截图 OCR 依赖服务端部署视觉模型（如 DeepSeek-OCR）
- 终端类应用使用 `Ctrl+Shift+C` 复制，已自动识别处理

## License

MIT
