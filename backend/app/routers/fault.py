"""故障登记接口：维护设备故障，覆盖确认定级、提交恢复、挂起故障等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, GradePayload, GradeResult, PageResult
from app.services.fault import FaultService

router = APIRouter(prefix="/api/fault", tags=["故障登记"])

service = FaultService()

LIST_FIELDS = ["故障编号", "发生设备", "故障现象", "影响范围", "发生时间", "报告人", "恢复时间", "故障状态", "定级等级", "处理期限"]
STATUSES = ["待定级", "已定级", "处置中", "已恢复", "已挂起"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按故障编号检索"),
    status: str | None = Query(default=None, description="待定级、已定级、处置中、已恢复、已挂起"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按故障编号与状态过滤故障登记列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.post("/grade", response_model=GradeResult)
def grade_entries(payload: GradePayload) -> GradeResult:
    """批量定级：多选故障按同一份定级依据套用，逐条给出结果；已恢复、已挂起、故障现象为空的会被拦下并说明原因。"""
    result, message = service.grade_batch(payload.ids, payload.grade, payload.basis)
    if result is None:
        return GradeResult(ok=False, message=message)
    return GradeResult(**result)


@router.get("/todos")
def list_todos() -> dict[str, Any]:
    """处置待办：同一台设备的故障合并成一条待办，被挂起的故障单独列出。"""
    return service.todos()


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出故障登记清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "fault", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条设备故障明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"设备故障 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条设备故障，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="设备故障已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条设备故障执行确认定级、提交恢复、挂起故障；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
