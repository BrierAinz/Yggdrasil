"""Generation routes — text-to-3D, image-to-3D, poll status, history."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend import database as db
from backend.blender_client import BlenderMCPError, blender_client
from backend.models import (
    AIProvider,
    Generation,
    GenerationListResponse,
    GenerationType,
    ImageTo3DRequest,
    TextTo3DRequest,
)


router = APIRouter()
logger = logging.getLogger("forge.generation")


# ── Text to 3D ────────────────────────────────────────────────────────────


@router.post("/text-to-3d", response_model=Generation)
async def generate_text_to_3d(req: TextTo3DRequest, background_tasks: BackgroundTasks):
    """Start a text-to-3D generation job via Hunyuan3D or Rodin."""
    gen_id = str(uuid.uuid4())[:8]

    await db.create_generation(
        id=gen_id,
        type=GenerationType.TEXT_TO_3D.value,
        provider=req.provider.value,
        prompt=req.prompt,
    )

    if req.provider == AIProvider.HUNYUAN3D:
        background_tasks.add_task(_run_hunyuan_text, gen_id, req.prompt)
    elif req.provider == AIProvider.RODIN:
        background_tasks.add_task(_run_rodin_text, gen_id, req.prompt, req.bbox_condition)
    else:
        raise HTTPException(400, f"Provider {req.provider} not supported for text-to-3D")

    gen = await db.get_generation(gen_id)
    return Generation(**gen)


@router.post("/image-to-3d", response_model=Generation)
async def generate_image_to_3d(req: ImageTo3DRequest, background_tasks: BackgroundTasks):
    """Start an image-to-3D generation job."""
    gen_id = str(uuid.uuid4())[:8]

    await db.create_generation(
        id=gen_id,
        type=GenerationType.IMAGE_TO_3D.value,
        provider=req.provider.value,
        prompt=req.prompt,
        input_image=req.image_url or req.image_path,
    )

    if req.provider == AIProvider.HUNYUAN3D:
        background_tasks.add_task(_run_hunyuan_image, gen_id, req.image_url, req.prompt)
    elif req.provider == AIProvider.RODIN:
        background_tasks.add_task(
            _run_rodin_image, gen_id, req.image_url, req.image_path, req.bbox_condition
        )
    else:
        raise HTTPException(400, f"Provider {req.provider} not supported for image-to-3D")

    gen = await db.get_generation(gen_id)
    return Generation(**gen)


# ── Poll / Status ─────────────────────────────────────────────────────────


@router.get("/{gen_id}", response_model=Generation)
async def get_generation_status(gen_id: str):
    """Get the status of a generation job."""
    gen = await db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, f"Generation {gen_id} not found")
    return Generation(**gen)


@router.get("/", response_model=GenerationListResponse)
async def list_generations(
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List generation history with optional filters."""
    items, total = await db.list_generations(
        status=status, provider=provider, limit=limit, offset=offset
    )
    return GenerationListResponse(
        items=[Generation(**i) for i in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ── Background Workers ───────────────────────────────────────────────────


async def _poll_with_timeout(
    poll_fn,
    job_id: str,
    interval: int = 5,
    timeout: int = 600,
    provider: str = "unknown",
) -> dict:
    """Poll a generation job until done or timeout."""
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval
        try:
            result = await poll_fn(job_id)
            # Parse result — may be dict or string
            if isinstance(result, str):
                # Rodin returns status as string
                status = result.lower()
                if status in {"done", "completed"}:
                    return result
                if "fail" in status or "cancel" in status or "error" in status:
                    raise BlenderMCPError(
                        code=-1, message=f"{provider} generation failed: {result}"
                    )
            elif isinstance(result, dict):
                status = result.get("status", "")
                status_str = str(status).lower()
                if status_str in ("done", "completed"):
                    return result
                if any(x in status_str for x in ("fail", "cancel", "error")):
                    raise BlenderMCPError(
                        code=-1, message=f"{provider} generation failed: {result}"
                    )
        except BlenderMCPError as e:
            # Connection error — don't fail, keep trying
            if e.code in (-32001, -32002):
                logger.warning(f"Blender MCP connection issue during poll: {e.message}")
                continue
            raise

    raise BlenderMCPError(code=-32003, message=f"{provider} generation timed out after {timeout}s")


async def _run_hunyuan_text(gen_id: str, prompt: str):
    """Background worker: Hunyuan3D text-to-3D."""
    try:
        # Start generation
        result = await blender_client.generate_hunyuan3d(text_prompt=prompt)
        await db.update_generation(
            gen_id,
            status="processing",
            provider_data=result if isinstance(result, dict) else {"raw": result},
        )

        # Extract job_id from result
        job_id = None
        if isinstance(result, dict):
            job_id = result.get("job_id") or result.get("jobId")
        if not job_id:
            # Some responses include it differently
            raw = str(result)
            if "job_" in raw:
                import re

                match = re.search(r"job_\w+", raw)
                if match:
                    job_id = match.group()

        if not job_id:
            await db.update_generation(
                gen_id,
                status="failed",
                error=f"Could not extract job_id from Hunyuan3D response: {result}",
            )
            return

        await db.update_generation(gen_id, provider_job_id=job_id)

        # Poll until done
        final = await _poll_with_timeout(
            blender_client.poll_hunyuan_status,
            job_id,
            provider="Hunyuan3D",
        )

        # Import the asset
        zip_url = None
        if isinstance(final, dict):
            zip_url = final.get("ResultFile3Ds") or final.get("zip_file_url")
        if not zip_url:
            await db.update_generation(
                gen_id, status="failed", error=f"No download URL in Hunyuan3D result: {final}"
            )
            return

        import_result = await blender_client.import_hunyuan_asset(
            name=f"forge_{gen_id}", zip_file_url=str(zip_url)
        )

        result_object = None
        if isinstance(import_result, dict):
            result_object = import_result.get("object_name") or import_result.get("name")
        if isinstance(import_result, str):
            result_object = import_result

        await db.update_generation(
            gen_id,
            status="completed",
            result_object=result_object,
            result_path=str(zip_url),
        )

    except BlenderMCPError as e:
        await db.update_generation(gen_id, status="failed", error=e.message)
    except Exception as e:
        logger.exception(f"Hunyuan3D generation {gen_id} failed")
        await db.update_generation(gen_id, status="failed", error=str(e))


async def _run_rodin_text(gen_id: str, prompt: str, bbox_condition: list[float] | None):
    """Background worker: Rodin text-to-3D."""
    try:
        result = await blender_client.generate_rodin_text(prompt, bbox_condition=bbox_condition)
        await db.update_generation(
            gen_id,
            status="processing",
            provider_data=result if isinstance(result, dict) else {"raw": result},
        )

        # Extract subscription_key or request_id (depends on Rodin mode)
        sub_key = None
        req_id = None
        if isinstance(result, dict):
            sub_key = result.get("subscription_key")
            req_id = result.get("request_id")

        # Poll
        if sub_key:
            await _poll_with_timeout(
                lambda _: blender_client.poll_rodin_status(subscription_key=sub_key),
                sub_key,
                provider="Rodin",
            )
        elif req_id:
            await _poll_with_timeout(
                lambda _: blender_client.poll_rodin_status(request_id=req_id),
                req_id,
                provider="Rodin",
            )
        else:
            await db.update_generation(
                gen_id, status="failed", error=f"No job ID in Rodin response: {result}"
            )
            return

        # Import
        import_result = await blender_client.import_rodin_asset(
            name=f"forge_{gen_id}",
            subscription_key=sub_key,
            request_id=req_id,
        )

        result_object = None
        if isinstance(import_result, dict):
            result_object = import_result.get("object_name") or import_result.get("name")

        await db.update_generation(
            gen_id,
            status="completed",
            result_object=result_object,
        )

    except BlenderMCPError as e:
        await db.update_generation(gen_id, status="failed", error=e.message)
    except Exception as e:
        logger.exception(f"Rodin generation {gen_id} failed")
        await db.update_generation(gen_id, status="failed", error=str(e))


async def _run_hunyuan_image(gen_id: str, image_url: str | None, prompt: str | None):
    """Background worker: Hunyuan3D image-to-3D."""
    try:
        result = await blender_client.generate_hunyuan3d(text_prompt=prompt, image_url=image_url)
        await db.update_generation(
            gen_id,
            status="processing",
            provider_data=result if isinstance(result, dict) else {"raw": result},
        )

        job_id = None
        if isinstance(result, dict):
            job_id = result.get("job_id") or result.get("jobId")
        if not job_id:
            import re

            raw = str(result)
            match = re.search(r"job_\w+", raw)
            if match:
                job_id = match.group()

        if not job_id:
            await db.update_generation(
                gen_id, status="failed", error=f"No job_id from Hunyuan3D: {result}"
            )
            return

        await db.update_generation(gen_id, provider_job_id=job_id)

        final = await _poll_with_timeout(
            blender_client.poll_hunyuan_status, job_id, provider="Hunyuan3D"
        )

        zip_url = None
        if isinstance(final, dict):
            zip_url = final.get("ResultFile3Ds") or final.get("zip_file_url")
        if not zip_url:
            await db.update_generation(gen_id, status="failed", error=f"No download URL: {final}")
            return

        import_result = await blender_client.import_hunyuan_asset(
            name=f"forge_{gen_id}", zip_file_url=str(zip_url)
        )

        result_object = None
        if isinstance(import_result, dict):
            result_object = import_result.get("object_name") or import_result.get("name")

        await db.update_generation(
            gen_id, status="completed", result_object=result_object, result_path=str(zip_url)
        )

    except BlenderMCPError as e:
        await db.update_generation(gen_id, status="failed", error=e.message)
    except Exception as e:
        logger.exception(f"Hunyuan3D image gen {gen_id} failed")
        await db.update_generation(gen_id, status="failed", error=str(e))


async def _run_rodin_image(
    gen_id: str,
    image_url: str | None,
    image_path: str | None,
    bbox_condition: list[float] | None,
):
    """Background worker: Rodin image-to-3D."""
    try:
        image_urls = [image_url] if image_url else None
        image_paths = [image_path] if image_path else None

        result = await blender_client.generate_rodin_image(
            image_urls=image_urls,
            image_paths=image_paths,
            bbox_condition=bbox_condition,
        )
        await db.update_generation(
            gen_id,
            status="processing",
            provider_data=result if isinstance(result, dict) else {"raw": result},
        )

        sub_key = None
        req_id = None
        if isinstance(result, dict):
            sub_key = result.get("subscription_key")
            req_id = result.get("request_id")

        if sub_key:
            await _poll_with_timeout(
                lambda _: blender_client.poll_rodin_status(subscription_key=sub_key),
                sub_key,
                provider="Rodin",
            )
        elif req_id:
            await _poll_with_timeout(
                lambda _: blender_client.poll_rodin_status(request_id=req_id),
                req_id,
                provider="Rodin",
            )
        else:
            await db.update_generation(gen_id, status="failed", error=f"No job ID: {result}")
            return

        import_result = await blender_client.import_rodin_asset(
            name=f"forge_{gen_id}",
            subscription_key=sub_key,
            request_id=req_id,
        )
        result_object = None
        if isinstance(import_result, dict):
            result_object = import_result.get("object_name") or import_result.get("name")

        await db.update_generation(gen_id, status="completed", result_object=result_object)

    except BlenderMCPError as e:
        await db.update_generation(gen_id, status="failed", error=e.message)
    except Exception as e:
        logger.exception(f"Rodin image gen {gen_id} failed")
        await db.update_generation(gen_id, status="failed", error=str(e))
