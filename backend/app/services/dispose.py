"""故障处置业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "dispose"
REQUIRED_FIELDS = ["处置单号", "关联故障", "处置措施"]
STATUS_ORDER = ["待受理", "处置中", "待验收", "已验收"]
ACTION_RULES = {"受理处置": "处置中", "提交验收": "待验收", "确认验收": "已验收"}
NEGATIVE_ACTIONS = []

# 待办合并只针对还没办结的处置单；已验收的不再并入新故障
OPEN_STATUSES = ("待受理", "处置中")


class DisposeService:
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
            rows = [row for row in rows if keyword in str(row.get("处置单号", ""))]
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

    def merge_todo(
        self,
        device: str,
        fault_numbers: list[str],
        *,
        basis: str,
        deadline: str,
    ) -> dict[str, Any]:
        """同一台设备同时处置的多条故障合并成一条待办。

        该设备已有未办结的处置单时把新故障并进去，否则新建一条待办。
        """
        rows = store.rows(MODULE)
        numbers = [number for number in fault_numbers if number]
        for row in rows:
            if row.get("发生设备") != device or row.get("status") not in OPEN_STATUSES:
                continue
            existing = [part for part in str(row.get("关联故障") or "").split("、") if part]
            merged = existing + [number for number in numbers if number not in existing]
            row["关联故障"] = "、".join(merged)
            row["处置措施"] = f"按统一定级依据「{basis}」合并处置"
            if deadline and (not row.get("处理期限") or deadline < str(row.get("处理期限"))):
                row["处理期限"] = deadline
            return {
                "dispose_id": row.get("id"),
                "处置单号": row.get("处置单号"),
                "发生设备": device,
                "关联故障": merged,
                "处理期限": row.get("处理期限"),
                "merged": True,
                "message": f"{device} 的 {len(numbers)} 条故障并入已有待办 {row.get('处置单号')}",
            }
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["处置单号"] = f"DISP-{int(entry['id']):04d}"
        entry["发生设备"] = device
        entry["关联故障"] = "、".join(numbers)
        entry["处置措施"] = f"按统一定级依据「{basis}」合并处置"
        entry["处理期限"] = deadline
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return {
            "dispose_id": entry["id"],
            "处置单号": entry["处置单号"],
            "发生设备": device,
            "关联故障": numbers,
            "处理期限": deadline,
            "merged": False,
            "message": f"{device} 的 {len(numbers)} 条故障合并生成待办 {entry['处置单号']}",
        }

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"处置单 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于故障处置可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"处置单已{action}"
