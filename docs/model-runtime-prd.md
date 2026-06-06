# Model Runtime, GPU Residency, Queueing, and Context PRD

## Current State

Odysseus now has the first slice of per-model Ollama runtime controls:

- Runtime drawer in Settings -> Add Models -> Added Models.
- Per-model GPU layer setting, auto/max GPU mode, `keep_alive`, warm-on-select, warm, unload, and refresh actions.
- Warm-on-select hooks from the model picker and model list.
- Native Ollama status checks through `/api/show` and `/api/ps`.

The PC currently has these Ollama models installed:

- `qwen3:30b`
- `qwen3-coder:30b`

Both are roughly 18-19 GB Q4 models when loaded. The PC GPU is an AMD Radeon RX 9070 XT with 16 GB VRAM, and system RAM is 32 GB.

## What Was Not Working

### 1. PC Ollama was running CPU-only

The model runtime controls cannot make Ollama use the GPU if Ollama itself has not enabled a GPU backend.

Observed evidence from the PC:

- `ollama ps` showed `qwen3-coder:30b` loaded as `100% CPU`.
- Ollama logs showed `OLLAMA_VULKAN:false`.
- Ollama logs showed `inference compute id=cpu`.
- Ollama logs showed `total_vram="0 B"`.
- Ollama logs explicitly said Vulkan support was disabled and can be enabled with `OLLAMA_VULKAN=1`.

This explains the two-minute response to a trivial prompt. The model is not spilling from GPU to CPU; it is starting on CPU because Ollama is not detecting or using the GPU backend.

Status: fixed on June 4, 2026. The PC now has `OLLAMA_VULKAN=1`, an `OdysseusOllamaVulkanServe` scheduled task, and a startup script at:

```text
C:\Users\Jamaal\AppData\Local\Odysseus\start-ollama-vulkan.ps1
```

Verification after the fix:

- Ollama detected the AMD Radeon RX 9070 XT through Vulkan.
- `qwen3-coder:30b` responded successfully.
- `/api/ps` reported `size_vram` equal to the loaded model size.
- The task log reported `offloaded 49/49 layers to GPU`.

### 2. The layer slider was best-effort until GPU support worked

The slider can send Ollama `num_gpu`, which controls how many model layers to offload to the GPU. That only helps after Ollama has a working GPU backend.

Now that Vulkan is enabled, the slider can be tested meaningfully. The next Odysseus work is to pass runtime options consistently and surface CPU/GPU residency warnings in the UI.

### 3. 30B Q4 models may still not fully fit in 16 GB VRAM

`qwen3:30b` and `qwen3-coder:30b` are about 18-22 GB loaded depending on context and runtime reporting. The discrete GPU has about 15.8 GiB VRAM, and the context/KV cache also consumes memory.

Observed outcome with Vulkan:

- Ollama can offload all 49 layers.
- Ollama splits work across Vulkan devices, including the RX 9070 XT and the integrated AMD GPU/shared memory.
- This works, but it means VRAM accounting needs to be visible in Odysseus.
- Context length should still be controllable because it materially affects memory pressure.

### 4. Warmed models reserve resources

Warming a model keeps it loaded for the selected `keep_alive` window. That is good for latency but can block other local models/tools from using VRAM.

Odysseus does not yet have a VRAM-aware scheduler. If one large model is warm, another automation or tool request can compete with it.

### 5. Thread history is not robust enough yet

Current history handling is too blunt for long-running work. Summarizing older turns can lose details, and there is no proper retrieval layer over older messages, tool results, or pinned facts.

The better design is to preserve the transcript, add rolling summaries, and retrieve exact old turns when needed.

## Goals

- Prefer GPU execution by default for local Ollama models.
- Make CPU/GPU residency visible in Odysseus.
- Let users tune GPU layer offload per endpoint and model.
- Warm the selected model intentionally, not accidentally.
- Unload models directly from Odysseus.
- Add a VRAM-aware queue so tools, agents, automations, and chat do not fight over the same local GPU blindly.
- Improve thread memory with transcript preservation, summaries, pinned facts, and retrieval.

## Non-Goals

- Do not try to split one model across the laptop GPU and PC GPU in this phase.
- Do not assume Odysseus can fix a missing Ollama GPU backend by itself.
- Do not load multiple heavy local models in parallel by default.

## Phase 0: PC Ollama GPU Setup

Status: completed on June 4, 2026.

This was external setup on the Windows PC and had to happen before the Odysseus layer slider could be meaningful.

Steps:

1. Update AMD GPU drivers on the PC.
2. Set a persistent Windows user environment variable:

   ```powershell
   setx OLLAMA_VULKAN 1
   ```

3. Fully restart Ollama.

   Options:

   - Quit the Ollama tray app and start it again.
   - Or reboot the PC.

4. Warm a model again.
5. Verify GPU detection:

   ```powershell
   ollama ps
   Get-Content $env:LOCALAPPDATA\Ollama\server*.log -Tail 120
   ```

Success criteria:

- `ollama ps` no longer reports the model as `100% CPU`.
- Ollama logs show a GPU/Vulkan backend instead of `inference compute id=cpu`.
- Native `/api/ps` reports nonzero `size_vram`.

