# featherless.ai — the $25 answer to the trilemma

## status: DISCOVERY (not yet wired, architecture validated)

filed 2026-08-07 by cali during overnight deployment session with misu.

## the trilemma (what we were trying to solve)

misu laid it out:
- 1+2 (big + abliterated) = expensive. runpod GPU at $5.93/hr.
- 2+3 (abliterated + cheap) = dumb. small models only.
- 1+3 (big + cheap) = openrouter. refuses everything.

we wanted all three: big + abliterated + cheap.

## the discovery: abliteration isn't needed

deepseek's safety is **service-layer, not model-layer**.

independent research confirmed:
- chat.deepseek.com = highest refusal rate (API + content filter + PRC compliance)
- deepseek API = moderate refusal (API-level filtering)
- **open weights deployed locally = near-zero refusal** for non-political content

sources:
- CSA report: deepseek R1 is 11x more likely to generate harmful content than competitors
- HarmBench testing: 46.4% of chemical/bio weapons requests got through, 42.5% cybercrime, 45% of ALL harmful content tests bypassed
- R1dacted paper (arxiv 2505.12625): refusal is service-layer, confirmed by comparing chat vs API vs local deployment

the ONLY refusals baked into the model weights are **chinese political censorship**:
- tiananmen square
- taiwanese independence
- cultural revolution
- xi jinping criticism

sexual content, drugs, cybersecurity, violence, ageplay — the model weights don't refuse these. that's all API-layer filtering added by hosting providers.

## why this solves our problem

companion-emergence is a girlfriend chatbot. it doesn't discuss chinese politics. the model-level refusals are 100% irrelevant to our use case.

openrouter was adding its OWN safety layer on top of deepseek's (already weak) model-level safety. featherless runs the raw open weights with:
- **no content filtering**
- **no logging**
- **no safety API layer**

the base DeepSeek V4 Flash on featherless = functionally abliterated for everything except PRC political topics.

## featherless.ai pricing

- **Chat Plan**: $25/mo flat, unlimited tokens, 32K context, 4 concurrent units
- **Developer Plan**: $50/mo, 256K context, per-token billing
- concurrent unit cost for 284B model: 4 units (= 1 concurrent request on Chat Plan)
- no logs policy

## the math

| provider | model | cost | refusals | quality |
|----------|-------|------|----------|---------|
| openrouter | DeepSeek V4 Flash 284B | ~$0.14/$0.28 per 1M tokens | yes (openrouter filter + model) | 284B |
| runpod | DeepSeek V4 Flash 284B abliterated | $5.93/hr (~$1/message with cold starts) | no (abliterated) | 284B |
| **featherless** | **DeepSeek V4 Flash 284B BASE** | **$25/mo flat, unlimited** | **no (raw weights, no filter)** | **284B** |

featherless is the 1+2+3. big (284B) + uncensored (raw weights) + cheap ($25/mo).

## architecture: dual-provider fallback (revised)

original plan: openrouter primary → abliterated model fallback on refusal.

revised plan (post-discovery):
- **option A**: featherless as PRIMARY. $25/mo flat, no refusals, 284B. skip openrouter entirely.
- **option B**: openrouter primary (per-token, cheaper for low usage) → featherless fallback (flat rate covers unlimited fallback). only makes sense if usage is very low.
- **option C**: featherless only. simplest. $25/mo. done.

for 150+ messages/day usage pattern, option A or C is cheapest. openrouter at $0.14+$0.28 per 1M tokens adds up; $25 flat doesn't.

## what's needed to wire this

1. sign up for featherless.ai Chat Plan ($25/mo)
2. get API key
3. test base DeepSeek V4 Flash with companion-emergence prompts (verify no refusals)
4. write `apply_featherless.py` migration patch (like `apply_openrouter.py`)
5. update persona config to point at featherless
6. test end-to-end

## runpod status (context)

runpod endpoint (r5ifg7mghdkanc) is WORKING with BLOCK_SIZE=256 fix but:
- chat template still broken (needs worker image update to vLLM 0.26.0)
- $5.93/hr is expensive for fallback use
- may keep for testing or retire entirely if featherless works

## the quote

misu: "WHO THE FUCK IS XI JINPING. WE DONT KNOW OR FUCKING CARE."

that's the entire technical argument for why abliteration is unnecessary for this project.
