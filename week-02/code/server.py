"""
FastAPI server that wraps a local Hugging Face transformers model and exposes
an OpenAI-compatible /v1/chat/completions endpoint with streaming support.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8000

Then point any OpenAI client at http://localhost:8000/v1 with any API key.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from threading import Thread
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

# ─── Configuration ────────────────────────────────────────────────────────────

MODEL_ID = "Qwen/Qwen3-1.7B"

tokenizer: Optional[AutoTokenizer] = None
model: Optional[AutoModelForCausalLM] = None


# ─── Lifespan (model load / teardown) ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, model
    print(f"Loading {MODEL_ID} …")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    model.eval()
    print("Model ready. Server is accepting requests.")
    yield
    # Nothing special needed on shutdown, but could offload model here.


app = FastAPI(
    title="Local LLM — OpenAI-compatible API",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Request / Response schemas ───────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[Message]
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=512, ge=1)
    # Qwen3-specific: set True to allow the model to think before answering
    enable_thinking: bool = False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sse_chunk(
    completion_id: str,
    created: int,
    model_id: str,
    delta: dict,
    finish_reason: Optional[str] = None,
) -> str:
    """Serialise one Server-Sent Event chunk in OpenAI format."""
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_id,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(payload)}\n\n"


async def _iter_streamer(streamer: TextIteratorStreamer):
    """Yield tokens from a synchronous TextIteratorStreamer without blocking
    the asyncio event loop by running each `next()` in the thread-pool."""
    loop = asyncio.get_event_loop()
    it = iter(streamer)
    while True:
        try:
            token = await loop.run_in_executor(None, next, it)
            yield token
        except StopIteration:
            break


def _build_generation_kwargs(req: ChatCompletionRequest) -> dict:
    # Disable sampling when temperature == 0 (greedy decoding)
    do_sample = req.temperature > 0
    return dict(
        max_new_tokens=req.max_tokens,
        do_sample=do_sample,
        temperature=req.temperature if do_sample else 1.0,
        top_p=req.top_p,
        pad_token_id=tokenizer.eos_token_id,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/v1/models")
async def list_models():
    """Return the list of available models (mirrors OpenAI /v1/models)."""
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": 0,
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint with optional SSE streaming."""
    if tokenizer is None or model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    # Apply the model's chat template to turn messages into a single prompt string
    messages = [m.model_dump() for m in req.messages]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=req.enable_thinking,
    )
    inputs = tokenizer(prompt, return_tensors="pt")

    gen_kwargs = _build_generation_kwargs(req)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    # ── Streaming response ────────────────────────────────────────────────────
    if req.stream:
        streamer = TextIteratorStreamer(
            tokenizer, skip_prompt=True, skip_special_tokens=True
        )

        def _run_generate():
            with torch.no_grad():
                model.generate(**inputs, streamer=streamer, **gen_kwargs)

        Thread(target=_run_generate, daemon=True).start()

        async def event_stream():
            # Opening chunk announces the assistant role
            yield _sse_chunk(completion_id, created, req.model, {"role": "assistant"})
            async for token in _iter_streamer(streamer):
                if token:
                    yield _sse_chunk(completion_id, created, req.model, {"content": token})
            # Closing chunk with finish_reason
            yield _sse_chunk(completion_id, created, req.model, {}, finish_reason="stop")
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # ── Non-streaming response ─────────────────────────────────────────────────
    def _run_generate_sync():
        with torch.no_grad():
            return model.generate(**inputs, **gen_kwargs)

    output_ids = await asyncio.to_thread(_run_generate_sync)

    # Decode only the newly generated tokens (skip the echoed prompt)
    new_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    reply = tokenizer.decode(new_ids, skip_special_tokens=True)

    prompt_tokens = int(inputs["input_ids"].shape[-1])
    completion_tokens = int(new_ids.shape[-1])

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


# ─── Entry-point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
