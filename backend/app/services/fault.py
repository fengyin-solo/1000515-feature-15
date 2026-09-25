"""故障登记业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.store import store

MODULE = "fault"
REQUIRED_FIELDS = ["故障编号", "发生设备", "故障现象"]
STATUS_ORDER = ["待定级", "已定级", "处置中", "已恢复", "已挂起"]
ACTION_RULES = {"确认定级": "已定级", "提交恢复": "已恢复", "挂起故障": "已挂起"}
NEGATIVE_ACTIONS = []

# 批量定级：同一份定级依据可套用到多条故障，等级决定处理期限（天）。
GRADE_OPTIONS = ["事故", "障碍", "一般故障"]
GRADE_DEADLINE_DAYS = {"事故": 1, "障碍": 2, "一般故障": 3}
GRADE_SEVERITY = {grade: index for index, grade in enumerate(GRADE_OPTIONS)}
ACTIVE_STATUSES = ("已定级", "处置中")


class FaultService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("故障编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"设备故障 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于故障登记可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"设备故障已{action}"

    def grade_batch(
        self,
        ids: list[int],
        grade: str,
        basis: str,
    ) -> tuple[dict[str, Any] | None, str]:
        """多选故障按同一份定级依据套用，逐条给出结果；参数不合法时整体拦下。"""
        grade = grade.strip()
        basis = basis.strip()
        if not ids:
            return None, "请先勾选需要定级的故障"
        if grade not in GRADE_OPTIONS:
            return None, f"定级等级「{grade or '空'}」不在允许范围，可选：{'、'.join(GRADE_OPTIONS)}"
        if not basis:
            return None, "定级依据不能为空，请填写本次统一套用的定级依据"

        results: list[dict[str, Any]] = []
        graded: list[dict[str, Any]] = []
        for entry_id in ids:
            entry = store.find(MODULE, entry_id)
            if entry is None:
                results.append({"id": entry_id, "ok": False, "message": f"设备故障 {entry_id} 不存在或已归档"})
                continue
            label = str(entry.get("故障编号") or f"故障 {entry_id}")
            status = str(entry.get("status") or "")
            if status == "已恢复":
                results.append({"id": entry_id, "ok": False, "message": f"{label} 已恢复，不允许再定级"})
                continue
            if status == "已挂起":
                results.append({"id": entry_id, "ok": False, "message": f"{label} 已挂起，不参与本次定级，已在挂起清单中单独列出"})
                continue
            if not str(entry.get("故障现象") or "").strip():
                results.append({"id": entry_id, "ok": False, "message": f"{label} 故障现象为空，无法套用定级依据，请先补录故障现象"})
                continue
            existing = str(entry.get("定级等级") or "").strip()
            if existing:
                results.append({"id": entry_id, "ok": False, "message": f"{label} 已定级为「{existing}」，定级结果保持不变"})
                continue
            deadline = (date.today() + timedelta(days=GRADE_DEADLINE_DAYS[grade])).isoformat()
            entry["定级等级"] = grade
            entry["定级依据"] = basis
            entry["处理期限"] = deadline
            entry["定级时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry["status"] = "已定级"
            entry["故障状态"] = "已定级"
            entry["pending"] = True
            graded.append(entry)
            results.append({
                "id": entry_id,
                "ok": True,
                "message": f"{label} 已定级为「{grade}」，处理期限 {deadline}",
                "entry": dict(entry),
            })

        done = len(graded)
        message = f"批量定级完成：成功 {done} 条、跳过 {len(results) - done} 条"
        if done:
            message += "，同一设备的故障已合并为一条待办"
        return {
            "ok": True,
            "message": message,
            "results": results,
            "todos": self._merge_todos(graded),
            "suspended": self._suspended_entries(),
        }, ""

    def todos(self) -> dict[str, Any]:
        """处置待办总览：已定级/处置中的故障按设备合并，被挂起的单独列出。"""
        rows = store.rows(MODULE)
        active = [row for row in rows if row.get("status") in ACTIVE_STATUSES]
        return {"todos": self._merge_todos(active), "suspended": self._suspended_entries()}

    def _merge_todos(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """同一台设备的多条故障合并成一条待办；等级取最重、期限取最早。"""
        groups: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            device = str(entry.get("发生设备") or "").strip() or "未填写设备"
            groups.setdefault(device, []).append(entry)
        todos: list[dict[str, Any]] = []
        for device, members in groups.items():
            grades = [str(m["定级等级"]) for m in members if m.get("定级等级")]
            level = min(grades, key=lambda g: GRADE_SEVERITY.get(g, len(GRADE_OPTIONS))) if grades else "未定级"
            deadlines = [str(m["处理期限"]) for m in members if m.get("处理期限")]
            todos.append({
                "发生设备": device,
                "故障编号": [m.get("故障编号") for m in members],
                "故障数量": len(members),
                "定级等级": level,
                "处理期限": min(deadlines) if deadlines else "",
            })
        return todos

    def _suspended_entries(self) -> list[dict[str, Any]]:
        """被挂起的故障单独列出，不并入处置待办。"""
        rows = [row for row in store.rows(MODULE) if row.get("status") == "已挂起"]
        return [
            {
                "id": row.get("id"),
                "故障编号": row.get("故障编号"),
                "发生设备": row.get("发生设备"),
                "故障现象": row.get("故障现象"),
                "发生时间": row.get("发生时间"),
                "说明": "故障已挂起，解除挂起后才能定级或恢复",
            }
            for row in rows
        ]