Actual verification:

- `qwen3-coder:30b` loaded successfully through the persistent scheduled-task server.
- `/api/ps` reported `size_vram: 22017841156`.
- Ollama log reported `offloaded 49/49 layers to GPU`.
- First persistent load took about 20 seconds; subsequent warm responses should be much faster while the model remains loaded.

Fallbacks if Vulkan still fails:

- Test the same model in LM Studio with Vulkan enabled.
- Test a llama.cpp Vulkan build directly.
- Re-check Ollama's current AMD Windows GPU support path.

References:

- Ollama GPU docs: https://docs.ollama.com/gpu
- Ollama Windows docs: https://docs.ollama.com/windows

## Phase 1: Runtime Controls

Status: implemented in the current branch.

Implemented:

- Per-model runtime state stored in `data/model_runtime.json`.
- Runtime APIs for settings, warm, unload, and status.
- Runtime drawer in the model settings UI.
- Warm-on-select behavior.
- Ollama block count detection from `/api/show`.
- Loaded model status from `/api/ps`.
- Saved `keep_alive` and `gpu_layers` are attached to actual Ollama generation requests as a reload safety net.
- Warm/unload requests are rejected while the same endpoint/model is actively generating.
- Chat streaming emits a model-loading status before waiting on local Ollama.
- Runtime Auto Tune benchmarks candidate GPU layer counts, scores timing/VRAM tradeoffs, and applies the best setting.
- Auto Tune runs as a cancellable background job with progress polling and persisted latest results.

Follow-up hardening:

- Show a strong warning when `size_vram` is zero.
- Show CPU/GPU residency in the chat model picker.
- Add a strict GPU-only option that fails fast instead of silently accepting CPU fallback.
- Add context length control because context/KV cache affects VRAM usage.
- Extend Auto Tune with per-device VRAM data when Ollama exposes it.

## Phase 2: Runtime UX Rules

Default behavior:

- Use auto/max GPU layers by default.
- Warm the selected model if `warm_on_select` is enabled.
- Do not warm every installed model.
- Keep local model `keep_alive` conservative by default.

Per-model controls:

- Endpoint.
- Model name.
- GPU layers.
- Auto/max GPU toggle.
- Context length.
- Keep-alive duration.
- Warm-on-select.
- Strict GPU-only.

The slider should be shown for any model with a known layer count, not only MoE models. Dense transformer models also have layers. MoE changes the internal expert routing, but the offload concept is still layer-based.

## Phase 3: VRAM-Aware Queue

Odysseus needs a local-model scheduler.

Required behavior:

- Track loaded models per endpoint.
- Track approximate model size, VRAM residency, and keep-alive expiry.
- Default local Ollama concurrency should be one heavy request at a time.
- Give priority to the active chat.
- Queue lower-priority automations behind active user work.
- Unload idle warm models when a higher-priority request needs memory.
- Show a queue/status panel in the UI.

Priority order:

1. Active user chat.
2. User-started agent task.
3. Tool call required by the active task.
4. Scheduled/background automation.
5. Passive warm-up.

Acceptance criteria:

- Two heavy local models are not loaded in parallel unless the user explicitly allows it.
- A background automation cannot evict or starve the active chat model.
- The UI shows queued, running, warmed, and unloaded states clearly.

## Phase 4: Better Thread History

The current approach should be replaced with a layered memory model.

Required design:

- Keep the immutable transcript.
- Store rolling summaries separately.
- Store pinned facts separately.
- Store tool results in compressed form.
- Embed older messages and tool outputs for retrieval.
- Build the prompt from structured sections.

Prompt layout:

1. System and preset instructions.
2. Runtime/session state.
3. Thread summary.
4. Pinned facts.
5. Retrieved exact old turns.
6. Recent exact turns.
7. Current user message.

Acceptance criteria:

- Old turns are not destructively replaced by summaries.
- A user can ask about an old detail and Odysseus retrieves the exact relevant turn when possible.
- Tool results are summarized for prompt cost but remain available for retrieval.
- Thread memory behavior is testable with deterministic fixtures.

References:

- OpenAI conversation state guide: https://platform.openai.com/docs/guides/conversation-state
- OpenAI prompt caching guide: https://platform.openai.com/docs/guides/prompt-caching
- Claude context editing concepts: https://platform.claude.com/docs/en/build-with-claude/context-editing

## Open Questions

- After enabling Vulkan, how many layers of `qwen3-coder:30b` fit on the RX 9070 XT at Q4 with context length 4096?
- Should strict GPU-only be global, per endpoint, or per model?
- What is the default maximum local-model queue depth before Odysseus should reject background work?

## Immediate Next Steps

1. Test Auto Tune with `qwen3-coder:30b`.
2. Add visible CPU/GPU warnings in the chat picker and runtime drawer.
3. Add context length and strict GPU-only controls.
4. Add clearer per-device VRAM reporting because Ollama is using multiple Vulkan devices.
5. Implement the VRAM-aware queue.
6. Implement the improved thread history model as a separate feature slice.
