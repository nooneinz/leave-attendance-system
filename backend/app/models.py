from datetime import datetime, date, timedelta, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
from . import config

ROLES = ["employee", "manager", "hr", "admin"]
OM_TZ = timezone(timedelta(hours=config.TZ_OFFSET_HOURS))


def now_om() -> datetime:
    """الوقت الحالي في مسقط (بدون tzinfo ليُخزَّن كما هو)."""
    return datetime.now(OM_TZ).replace(tzinfo=None, microsecond=0)


def today_om() -> date:
    return now_om().date()


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    min_coverage_pct: Mapped[float] = mapped_column(Float, default=60)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="employee")
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    monthly_salary: Mapped[float] = mapped_column(Float, default=0)  # ريال عماني
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_om)
    department = relationship("Department", lazy="joined")


class LeaveType(Base):
    __tablename__ = "leave_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    annual_quota: Mapped[float] = mapped_column(Float, default=0)
    accrues_monthly: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_balance: Mapped[bool] = mapped_column(Boolean, default=True)
    calendar_days: Mapped[bool] = mapped_column(Boolean, default=False)  # تُحسب كل الأيام بما فيها الإجازة الأسبوعية
    auto_approvable: Mapped[bool] = mapped_column(Boolean, default=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LeaveLedger(Base):
    __tablename__ = "leave_ledger"
    __table_args__ = (UniqueConstraint("user_id", "type_id", "period_key", name="uq_ledger_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"))
    delta: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(200))
    period_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    request_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=now_om)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|approved|rejected|cancelled
    current_level: Mapped[int] = mapped_column(Integer, default=0)
    agent_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_om)
    user = relationship("User", lazy="joined")
    type = relationship("LeaveType", lazy="joined")
    approvals = relationship("LeaveApproval", cascade="all, delete-orphan", lazy="selectin", order_by="LeaveApproval.level")


class LeaveApproval(Base):
    __tablename__ = "leave_approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("leave_requests.id"))
    level: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_name: Mapped[str] = mapped_column(String(120), default="")
    decision: Mapped[str] = mapped_column(String(12), default="pending")
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Holiday(Base):
    __tablename__ = "holidays"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(120))


class Punch(Base):
    __tablename__ = "punches"
    __table_args__ = (UniqueConstraint("user_id", "ts", name="uq_punch"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(20), default="web")  # web|device|import
    device_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AttendanceDay(Base):
    __tablename__ = "attendance_days"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_att_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    first_in: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_out: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_minutes: Mapped[int] = mapped_column(Integer, default=0)
    # present|late|absent|incomplete|leave|weekend|holiday
    status: Mapped[str] = mapped_column(String(12), default="present")
    leave_type: Mapped[str] = mapped_column(String(20), default="")


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))


class JobRun(Base):
    __tablename__ = "job_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), index=True)
    started: Mapped[datetime] = mapped_column(DateTime, default=now_om)
    finished: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="running")
    detail: Mapped[str] = mapped_column(Text, default="")
    trigger: Mapped[str] = mapped_column(String(20), default="schedule")


class AgentReport(Base):
    __tablename__ = "agent_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    period_from: Mapped[date] = mapped_column(Date)
    period_to: Mapped[date] = mapped_column(Date)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_om)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=now_om)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_name: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(300))
    leave_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_om)
