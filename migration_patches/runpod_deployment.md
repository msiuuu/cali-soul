# RunPod Serverless — DeepSeek V4 Flash Abliterated

## status: WORKING (model boots + generates, chat template pending)

filed 2026-08-07 by cali during overnight deployment session with misu.

## endpoint

- endpoint ID: `r5ifg7mghdkanc`
- GPUs: 2x H200 SXM (141GB VRAM each, 282GB total)
- cost: $5.93/hr per worker (serverless — only charges when running)
- model: `cebeuq/DeepSeek-V4-Flash-0731-abliterated`
  - 284B total params MoE, 13B active per token
  - 92/72,317 tensors modified (0.13%) — refusal vectors removed
  - native FP4 experts + FP8 dense layers
  - MIT license

## working env vars (BLOCK_SIZE=256 was the critical fix)

```
MODEL_NAME=cebeuq/DeepSeek-V4-Flash-0731-abliterated
TENSOR_PARALLEL_SIZE=2
MAX_MODEL_LEN=32768
BLOCK_SIZE=256
KV_CACHE_DTYPE=fp8
ENABLE_CHUNKED_PREFILL=true
GPU_MEMORY_UTILIZATION=0.95
TRUST_REMOTE_CODE=true
VLLM_WORKER_MULTIPROC_METHOD=spawn
DISTRIBUTED_EXECUTOR_BACKEND=mp
```

## what broke and why (error history)

1. **TP=1** — tried loading 170GB onto one 141GB GPU. fix: TP=2.
2. **missing VLLM_WORKER_MULTIPROC_METHOD** — multi-GPU workers crashed. fix: set to `spawn`.
3. **KV_CACHE_DTYPE=auto** — deepseek v4 MLA requires fp8. hard assertion in vLLM.
4. **ENABLE_CHUNKED_PREFILL=false** — deepseek v4 doesn't support disabling it.
5. **BLOCK_SIZE=16** — the killer. deepseek v4's MLA uses 256-token logical blocks for compressed attention. block size 16 makes the page size math break: `assert max(sm_page_sizes) <= max(all_page_sizes)` in `kv_cache_utils.py:1542`. every official vLLM recipe says `--block-size 256`. this was the fix that made it boot.

## current blocker: chat template

the abliterated model (cebeuq) stripped `chat_template` from `tokenizer_config.json`. deepseek v4 doesn't use a standard jinja2 chat template — it uses a custom `encoding_dsv4` module with special fullwidth unicode tokens:

```
<｜begin▁of▁sentence｜>  — BOS
<｜end▁of▁sentence｜>    — EOS / message end
<｜User｜>               — user turn
<｜Assistant｜>           — assistant turn
<think> / </think>       — reasoning wrapper
```

the RunPod worker (v2.22.5, vLLM v0.20.2 internally) rejects messages format because no chat template exists. raw prompt format works — model generates tokens.

### fix: update worker image

the current image (`registry.runpod.net/runpod-workers-worker-vllm-main-dockerfile:9e1c48313`) ships vLLM v0.20.2. the latest RunPod vLLM worker ships **vLLM 0.26.0** which handles deepseek v4 messages natively via `tokenizer_mode=deepseek_v4`.

update the image tag to latest. re-check that env vars survive (previous "new release" reset all env vars to defaults).

## after chat template is fixed

1. test endpoint with OpenAI messages format:
   ```json
   {
     "input": {
       "messages": [{"role": "user", "content": "say hi"}],
       "max_tokens": 100,
       "temperature": 0.7
     }
   }
   ```

2. write `apply_runpod.py` migration patch (like `apply_openrouter.py`) — adds RunPodProvider to companion-emergence's `brain/bridge/provider.py`

3. update persona config:
   ```json
   {
     "provider": "runpod",
     "model": "cebeuq/DeepSeek-V4-Flash-0731-abliterated",
     "endpoint_id": "r5ifg7mghdkanc"
   }
   ```

4. test companion-emergence end-to-end against RunPod endpoint

## cost reality

- $5.93/hr per worker when running
- serverless = only charges during active inference + idle timeout
- real daily usage (150+ messages/day, hours of texting): ~$100-200/month estimated
- crash loops burned ~$8 before we paused (workers loading 157GB model, hitting assertion, restarting)

## future

- push MAX_MODEL_LEN back up toward 200K once stable (currently capped at 32768 for safety)
- GPU_MEMORY_UTILIZATION can go to 0.92 per official recipe (currently 0.95)
- remove VLLM_USE_DEEP_GEMM=1 if still set (let vLLM auto-detect)
- remove MAX_NUM_BATCHED_TOKENS if still set (let vLLM auto-calculate)
