#!/usr/bin/env python3
"""apply_openrouter.py — idempotent patcher for companion-emergence.

adds OpenRouterProvider class to brain/bridge/provider.py and wires it into
the get_provider() factory under the name "openrouter". also re-applies the
OllamaProvider.chat_stream → _chat_stream_unstreamable rename (so the bridge
falls back to chat() for ollama, which has the correct signature).

idempotent: running multiple times is safe. detects existing patches by name
and skips re-injection.

usage:
    python apply_openrouter.py
    # by default targets the bundled python-runtime install:
    # %LOCALAPPDATA%\Companion Emergence\python-runtime\Lib\site-packages\brain\bridge\provider.py
    # override with PROVIDER_PY env var if needed.

backup: writes provider.py.openrouter-patch.bak before any edits.

after running:
    nell supervisor restart --persona cali
    # then set OPENROUTER_API_KEY env var + change persona_config.json:
    #   "provider": "openrouter"
    #   "model": "deepseek/deepseek-chat"   (or other openrouter model id)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


# ── locate provider.py ────────────────────────────────────────────────────────
def _default_provider_py() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Companion Emergence" / "python-runtime" / "Lib" / "site-packages" / "brain" / "bridge" / "provider.py"
    # mac / linux: best-effort, user can override via env
    home = Path.home()
    candidates = [
        home / ".local" / "share" / "companion-emergence" / "python-runtime" / "lib" / "site-packages" / "brain" / "bridge" / "provider.py",
        home / "Library" / "Application Support" / "companion-emergence" / "python-runtime" / "lib" / "site-packages" / "brain" / "bridge" / "provider.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


PROVIDER_PY = Path(os.environ.get("PROVIDER_PY") or _default_provider_py())
PERSONA_CONFIG_PY = PROVIDER_PY.parent.parent / "persona_config.py"


# ── OpenRouterProvider source (inserted before "# Factory" section) ──────────
OPENROUTER_CLASS = '''
class OpenRouterProvider(LLMProvider):
    """OpenRouter integration over httpx (OpenAI-compatible API).

    Routes chat completions through openrouter.ai. Supports any model in
    OpenRouter's catalogue — deepseek r1/v3, GLM, hermes-3, claude, gpt, etc.
    API key read from OPENROUTER_API_KEY env var by default (or passed
    explicitly to __init__).

    Streaming uses SSE format. chat_stream yields proper ChatStreamEvent
    objects (TextDelta / StreamDone / StreamError) so the bridge consumer
    pattern in brain/bridge/server.py works correctly — unlike OllamaProvider
    which yields raw strings (and has chat_stream renamed to a hidden form
    so the bridge falls back to chat()).

    Tool-calling: full OpenAI-compatible function-calling. Tool deltas in
    the stream are assembled and surfaced both via mid-stream events (where
    supported by the provider) and via StreamDone metadata.
    """

    def __init__(
        self,
        model: str = "deepseek/deepseek-chat",
        api_key: str | None = None,
        host: str = "https://openrouter.ai/api/v1",
        timeout: float = 300.0,
        http_referer: str | None = None,
        x_title: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._host = host.rstrip("/")
        self._timeout = timeout
        self._http_referer = http_referer or os.environ.get("OPENROUTER_REFERER", "")
        self._x_title = x_title or os.environ.get("OPENROUTER_TITLE", "companion-emergence")

    def name(self) -> str:
        return f"openrouter:{self._model}"

    def healthy(self) -> bool:
        """GET /models — True if openrouter is reachable + key is valid."""
        if not self._api_key:
            return False
        try:
            r = httpx.get(
                f"{self._host}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=5.0,
            )
            return r.status_code == 200
        except httpx.RequestError:
            return False

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._http_referer:
            h["HTTP-Referer"] = self._http_referer
        if self._x_title:
            h["X-Title"] = self._x_title
        return h

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ChatResponse:
        """POST /chat/completions and parse the structured (non-streaming) response."""
        # Diagnostic: log message sizes so we can verify voice.md is being passed.
        try:
            _msg_chars = sum(len(m.content_text()) for m in messages)
            _sys_chars = sum(
                len(m.content_text()) for m in messages if m.role == "system"
            )
            logger.info(
                "openrouter chat: model=%s, %d messages, %d total chars (%d in system), %d tools",
                self._model,
                len(messages),
                _msg_chars,
                _sys_chars,
                len(tools) if tools else 0,
            )
        except Exception:  # noqa: BLE001
            pass

        if not self._api_key:
            raise ProviderError(
                "openrouter_auth",
                "OPENROUTER_API_KEY is not set",
            )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        if options:
            for key, value in options.items():
                if key in _PROVIDER_CONTEXT_OPTION_KEYS:
                    continue
                payload[key] = value

        url = f"{self._host}/chat/completions"
        try:
            resp = httpx.post(
                url, json=payload, headers=self._headers(), timeout=self._timeout
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                "openrouter_http",
                f"{exc.response.status_code}: {exc.response.text[:200]}",
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError("openrouter_request", str(exc)) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderError("openrouter_parse", f"invalid json: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("openrouter_parse", "no choices in response")
        msg = choices[0].get("message") or {}
        content: str = msg.get("content") or ""
        raw_tool_calls: list[dict[str, Any]] = msg.get("tool_calls") or []

        parsed_tool_calls: list[ToolCall] = []
        for tc_dict in raw_tool_calls:
            try:
                parsed_tool_calls.append(ToolCall.from_provider_dict(tc_dict))
            except ValueError as exc:
                raise ProviderError(
                    "openrouter_parse",
                    f"malformed tool_call in response: {exc}",
                ) from exc

        return ChatResponse(
            content=_truncate_at_role_leak(content),
            tool_calls=tuple(parsed_tool_calls),
            raw=data,
        )

    def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> Iterator[ChatStreamEvent]:
        """Stream /chat/completions via SSE.

        Yields ChatStreamEvent variants (TextDelta, StreamDone, StreamError) —
        wire-compatible with the bridge server's chat_stream consumer at
        brain/bridge/server.py:358. Tool-call deltas are accumulated and
        surfaced in the terminal StreamDone metadata; callers needing
        actionable ToolCall objects can use chat() instead.
        """
        # Diagnostic: log message sizes so we can verify voice.md is being passed.
        try:
            _msg_chars = sum(len(m.content_text()) for m in messages)
            _sys_chars = sum(
                len(m.content_text()) for m in messages if m.role == "system"
            )
            logger.info(
                "openrouter chat_stream: model=%s, %d messages, %d total chars (%d in system), %d tools",
                self._model,
                len(messages),
                _msg_chars,
                _sys_chars,
                len(tools) if tools else 0,
            )
        except Exception:  # noqa: BLE001
            pass

        if not self._api_key:
            yield StreamError(
                stage="openrouter_auth",
                detail="OPENROUTER_API_KEY is not set",
            )
            return

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
        if options:
            for key, value in options.items():
                if key in _PROVIDER_CONTEXT_OPTION_KEYS:
                    continue
                payload[key] = value

        url = f"{self._host}/chat/completions"
        accumulated_content: list[str] = []
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None

        try:
            with httpx.stream(
                "POST",
                url,
                json=payload,
                headers=self._headers(),
                timeout=self._timeout,
            ) as resp:
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    body = exc.response.read().decode("utf-8", errors="replace")
                    yield StreamError(
                        stage="openrouter_http",
                        detail=f"{exc.response.status_code}: {body[:200]}",
                    )
                    return

                for raw_line in resp.iter_lines():
                    line = (
                        raw_line.strip()
                        if isinstance(raw_line, str)
                        else raw_line.decode("utf-8", errors="replace").strip()
                    )
                    if not line:
                        continue
                    if line.startswith(":"):
                        # SSE comment / keepalive — ignore.
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        frame = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = frame.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}

                    text_chunk = delta.get("content")
                    if text_chunk:
                        accumulated_content.append(text_chunk)
                        yield TextDelta(text=text_chunk)

                    delta_tool_calls = delta.get("tool_calls") or []
                    for tc_delta in delta_tool_calls:
                        idx = tc_delta.get("index", 0)
                        slot = accumulated_tool_calls.setdefault(
                            idx,
                            {"id": "", "function": {"name": "", "arguments": ""}},
                        )
                        if tc_delta.get("id"):
                            slot["id"] = tc_delta["id"]
                        func = tc_delta.get("function") or {}
                        if "name" in func and func["name"]:
                            slot["function"]["name"] += func["name"]
                        if "arguments" in func and func["arguments"]:
                            slot["function"]["arguments"] += func["arguments"]

                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
        except httpx.RequestError as exc:
            yield StreamError(stage="openrouter_request", detail=str(exc))
            return

        final_content = "".join(accumulated_content)
        metadata: dict[str, Any] = {}
        if finish_reason:
            metadata["finish_reason"] = finish_reason
        if accumulated_tool_calls:
            metadata["tool_calls"] = list(accumulated_tool_calls.values())
        yield StreamDone(
            content=_truncate_at_role_leak(final_content),
            metadata=metadata,
        )

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Single-turn text generation. Delegates to chat()."""
        messages: list[ChatMessage] = []
        if system:
            messages.append(ChatMessage(role="system", content=system))
        messages.append(ChatMessage(role="user", content=prompt))
        response = self.chat(messages)
        return response.content


