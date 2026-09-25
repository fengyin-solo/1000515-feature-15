"""故障登记业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.services.dispose import DisposeService
from app.store import store

MODULE = "fault"
REQUIRED_FIELDS = ["故障编号", "发生设备", "故障现象"]
STATUS_ORDER = ["待定级", "已定级", "处置中", "已恢复", "已挂起"]
ACTION_RULES = {"确认定级": "已定级", "提交恢复": "已恢复", "挂起故障": "已挂起"}
NEGATIVE_ACTIONS = []

# 统一定级规则：同一份定级依据下，同样的现象必须定出同样的等级，
# 避免不同班组各定各的（有的定事故、有的定一般）。
# 按 (等级, 现象关键词, 处置时限小时) 依次匹配，都不命中时兜底为「一般」。
GRADE_TABLE = [
    ("事故", ("中断", "脱轨", "冲突", "挤岔", "冒进", "追尾"), 4),
    ("障碍", ("失效", "熄灭", "停用", "不良", "异常", "报警", "红光带"), 24),
    ("一般", (), 72),
]
DEFAULT_GRADE = GRADE_TABLE[-1]

dispose_service = DisposeService()


def _grade_for(phenomenon: str, scope: str) -> tuple[str, int]:
    """按统一规则表定级：同一份依据、同样的现象，结果必然一致。"""
    text = f"{phenomenon}{scope}"
    for grade, keywords, hours in GRADE_TABLE:
        if keywords and any(keyword in text for keyword in keywords):
            return grade, hours
    return DEFAULT_GRADE[0], DEFAULT_GRADE[2]


def _deadline(occurred: Any, hours: int) -> str:
    """处理期限跟着等级走：发生时间 + 等级对应时限；时间缺失时退化为时限说明。"""
    text = str(occurred or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            base = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return (base + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    return f"定级后{hours}小时内"


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
        entry["故障状态"] = STATUS_ORDER[0]
        entry["定级结果"] = ""
        entry["定级依据"] = ""
        entry["处理期限"] = ""
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
        # 列表里的故障状态列始终跟状态流转对得上
        entry["故障状态"] = target
        return entry, f"设备故障已{action}"

    def grade_entries(self, ids: list[int], basis: str) -> dict[str, Any]:
        """批量定级：多选故障按同一份定级依据统一套用，逐条给出结果。

        - 已恢复的故障不允许再定级；
        - 故障现象为空的无法对照依据，逐条说明原因；
        - 已挂起的故障不参与定级，单独列出；
        - 定级成功的按发生设备合并成一条处置待办。
        """
        results: list[dict[str, Any]] = []
        suspended: list[dict[str, Any]] = []
        graded: list[dict[str, Any]] = []
        for raw_id in ids:
            try:
                entry_id = int(raw_id)
            except (TypeError, ValueError):
                results.append({"id": raw_id, "ok": False, "message": f"故障标识「{raw_id}」不是有效编号"})
                continue
            entry = store.find(MODULE, entry_id)
            if entry is None:
                results.append({"id": entry_id, "ok": False, "message": f"设备故障 {entry_id} 不存在或已归档"})
                continue
            item = {"id": entry_id, "故障编号": entry.get("故障编号"), "发生设备": entry.get("发生设备")}
            status = entry.get("status")
            if status == "已恢复":
                results.append({**item, "ok": False, "message": "故障已恢复，不允许再定级"})
                continue
            if status == "已挂起":
                message = "故障已挂起，不参与本次批量定级，单独列出"
                suspended.append({**item, "message": message})
                results.append({**item, "ok": False, "suspended": True, "message": message})
                continue
            phenomenon = str(entry.get("故障现象") or "").strip()
            if not phenomenon:
                results.append({**item, "ok": False, "message": "故障现象为空，无法对照定级依据定级，请先补充故障现象"})
                continue
            grade, hours = _grade_for(phenomenon, str(entry.get("影响范围") or ""))
            deadline = _deadline(entry.get("发生时间"), hours)
            entry["定级结果"] = grade
            entry["定级依据"] = basis
            entry["处理期限"] = deadline
            entry["status"] = "已定级"
            entry["故障状态"] = "已定级"
            entry["pending"] = True
            graded.append(entry)
            results.append({
                **item,
                "ok": True,
                "定级结果": grade,
                "处理期限": deadline,
                "message": f"按统一定级依据定为「{grade}」，处理期限 {deadline}",
            })
        todos = self._merge_todos(graded, basis)
        done = len(graded)
        skipped = len(results) - done
        return {
            "ok": True,
            "message": f"批量定级完成：成功 {done} 条，未定级 {skipped} 条，合并生成 {len(todos)} 条处置待办",
            "basis": basis,
            "results": results,
            "todos": todos,
            "suspended": suspended,
        }

    def _merge_todos(self, graded: list[dict[str, Any]], basis: str) -> list[dict[str, Any]]:
        """同一台设备同时处置的多条故障合并成一条待办；挂起的不进待办。"""
        groups: dict[str, list[dict[str, Any]]] = {}
        for entry in graded:
            device = str(entry.get("发生设备") or "").strip() or "未指明设备"
            groups.setdefault(device, []).append(entry)
        todos: list[dict[str, Any]] = []
        for device, entries in groups.items():
            numbers = [str(entry.get("故障编号") or "") for entry in entries]
            # 待办期限取同组里最早的处理期限，保证最急的先办
            deadline = min((str(entry.get("处理期限") or "") for entry in entries), default="")
            todos.append(dispose_service.merge_todo(device, numbers, basis=basis, deadline=deadline))
        return todos
