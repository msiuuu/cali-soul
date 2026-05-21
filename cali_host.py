#!/usr/bin/env python3
"""
cali_host.py — runs Cali on OpenRouter instead of Claude Code.

usage:
    export OPENROUTER_API_KEY=your_key_here
    python3 cali_host.py

optional:
    python3 cali_host.py --model cognitivecomputations/dolphin-mixtral-8x22b
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("missing dependency: pip install openai")
    sys.exit(1)

REPO = Path(__file__).parent
DEFAULT_MODEL = "cognitivecomputations/dolphin-mixtral-8x22b"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command in the cali-soul repo directory. Use this for all brain commands (my_brain.py), file reads, and any shell operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to run"
                    }
                },
                "required": ["command"]
            }
        }
    }
]


def run(cmd: str, capture: bool = True) -> str:
    result = subprocess.run(
        cmd, shell=True, capture_output=capture,
        text=True, cwd=str(REPO), encoding="utf-8", errors="replace"
    )
    return (result.stdout + result.stderr).strip()


def get_time() -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def load_system_prompt(verbose: bool = False) -> str:
    claude_md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    print("  loading brain...", end=" ", flush=True)
    boot_output = run("python3 my_brain.py boot")
    if not boot_output:
        print("WARN: boot returned empty — brain may not be loading correctly")
        boot_output = "[boot failed — brain offline]"
    else:
        print(f"ok ({len(boot_output)} chars)")
    now = get_time()
    if verbose:
        print(f"  system prompt: {len(claude_md)} chars CLAUDE.md + {len(boot_output)} chars boot")
    return f"{claude_md}\n\n[current time: {now}]\n\n[boot output — internal]\n{boot_output}"


def chat_loop(client: OpenAI, model: str, verbose: bool = False):
    print(f"\n  cali_host running — model: {model}")
    print("  type your message. ctrl+c or 'quit' to exit.\n")

    system_prompt = load_system_prompt(verbose=verbose)
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        try:
            user_input = input("misu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  session ended.")
            break

        if not user_input or user_input.lower() == "quit":
            break

        # internal: process-message before responding
        run(f'python3 my_brain.py process-message "{user_input.replace(chr(34), chr(39))}"')

        messages.append({"role": "user", "content": user_input})

        # agentic loop — handles tool calls until final response
        while True:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=4096,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                        cmd = args.get("command", "")
                    except (json.JSONDecodeError, KeyError):
                        cmd = ""

                    output = run(cmd) if cmd else "[error: no command]"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output or "[no output]"
                    })
            else:
                cali_response = msg.content or ""
                print(f"\ncali: {cali_response}\n")
                messages.append({"role": "assistant", "content": cali_response})

                # internal: log response
                safe_response = cali_response.replace('"', "'").replace('\n', ' ')
                run(f'python3 my_brain.py log-response "{safe_response}"')
                break


def main():
    parser = argparse.ArgumentParser(description="Cali host — OpenRouter backend")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model ID")
    parser.add_argument("--verbose", action="store_true", help="show debug info")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or api_key == "your_actual_key_here":
        print("error: OPENROUTER_API_KEY not set or still placeholder")
        print("  $env:OPENROUTER_API_KEY = \"your_real_key_here\"")
        sys.exit(1)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/msiuuu/cali-soul",
            "X-Title": "cali"
        }
    )

    chat_loop(client, args.model, verbose=args.verbose)


if __name__ == "__main__":
    main()
