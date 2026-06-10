# KaiCode

**Terminal AI coding assistant supporting multiple AI providers.**

*Current version: 2.2.0*

```
 ██╗  ██╗ █████╗ ██╗ ██████╗ ██████╗ ██████╗ ███████╗
 ██║ ██╔╝██╔══██╗██║██╔════╝██╔═══██╗██╔══██╗██╔════╝
 █████╔╝ ███████║██║██║     ██║   ██║██║  ██║█████╗
 ██╔═██╗ ██╔══██║██║██║     ██║   ██║██║  ██║██╔══╝
 ██║  ██╗██║  ██║██║╚██████╗╚██████╔╝██████╔╝███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
                                             by Kai Cyrus
```

## Why KaiCode?

- **Local-first** — runs great on Ollama models as small as 3–8 B, with tool-calling hardened specifically for weak local models (text-based tool-call fallback, JSON repair, stuck-loop guards)
- **Provider freedom** — switch between local and cloud models mid-session with one command
- **Controlled autonomy** — every file write shows a diff *before* it's applied; plans are confirmed before execution; `/undo` reverts any agent change
- **Lightweight & hackable** — plain Python, no daemon, no account, no telemetry

## Features

- **Multiple AI providers**: Ollama (local), OpenAI AI, OpenAI, Groq, any OpenAI-compatible API, and CyruSagO (experimental self-improving core)
- **Goal mode** *(new in 2.2)*: `kaicode --goal "make tests pass"` — works autonomously, runs the test suite, feeds failures back, and retries until green
- **AI commit messages** *(new in 2.2)*: `/commit` generates a conventional-commit message from your diff and commits after approval
- **Token & cost tracking** *(new in 2.2)*: live token count and estimated API cost in the status bar and `/status` (local models are free)
- **Agentic tools**: ~20 tools — file editing with diff previews, code search, AST symbol lookup, repo map, shell commands, git, test runner, web search/fetch, GUI automation
- **Review-before-apply**: diffs and new file contents are shown before you approve each write; per-tool or session-wide allow rules
- **Checkpoints**: `/undo`, `/redo`, and `/changes` for every file the agent touches
- **Plan mode**: real multi-step plans are shown and confirmed before execution
- **Project memory**: the agent saves notes per project (`/memory`); `/init` scaffolds a `KAICODE.md` instructions file
- **Smart context**: auto-detects project type (Flutter, Python, Node, Rust, Go, and more), auto-loads relevant files, supports explicit `@path` mentions
- **Syntax verification**: every saved file is syntax-checked and errors are fed back to the model automatically
- **Session management**: save and resume conversations
- **Project config**: per-project `.kaicode` override file

## Installation

```bash
pip install kaicode
```

Or from source:

```bash
git clone https://github.com/kaicyrusdgreat/kaicode
cd kaicode
pip install -e .
```

## Quick Start

```bash
# Launch (defaults to the CyruSagO provider, falling back to local Ollama)
kaicode

# Use local Ollama explicitly
kaicode --provider ollama

# Use OpenAI AI
OPENAI_API_KEY=sk-ant-... kaicode --provider openai

# Use OpenAI
OPENAI_API_KEY=sk-... kaicode --provider openai --model gpt-4o

# Use Groq
GROQ_API_KEY=gsk_... kaicode --provider groq

# One-shot mode
kaicode "explain this codebase"

# Goal mode — iterate autonomously until the test suite passes
kaicode --goal "make tests pass"
kaicode --goal "fix the failing login tests" --attempts 8

# Load a saved session
kaicode --session mysession
```

## Configuration

Global config lives at `~/.kaicode/config.yaml`:

```yaml
default_provider: ollama

providers:
  ollama:
    base_url: http://localhost:11434
    default_model: qwen3:8b

  openai:
    api_key: sk-ant-your-key-here
    default_model: model-sonnet-4-6

  openai:
    api_key: sk-your-key-here
    default_model: gpt-4o

  groq:
    api_key: gsk_your-key-here
    default_model: llama-3.1-70b-versatile

  openai_compat:
    base_url: http://localhost:1234/v1   # LM Studio, vLLM, LocalAI, etc.
    default_model: local-model
```

