# Shanyi · 闪译

**划词即译，闪截即翻。** Windows 全局划词 + 截图 OCR 翻译工具，一个热键搞定，随按随走。

![shanyi](https://img.shields.io/badge/platform-Windows%2010%2F11-blue) ![deps](https://img.shields.io/badge/dependencies-0-brightgreen) ![license](https://img.shields.io/badge/license-MIT-green)

## 它解决什么问题

划词翻译工具很多，但大多数要么臃肿（常驻几百 MB），要么只能在特定应用里用。Shanyi 的取舍很简单：

- **全局热键，处处可用** —— 浏览器、PDF、IDE、聊天窗口，只要能选中文字就能译
- **Alt+O 截图 OCR** —— 文字选不中的场景（图片、扫描件、视频字幕）框一下就翻
- **零依赖** —— 纯 Python 标准库（ctypes/tkinter/urllib），无第三方包，内存 ~42MB
- **接入你自己的 AI 服务** —— 任何 OpenAI 兼容端点（vLLM/Ollama/OpenRouter/官方 API 均可）

## 快速开始

```bash
# 要求：Windows 10/11 + Python 3.11+（需自带 tkinter）
python main.py
```

首次运行会在 `%LOCALAPPDATA%\Shanyi\config.json` 生成默认配置，填入任意 OpenAI 兼容端点即可：

```json
{
  "cloud": {
    "base_url": "https://your-api.example.com/v1",
    "model": "your-chat-model",
    "ocr_model": "deepseek-ai/DeepSeek-OCR",
    "api_key": "sk-..."
  }
}
```

翻译方向自动判断：中文选区 → 译英；英文选区 → 译中。

OCR 功能需要一个视觉模型（兼容 OpenAI `image_url` 格式，如 `deepseek-ai/DeepSeek-OCR`）；不需要 OCR 的话可以不配，`Alt+T` 划词翻译照常工作。

## 快捷键

| 按键 | 功能 |
|---|---|
| `Alt+T` | 划词翻译（模拟复制，剪贴板自动还原） |
| `Alt+O` | 截图 OCR 翻译（框选区域） |
| `Ctrl+Alt+X` | 退出 |

所有热键可在 `config.json` 的 `hotkey_*` 段自定义（支持 CTRL/ALT/SHIFT/WIN 组合与字母、F1-F12）。

## 配置项

| 键 | 默认 | 说明 |
|---|---|---|
| `popup_seconds` | 10 | 译文弹窗自动关闭秒数（悬停暂停） |
| `max_chars` | 2000 | 单次翻译的选区长度上限 |
| `http_timeout` | 20 | 翻译请求超时（秒） |
| `ocr_min_side` | 64 | 框选区最小边长（过窄自动扩边） |
| `cloud.ocr_model` | DeepSeek-OCR | 视觉模型，需兼容 OpenAI `image_url` 格式 |

## 架构

```
main.py      入口：单实例互斥锁 + 装配
config.py    配置加载（%LOCALAPPDATA%\Shanyi\config.json）
winapi.py    ctypes 声明（restype/argtypes 集中管理）
capture.py   剪贴板取词 + GDI 截屏 + 纯 stdlib PNG 编码
api.py       OpenAI 兼容 API 调用（翻译 + OCR）
ui.py        DeepL 风深色弹窗 + 全屏框选遮罩
hotkeys.py   全局热键循环 + 工作线程
tests.py     纯逻辑单测（PNG 编码/区域扩边/热键解析）
```

单文件约 600 行，进程常驻内存 ~42MB（Python 解释器底噪），无依赖、无打包、无服务进程。

## 已知限制

- 仅 Windows（热键/剪贴板/GDI 均为 Win32 实现）
- 截图 OCR 依赖服务端部署视觉模型（如 DeepSeek-OCR）
- 终端类应用使用 `Ctrl+Shift+C` 复制，已自动识别处理

## License

MIT