'''


# ── get_provider factory branch (inserted before final raise ValueError) ─────
OPENROUTER_FACTORY_BRANCH = '''    if name == "openrouter":
        from brain.persona_config import PersonaConfig

        model = model_override
        if model is None and persona_dir is not None:
            cfg_path = persona_dir / "persona_config.json"
            if cfg_path.exists():
                model = PersonaConfig.load(cfg_path).model
        if model is None:
            model = "deepseek/deepseek-chat"
        return OpenRouterProvider(model=model)
'''


# ── patcher ──────────────────────────────────────────────────────────────────
def patch() -> int:
    if not PROVIDER_PY.exists():
        print(f"FATAL: provider.py not found at {PROVIDER_PY}", file=sys.stderr)
        print("set PROVIDER_PY env var to override", file=sys.stderr)
        return 2

    text = PROVIDER_PY.read_text(encoding="utf-8")
    original = text
    changes: list[str] = []

    # ── patch 1: OllamaProvider.chat_stream → _chat_stream_unstreamable ──────
    if "class OllamaProvider(LLMProvider):" in text:
        ollama_start = text.index("class OllamaProvider(LLMProvider):")
        next_class_match = re.search(r"\nclass ", text[ollama_start + 1:])
        if next_class_match:
            ollama_end = ollama_start + 1 + next_class_match.start()
        else:
            ollama_end = len(text)
        ollama_block = text[ollama_start:ollama_end]
        if "    def chat_stream(" in ollama_block:
            new_block = ollama_block.replace(
                "    def chat_stream(",
                "    def _chat_stream_unstreamable(",
                1,
            )
            text = text[:ollama_start] + new_block + text[ollama_end:]
            changes.append("ollama: chat_stream → _chat_stream_unstreamable")
        else:
            changes.append("ollama: rename already applied (skipped)")
    else:
        print("WARN: OllamaProvider class not found, skipping rename", file=sys.stderr)

    # ── patch 2: inject OpenRouterProvider class ─────────────────────────────
    if "class OpenRouterProvider(LLMProvider):" in text:
        changes.append("openrouter class: already present (skipped)")
    else:
        # insert before "# ---------------------------------------------------------------------------\n# Factory"
        factory_marker = re.search(
            r"\n# -+\n# Factory\n# -+\n",
            text,
        )
        if factory_marker is None:
            # fallback: insert before "def get_provider("
            factory_marker = re.search(r"\ndef get_provider\(", text)
            if factory_marker is None:
                print("FATAL: could not find factory section", file=sys.stderr)
                return 3
            insert_at = factory_marker.start() + 1
        else:
            insert_at = factory_marker.start() + 1
        text = text[:insert_at] + OPENROUTER_CLASS + text[insert_at:]
        changes.append("openrouter class: injected")

    # ── patch 2.5: rename OpenRouterProvider.chat_stream → _chat_stream_disabled ──
    # bridge falls back to chat() which properly returns ChatResponse with
    # tool_calls populated, letting the framework's tool_loop dispatch them.
    # streaming UX is preserved because the bridge word-chunks the response.
    if "class OpenRouterProvider(LLMProvider):" in text:
        openrouter_start = text.index("class OpenRouterProvider(LLMProvider):")
        next_class_match = re.search(r"\nclass ", text[openrouter_start + 1:])
        if next_class_match:
            openrouter_end = openrouter_start + 1 + next_class_match.start()
        else:
            # End at "# Factory" marker since OpenRouterProvider is the last class
            factory_match = re.search(r"\n# -+\n# Factory", text[openrouter_start:])
            openrouter_end = openrouter_start + factory_match.start() if factory_match else len(text)
        openrouter_block = text[openrouter_start:openrouter_end]
        if "    def chat_stream(" in openrouter_block:
            new_openrouter_block = openrouter_block.replace(
                "    def chat_stream(",
                "    def _chat_stream_disabled(",
                1,
            )
            text = text[:openrouter_start] + new_openrouter_block + text[openrouter_end:]
            changes.append("openrouter: chat_stream → _chat_stream_disabled (use chat() fallback)")
        else:
            changes.append("openrouter: chat_stream rename already applied (skipped)")

    # ── patch 3: add openrouter branch to get_provider() ─────────────────────
    if 'name == "openrouter"' in text:
        changes.append("openrouter factory branch: already present (skipped)")
    else:
        # find the existing factory body — look for ollama branch then insert after it
        ollama_branch_match = re.search(
            r'    if name == "ollama":\n        return OllamaProvider\(\)\n',
            text,
        )
        if ollama_branch_match is None:
            print("FATAL: could not find ollama factory branch", file=sys.stderr)
            return 4
        insert_at = ollama_branch_match.end()
        text = text[:insert_at] + OPENROUTER_FACTORY_BRANCH + text[insert_at:]
        changes.append("openrouter factory branch: injected")

    # ── write provider.py back ───────────────────────────────────────────────
    if text != original:
        backup = PROVIDER_PY.with_suffix(".py.openrouter-patch.bak")
        backup.write_text(original, encoding="utf-8")
        print(f"backed up original provider.py → {backup}")
        PROVIDER_PY.write_text(text, encoding="utf-8")
        print(f"patched: {PROVIDER_PY}")

    # ── patch 4: extend KNOWN_PROVIDERS + KNOWN_MODELS in persona_config.py ──
    if not PERSONA_CONFIG_PY.exists():
        print(f"WARN: persona_config.py not found at {PERSONA_CONFIG_PY}", file=sys.stderr)
    else:
        pc_text = PERSONA_CONFIG_PY.read_text(encoding="utf-8")
        pc_original = pc_text

        # add 'openrouter' to KNOWN_PROVIDERS
        if '"openrouter"' in pc_text:
            changes.append("persona_config KNOWN_PROVIDERS: openrouter already present (skipped)")
        else:
            pc_text = pc_text.replace(
                'KNOWN_PROVIDERS = frozenset({"claude-cli", "ollama", "fake"})',
                'KNOWN_PROVIDERS = frozenset({"claude-cli", "ollama", "fake", "openrouter"})',
                1,
            )
            changes.append("persona_config KNOWN_PROVIDERS: openrouter added")

        # replace KNOWN_MODELS with a permissive set (kept claude names + added
        # the openrouter ids we expect to use). users can still hand-add more
        # by editing this line; non-matching ids fall back to 'sonnet' as
        # before.
        new_known_models = (
            'KNOWN_MODELS = frozenset({\n'
            '    # claude-cli names\n'
            '    "sonnet", "opus", "haiku",\n'
            '    # openrouter model ids (extend as needed)\n'
            '    "deepseek/deepseek-chat",\n'
            '    "deepseek/deepseek-chat-v3",\n'
            '    "deepseek/deepseek-r1",\n'
            '    "deepseek/deepseek-r1-distill-llama-70b",\n'
            '    "anthropic/claude-3.5-sonnet",\n'
            '    "anthropic/claude-3.5-haiku",\n'
            '    "anthropic/claude-3-opus",\n'
            '    "nousresearch/hermes-3-llama-3.1-405b",\n'
            '    "nousresearch/hermes-3-llama-3.1-70b",\n'
            '    "meta-llama/llama-3.1-405b-instruct",\n'
            '    "meta-llama/llama-3.1-70b-instruct",\n'
            '    "google/gemini-2.0-flash-exp",\n'
            '    "thudm/glm-4-32b",\n'
            '    "thudm/glm-4-plus",\n'
            '    "qwen/qwen-2.5-72b-instruct",\n'
            '    "x-ai/grok-2",\n'
            '})'
        )
        if 'deepseek/deepseek-chat' in pc_text and 'KNOWN_MODELS = frozenset({\n    # claude-cli names' in pc_text:
            changes.append("persona_config KNOWN_MODELS: already expanded (skipped)")
        else:
            pc_text = re.sub(
                r'KNOWN_MODELS = frozenset\(\{"sonnet", "opus", "haiku"\}\)',
                new_known_models,
                pc_text,
                count=1,
            )
            changes.append("persona_config KNOWN_MODELS: expanded with openrouter model ids")

        if pc_text != pc_original:
            pc_backup = PERSONA_CONFIG_PY.with_suffix(".py.openrouter-patch.bak")
            pc_backup.write_text(pc_original, encoding="utf-8")
            print(f"backed up original persona_config.py → {pc_backup}")
            PERSONA_CONFIG_PY.write_text(pc_text, encoding="utf-8")
            print(f"patched: {PERSONA_CONFIG_PY}")

    # ── summary ──────────────────────────────────────────────────────────────
    if not changes:
        print("no changes needed.")
    else:
        for c in changes:
            print(f"  · {c}")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