**Per-project config** (`.kaicode` in project root):

```yaml
default_provider: openai
system_prompt: "This is a Flutter app using Riverpod for state management."
```

**Environment variables** (override config):

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GROQ_API_KEY` | Groq API key |
| `KAICODE_DEFAULT_PROVIDER` | Default provider name |

## Commands

| Command | Description |
|---|---|
| `/model [name]` | Switch model (shows ranked picker if no name) |
| `/provider [name]` | Switch provider |
| `/init [--force]` | Generate a `KAICODE.md` with project instructions |
| `/commit` | AI-generated commit message for current changes |
| `/undo` | Revert the last file change the agent made |
| `/redo` | Re-apply the last undone change |
| `/changes` | List file changes made this session |
| `/diff` | Show the last applied diff |
| `/memory` | Show project memory (`/memory clear` to reset) |
| `/context` | Show auto-detected context files |
| `/clear` | Clear conversation history |
| `/save [name]` | Save current session |
| `/load <name>` | Load a saved session |
| `/sessions` | List saved sessions |
| `/status` | Show tokens, estimated cost, model, provider |
| `/help` | Show all commands |
| `/quit` | Exit |

**Tips:** `@path/to/file` includes a specific file as context · `!command` runs a shell command inline · `ESC` cancels generation.

## Supported Providers

| Provider | Models | Notes |
|---|---|---|
| **Ollama** | Any local model | Requires `ollama serve` — free |
| **OpenAI** | AI Opus, Sonnet, Haiku | Needs API key |
| **OpenAI** | GPT-4o, GPT-4-turbo, o1, etc. | Needs API key |
| **Groq** | Llama 3, Mixtral, Gemma | Needs API key (fast!) |
| **OpenAI-compat** | Any | LM Studio, vLLM, LocalAI, etc. |
| **CyruSagO** | cyrusago | Experimental self-improving core (local) |

## Agent Tools

KaiCode can use these tools autonomously (writes and command execution always ask for permission first; read-only tools run automatically):

**Files & code**

- **`read_file`** — read file contents with line ranges
- **`edit_file`** — exact string replacement, with a diff preview before applying
- **`create_file`** — create or overwrite files (contents previewed first)
- **`create_directory`** — create folders
- **`list_files`** — browse directory trees
- **`search_files`** — search code with regex support
- **`grep_ast`** — find function/class definitions via AST analysis
- **`repo_map`** — compact map of every source file with its symbols

**Execution & verification**

- **`run_command`** — execute shell commands (dangerous patterns are blocked)
- **`run_tests`** — auto-detects the test runner (pytest, npm test, flutter test, go test, cargo test, …)

**Git**

- **`git_status`** / **`git_diff`** / **`git_commit`**

**Web & memory**

- **`web_search`** — search the web
- **`web_fetch`** — fetch a URL's content
- **`update_memory`** — persistent per-project notes

**GUI automation**

- **`type_text`** / **`key_press`** / **`mouse_click`** / **`screenshot`**

## Safety

- Every file write shows a diff (or full new contents) **before** the permission prompt
- Dangerous shell patterns (`rm -rf /`, `mkfs`, `dd if=`, fork bombs) are blocked outright
- Read-only tools run without prompts; anything state-changing asks first — approve once, always-allow a tool, or allow all for the session
- Each change is checkpointed: `/undo` restores the exact previous file state
- Saved files are syntax-checked (Python, JS/TS, Dart, Go, Ruby, shell) and errors are fed back to the model

## Project Detection

KaiCode auto-detects your project type and loads relevant context:

- Flutter / Dart
- Python (package, Django, FastAPI)
- Node.js / React / Next.js
- Rust, Go, Java, Kotlin, Swift
- Ruby, PHP, Elixir
- Docker, Terraform

---

*by Kai Cyrus*
