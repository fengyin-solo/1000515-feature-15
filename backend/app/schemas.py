"""接口出入参模型：列表分页、动作结果与各模块的明细结构。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class ActionResult(BaseModel):
    ok: bool
    message: str
    entry: dict[str, Any] | None = None


class EntryPayload(BaseModel):
    """登记或修改一条业务记录时提交的字段集合。"""

    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None


class GradePayload(BaseModel):
    """批量定级提交：勾选的故障 id 集合，加上统一套用的定级等级与定级依据。"""

    ids: list[int] = Field(default_factory=list)
    grade: str = ""
    basis: str = ""


class GradeResult(BaseModel):
    """批量定级结果：逐条给出结论，并带上合并后的处置待办与单独列出的挂起清单。"""

    ok: bool
    message: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    todos: list[dict[str, Any]] = Field(default_factory=list)
    suspended: list[dict[str, Any]] = Field(default_factory=list)



class SectionEntry(BaseModel):
    """线路区段明细结构。"""

    field_0: str | None = None  # 区段编码
    field_1: str | None = None  # 区段名称
    field_2: str | None = None  # 所属线路
    field_3: str | None = None  # 起止里程
    field_4: str | None = None  # 管辖工区
    field_5: str | None = None  # 投运日期
    field_6: str | None = None  # 限速值
    field_7: str | None = None  # 区段状态

class SignalEntry(BaseModel):
    """信号机明细结构。"""

    field_0: str | None = None  # 设备编号
    field_1: str | None = None  # 设备类型
    field_2: str | None = None  # 安装位置
    field_3: str | None = None  # 显示制式
    field_4: str | None = None  # 所属区段
    field_5: str | None = None  # 上次检修日
    field_6: str | None = None  # 下次检修日
    field_7: str | None = None  # 设备状态

class SwitchEntry(BaseModel):
    """转辙机明细结构。"""

    field_0: str | None = None  # 设备编号
    field_1: str | None = None  # 设备型号
    field_2: str | None = None  # 安装道岔
    field_3: str | None = None  # 动作电流
    field_4: str | None = None  # 转换时间
    field_5: str | None = None  # 所属区段
    field_6: str | None = None  # 上次检修日
    field_7: str | None = None  # 设备状态

class TrackEntry(BaseModel):
    """轨道电路明细结构。"""

    field_0: str | None = None  # 设备编号
    field_1: str | None = None  # 制式类型
    field_2: str | None = None  # 区段长度
    field_3: str | None = None  # 分路灵敏度
    field_4: str | None = None  # 所属区段
    field_5: str | None = None  # 上次测试日
    field_6: str | None = None  # 下次测试日
    field_7: str | None = None  # 设备状态

class InterlockEntry(BaseModel):
    """联锁设备明细结构。"""

    field_0: str | None = None  # 设备编号
    field_1: str | None = None  # 联锁类型
    field_2: str | None = None  # 控制范围
    field_3: str | None = None  # 软件版本
    field_4: str | None = None  # 所属车站
    field_5: str | None = None  # 上次检修日
    field_6: str | None = None  # 责任人
    field_7: str | None = None  # 设备状态

class AtpEntry(BaseModel):
    """防护设备明细结构。"""

    field_0: str | None = None  # 设备编号
    field_1: str | None = None  # 防护等级
    field_2: str | None = None  # 覆盖区段
    field_3: str | None = None  # 应答器数量
    field_4: str | None = None  # 所属线路
    field_5: str | None = None  # 版本号
    field_6: str | None = None  # 责任人
    field_7: str | None = None  # 防护状态

class PlanEntry(BaseModel):
    """检修计划明细结构。"""

    field_0: str | None = None  # 计划编号
    field_1: str | None = None  # 检修类型
    field_2: str | None = None  # 检修对象
    field_3: str | None = None  # 计划日期
    field_4: str | None = None  # 检修周期
    field_5: str | None = None  # 作业班组
    field_6: str | None = None  # 计划工时
    field_7: str | None = None  # 计划状态

class TaskEntry(BaseModel):
    """检修任务明细结构。"""

    field_0: str | None = None  # 任务编号
    field_1: str | None = None  # 关联计划
    field_2: str | None = None  # 检修人员
    field_3: str | None = None  # 开始时间
    field_4: str | None = None  # 完成时间
    field_5: str | None = None  # 检修项目数
    field_6: str | None = None  # 遗留问题数
    field_7: str | None = None  # 任务状态

class FaultEntry(BaseModel):
    """设备故障明细结构。"""

    field_0: str | None = None  # 故障编号
    field_1: str | None = None  # 发生设备
    field_2: str | None = None  # 故障现象
    field_3: str | None = None  # 影响范围
    field_4: str | None = None  # 发生时间
    field_5: str | None = None  # 报告人
    field_6: str | None = None  # 恢复时间
    field_7: str | None = None  # 故障状态

class DisposeEntry(BaseModel):
    """处置单明细结构。"""

    field_0: str | None = None  # 处置单号
    field_1: str | None = None  # 关联故障
    field_2: str | None = None  # 处置措施
    field_3: str | None = None  # 更换器材
    field_4: str | None = None  # 处置人员
    field_5: str | None = None  # 完成时间
    field_6: str | None = None  # 验收人员
    field_7: str | None = None  # 处置状态

class SpareEntry(BaseModel):
    """器材领用单明细结构。"""

    field_0: str | None = None  # 领用单号
    field_1: str | None = None  # 器材名称
    field_2: str | None = None  # 器材规格
    field_3: str | None = None  # 领用数量
    field_4: str | None = None  # 领用人员
    field_5: str | None = None  # 领用日期
    field_6: str | None = None  # 所属工区
    field_7: str | None = None  # 领用状态

class MeasureEntry(BaseModel):
    """测试单明细结构。"""

    field_0: str | None = None  # 测试单号
    field_1: str | None = None  # 测试项目
    field_2: str | None = None  # 测试设备
    field_3: str | None = None  # 测试值
    field_4: str | None = None  # 标准范围
    field_5: str | None = None  # 测试结论
    field_6: str | None = None  # 测试人员
    field_7: str | None = None  # 测试状态

class PatrolEntry(BaseModel):
    """巡视单明细结构。"""

    field_0: str | None = None  # 巡视单号
    field_1: str | None = None  # 巡视路线
    field_2: str | None = None  # 巡视人员
    field_3: str | None = None  # 巡视日期
    field_4: str | None = None  # 发现问题数
    field_5: str | None = None  # 整改项数
    field_6: str | None = None  # 巡视时长
    field_7: str | None = None  # 巡视状态

class WindowEntry(BaseModel):
    """天窗计划明细结构。"""

    field_0: str | None = None  # 天窗编号
    field_1: str | None = None  # 作业类型
    field_2: str | None = None  # 作业区段
    field_3: str | None = None  # 计划时段
    field_4: str | None = None  # 实际时段
    field_5: str | None = None  # 申请单位
    field_6: str | None = None  # 负责人
    field_7: str | None = None  # 天窗状态

class AlarmEntry(BaseModel):
    """报警事件明细结构。"""

    field_0: str | None = None  # 报警编号
    field_1: str | None = None  # 报警类型
    field_2: str | None = None  # 报警等级
    field_3: str | None = None  # 触发设备
    field_4: str | None = None  # 触发时间
    field_5: str | None = None  # 确认人员
    field_6: str | None = None  # 处置说明
    field_7: str | None = None  # 报警状态

class VerifyEntry(BaseModel):
    """验收单明细结构。"""

    field_0: str | None = None  # 验收单号
    field_1: str | None = None  # 关联任务
    field_2: str | None = None  # 验收项目
    field_3: str | None = None  # 验收标准
    field_4: str | None = None  # 验收结论
    field_5: str | None = None  # 验收人员
    field_6: str | None = None  # 验收日期
    field_7: str | None = None  # 验收状态

class ShiftEntry(BaseModel):
    """交接记录明细结构。"""

    field_0: str | None = None  # 交接编号
    field_1: str | None = None  # 值班班组
    field_2: str | None = None  # 值班人员
    field_3: str | None = None  # 交接时间
    field_4: str | None = None  # 交接事项
    field_5: str | None = None  # 遗留事项
    field_6: str | None = None  # 接收人员
    field_7: str | None = None  # 交接状态

class AssessEntry(BaseModel):
    """评估记录明细结构。"""

    field_0: str | None = None  # 评估编号
    field_1: str | None = None  # 评估对象
    field_2: str | None = None  # 评估周期
    field_3: str | None = None  # 健康分值
    field_4: str | None = None  # 风险等级
    field_5: str | None = None  # 评估人员
    field_6: str | None = None  # 评估结论
    field_7: str | None = None  # 评估状态
