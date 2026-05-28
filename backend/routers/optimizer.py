"""
routers/optimizer.py
────────────────────
WS  /api/optimize/de        — DE optimizer   (WebSocket — cloud-safe, no HTTP timeout)
WS  /api/optimize/ga-minlp  — GA-MINLP       (WebSocket — streams live progress)

Both optimizers use WebSocket so long-running jobs survive cloud platform
HTTP timeouts (typically 30–60 s).  The protocol is identical for both:
  Client → server : JSON-serialised request payload
  Server → client : {"type":"progress", "iteration":N, "best":W}  (streaming)
                    {"type":"result",   "result": <OptResult>}      (final)
                    {"type":"error",    "message":"…"}               (on failure)
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models import DEOptRequest, GAMINLPRequest
from services.truss_service import run_de_optimizer, run_ga_minlp_optimizer

router   = APIRouter()
executor = ThreadPoolExecutor(max_workers=2)


# ─────────────────────────────────────────────────────────────────
#  Shared WebSocket helper
# ─────────────────────────────────────────────────────────────────

async def _ws_run(websocket: WebSocket, fn, req):
    """
    Generic WebSocket runner.
    Calls fn(req, progress_cb) in a thread pool and streams messages back.
    """
    await websocket.accept()
    loop  = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress_cb(msg: dict):
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    future = loop.run_in_executor(executor, lambda: fn(req, progress_cb))

    try:
        while not future.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.15)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                pass

        while not queue.empty():
            await websocket.send_json(queue.get_nowait())

        result = await future
        await websocket.send_json({"type": "result", "result": result.model_dump()})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────
#  DE optimizer  (WebSocket — replaces the old blocking POST)
# ─────────────────────────────────────────────────────────────────
@router.websocket("/optimize/de")
async def optimize_de_ws(websocket: WebSocket):
    """
    WebSocket endpoint for the DE (sizing + shape) optimizer.
    Streams per-generation progress; safe on any cloud platform.
    """
    # 1. CRITICAL FIX: Accept the connection first!
    await websocket.accept()
    
    try:
        raw = await websocket.receive_text()
        req = DEOptRequest.model_validate_json(raw)
    except Exception as e:
        # Since we already accepted above, we don't need to call accept() here anymore
        await websocket.send_json({"type": "error", "message": f"Bad request: {e}"})
        await websocket.close()
        return

    # Wrap run_de_optimizer to accept the progress_cb signature
    def _de_with_cb(req, progress_cb):
        # ... (Keep all your existing optimizer compilation logic exactly the same) ...
        
        sections, shifts, weight, is_valid, history = opt.optimize(pop_size=req.pop_size, max_gen=req.max_gen)
        
        from models import OptResult, SectionAssignment, NodeShift
        return OptResult(
            sections=[SectionAssignment(member_id=k, section=v) for k, v in sections.items()],
            node_shifts=[NodeShift(node_id=k, dx=v["dx"], dy=v["dy"], dz=v["dz"]) for k, v in shifts.items()],
            topology={m.id: True for m in combos_ts[0].members},
            weight_kg=round(weight, 3),
            orig_weight_kg=round(orig_weight, 3),
            is_valid=is_valid,
            hist_p1=[],
            hist_p2=[w for w in history if w < 1e6],
        )

    # 2. Pass the authenticated websocket down to your helper runner
    await _ws_run(websocket, _de_with_cb, req)

# ─────────────────────────────────────────────────────────────────
#  GA-MINLP optimizer  (WebSocket with live progress stream)
# ─────────────────────────────────────────────────────────────────

@router.websocket("/optimize/ga-minlp")
async def optimize_ga_minlp_ws(websocket: WebSocket):
    """
    WebSocket endpoint for the GA-MINLP optimizer.

    Protocol
    ────────
    Client → server : JSON-serialised GAMINLPRequest
    Server → client : stream of WSProgress JSON objects
        {"type":"phase",    "phase":1, "message":"…"}
        {"type":"progress", "phase":1, "generation":10, "best":1234.5}
        {"type":"phase",    "phase":2, "message":"…"}
        {"type":"progress", "phase":2, "iteration":20,  "best":987.6}
        {"type":"result",   "result": <OptResult JSON>}
        {"type":"error",    "message":"…"}
    """
    await websocket.accept()
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    # ── Receive request ───────────────────────────────────────────
    try:
        raw = await websocket.receive_text()
        req = GAMINLPRequest.model_validate_json(raw)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Bad request: {e}"})
        await websocket.close()
        return

    # ── Progress callback (called from optimizer thread) ──────────
    def progress_cb(msg: dict):
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    # ── Run optimizer in thread pool ──────────────────────────────
    future = loop.run_in_executor(
        executor,
        lambda: run_ga_minlp_optimizer(req, progress_cb=progress_cb),
    )

    # ── Stream progress until the optimizer finishes ──────────────
    try:
        while not future.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.15)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                pass  # keep polling

        # Drain any remaining queued messages
        while not queue.empty():
            await websocket.send_json(queue.get_nowait())

        # Send final result
        result: OptResult = await future
        await websocket.send_json({
            "type":   "result",
            "result": result.model_dump(),
        })

    except WebSocketDisconnect:
        pass  # client closed early — optimizer thread will finish naturally
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
