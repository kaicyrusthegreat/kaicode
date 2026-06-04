# Antigravity Logs — KaiCode Development

## Session: 2026-06-04 — KaiCode v2.0.0 Upgrade & Testing

### Changes Made

---

#### 1. Fixed startup crash (from previous session)
- **File**: `kaicode/providers/__init__.py`
- **Issue**: Unconditional `CyrusAIProvider` import caused `ModuleNotFoundError`
- **Fix**: Lazy loading with `try/except` inside `get_provider()`

---

#### 2. New Capabilities — Phase 1

##### New Files Created:
- **`kaicode/tools/keyboard_mouse_tools.py`** — Keyboard/mouse control via `pyautogui`
  - `type_text(text)` — Type text using keyboard
  - `key_press(keys)` — Press key combos (cmd+c, ctrl+z, etc.)
  - `mouse_click(x, y)` — Click at screen coordinates
  - `screenshot(path)` — Take screenshot
  - All have FAILSAFE enabled and safety pauses

- **`kaicode/tools/web_search_tools.py`** — Web search via DuckDuckGo
  - `web_search(query)` — Search the web, returns titles/URLs/snippets
  - Uses `httpx` (no API key needed)
  - Includes fallback regex extractor

##### Modified Files:
- **`kaicode/tools/registry.py`** — Registered all 5 new tools with definitions
- **`kaicode/app.py`** — Added trigger keywords for new tools in `_select_tools()`
- **`kaicode/project_detector.py`** — Updated system prompt with new tools listing
- **`kaicode/pyproject.toml`** — Added `pyautogui>=0.9.54`, `beautifulsoup4>=4.12.0`

---

#### 3. Engine Hardening — Phase 2

- **Tool-call ID collision fix** — Replaced `hash()` with `uuid4().hex[:8]` (app.py)
- **Raised MAX_TOOL_ITERATIONS** — 10 → 25 (complex tasks hit the ceiling)
- **`<think>` tag stripping** — Reasoning models (qwen3, phi4) emit `<think>` tags; now stripped from display
- **git_diff added to `_select_tools()`** — Was in TOOL_DEFINITIONS but never selected
- **Per-model system prompt hints** — Model-specific instructions for qwen3, phi4, gemma, granite
- **Expanded `_needs_tools` regex** — Now catches: debug, open, script, code, program, function, class, module, fetch, download, deploy, click, type, screenshot
- **Text-based tool fallback** — Models without native tool support (phi4, gpt-oss) now get text-tool-call extraction instead of being blocked
- **web_search added to auto-approve list** — Read-only, safe

---

#### 4. Version Bump
- `1.3.0` → `2.0.0` in: pyproject.toml, theme.py, main.py

---

### Model Testing Results

| Model | Size | Tool Calling | FizzBuzz Test | Reasoning Test | Notes |
|---|---|---|---|---|---|
| **qwen3:8b** | 5.2 GB | ⭐ Native | ✅ PASS — created, ran, verified | ✅ PASS — 6,604 correct | **Best overall** — fast, accurate, verifies work |
| **qwen3:4b** | 2.5 GB | ⭐ Native | ✅ PASS — created, ran, verified | — | Incredible for 2.5GB model |
| **qwen2.5-coder:7b** | 4.7 GB | ⭐ Native | ✅ PASS — created, ran, verified | — | **Best for code** — code-specialized, fast |
| **gemma4:latest** | 9.6 GB | ⭐ Native | ✅ PASS — created file, syntax OK | — | Clean, concise output |
| **gemma3:4b** | 3.3 GB | ⭐ Native | ✅ PASS — created, ran, verified | — | Fast, reliable small model |
| **llama3.1:8b** | 4.9 GB | ⭐ Native | ✅ PASS — created file, syntax OK | — | Solid, reliable |
| **llama3.2:latest** | 2.0 GB | ⚠️ Weak | ⚠️ PARTIAL — wrote code in text, no tool call | — | Small model; tends to explain instead of act |
| **granite4:3b** | 2.1 GB | ⭐ Native | ✅ PASS — created, ran, verified | — | Impressive for 2.1GB; IBM Granite shines |
| **phi4:latest** | 9.1 GB | ❌ No native | ⚠️ PARTIAL — correct code but didn't invoke tool | — | No Ollama tool template; emits CLI-style commands |
| **gpt-oss:20b** | 13 GB | ❌ No native | ⚠️ PARTIAL — correct code but didn't invoke tool | — | No Ollama tool template; slow to load |

### Model Rankings (for KaiCode use)

1. 🥇 **qwen3:8b** — Best all-around. Fast reasoning, tool-calling, verification loop.
2. 🥈 **qwen2.5-coder:7b** — Best for pure coding. Code-specialized, reliable tools.
3. 🥉 **qwen3:4b** — Best bang-for-buck. Tiny (2.5GB) but full tool-calling + verification.
4. **granite4:3b** — Smallest model that works flawlessly. 2.1GB.
5. **gemma4:latest** — Reliable, clean output. Bigger (9.6GB).
6. **gemma3:4b** — Fast, compact Google model.
7. **llama3.1:8b** — Solid workhorse, reliable tool calls.
8. **llama3.2:latest** — Good for chat, weak on tool calling.
9. **phi4:latest** — Great reasoning but no native tool support.
10. **gpt-oss:20b** — Large, slow, no native tool support.

### Key Findings
- **8 out of 10 models** successfully use native tool calling via Ollama
- **phi4 and gpt-oss** lack Ollama tool templates — they need text-based fallback
- The `<think>` tag stripping works correctly for reasoning models (qwen3)
- Permission system works as expected across all models
- Syntax verification (py_compile) catches errors and feeds them back to model
- All models produced correct FizzBuzz code — the difference is tool usage

---

#### 5. Speed Optimization — Interactive Mode
- **File**: `kaicode/providers/ollama.py`
- **Issue**: Models felt slower in interactive mode vs one-shot mode
- **Root cause**: Ollama's default `keep_alive=5m` causes model unloading between prompts
- **Fixes applied**:
  - `keep_alive: "30m"` — keeps model loaded in RAM for 30 minutes (was 5m default)
  - `num_ctx: 4096` — smaller context window = faster inference for most tasks
- **Why one-shot seemed faster**: No REPL overhead, models were hot in RAM from sequential tests, tiny context

#### 6. Fixed greeting bug — model used `key_press` for "hi"
- **Files**: `app.py` (tightened `_select_tools` triggers), `project_detector.py` (system prompt rules 9+11)
- **Root cause**: Trigger word `"type"` was too broad — matched normal language
- **Fix**: Changed triggers to specific phrases: `"type text"`, `"click on"`, `"press key"`, etc.
- **System prompt**: Added rule 11 — "NEVER use keyboard tools unless explicitly asked"

---

#### 7. Model list ordering + default model change
- **Files**: `main.py`, `config.py`, `app.py`, `~/.kaicode/config.yaml`
- **Change**: `/model` picker now sorts models by test ranking (best first)
- **Default model**: `llama3.2` → `qwen3:8b` (our #1 ranked model)
- **Ranking**: qwen3:8b > qwen2.5-coder:7b > qwen3:4b > granite4:3b > gemma4 > gemma3:4b > llama3.1 > llama3.2 > phi4 > gpt-oss

---

*Logged by Antigravity IDE — 2026-06-04*

