"""Excel import/export routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.schemas import ImportResponse
from app.dependencies import get_plan_service
from app.excel.service import export_xlsx, import_xlsx
from app.services.plan_service import PlanService

router = APIRouter(prefix="/api/excel", tags=["excel"])


@router.post("/import", response_model=ImportResponse)
async def excel_import(
    file: UploadFile = File(...),
    service: PlanService = Depends(get_plan_service),
) -> ImportResponse:
    content = await file.read()
    parsed = import_xlsx(content, project_start=None)
    # Keep existing project_start if plan exists
    try:
        current = service.get_active_plan()
        project_start = current.project_start
    except Exception:  # noqa: BLE001
        project_start = parsed["project_start"]

    plan = service.replace_plan_from_rows(
        name=parsed["name"],
        project_start=project_start,
        rows=parsed["rows"],
    )
    return ImportResponse(
        plan=plan,
        import_report={"created": len(plan.tasks), "warnings": []},
    )


@router.get("/export")
def excel_export(service: PlanService = Depends(get_plan_service)) -> Response:
    plan = service.get_active_plan()
    data = export_xlsx(plan)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plan.xlsx"'},
    )
