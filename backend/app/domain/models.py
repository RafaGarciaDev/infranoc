import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Enum as SQLEnum,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from enum import Enum as PyEnum
from app.domain.enums import AssetStatus, AssetType, Criticality, Layer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    ...


def _uuid():
    return uuid.uuid4()


def _now():
    return datetime.now(timezone.utc)


# Mixin de auditoria
class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=_now)
    updated_by: Mapped[str | None] = mapped_column(String(256), nullable=True)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base, AuditMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(256), index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(256))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(64))
    users: Mapped[list[User]] = relationship(secondary="user_roles", back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(64), unique=True)  # "cmdb.write"
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)


# tabelas de associacao
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(128))
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    details: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON, sem segredos
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ============================================================
# Fase 3 — Bloco 4: Alertas vindos do AlertManager
# ============================================================
# Severity: critical | high | warning | info
# Status:   firing | resolved
# Categoria: OT | energia | ti_rede | AD  (livre, alinhado com rules do Prometheus)


class Alert(Base, AuditMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "fingerprint", name="uq_alerts_tenant_fingerprint"),
        Index("ix_alerts_tenant_status", "tenant_id", "status"),
        Index("ix_alerts_tenant_starts_at", "tenant_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    # Identificador estavel gerado pelo AlertManager (hash de labels).
    fingerprint: Mapped[str] = mapped_column(String(64))

    # Campos derivados das labels/annotations do payload
    alertname: Mapped[str] = mapped_column(String(128), index=True)
    asset: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    categoria: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    impacto_negocio: Mapped[str | None] = mapped_column(Text, nullable=True)
    generator_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ciclo de vida
    status: Mapped[str] = mapped_column(String(16), default="firing", index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Payload completo pra debug / analise (labels e annotations)
    labels: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    annotations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Reconhecimento manual (ack)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(256), nullable=True)

    status_history: Mapped[list["AlertStatusChange"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="AlertStatusChange.changed_at",
    )


class AlertStatusChange(Base):
    __tablename__ = "alert_status_changes"
    __table_args__ = (
        Index("ix_alert_status_changes_alert_id", "alert_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE")
    )
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)

    alert: Mapped[Alert] = relationship(back_populates="status_history")

# ============================================================
# Fase 4.5 - CMDB: Setores (ISA-95 Level 3) e hierarquia
# ============================================================
class HierarchyLevel(str, PyEnum):
    Area = "Area"
    Line = "Line"
    Equipment = "Equipment"


class Sector(Base, AuditMixin):
    """Setor/area produtiva (ISA-95 Level 3 - Area)."""
    __tablename__ = "sectors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_sectors_tenant_code"),
        Index("ix_sectors_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), index=True
    )

    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metricas agregadas (populadas por job futuro)
    oee_target: Mapped[float | None] = mapped_column(nullable=True)

    assets: Mapped[list["Asset"]] = relationship(back_populates="sector")


# ============================================================
# Fase 4 - CMDB: Ativos
# ============================================================
class Asset(Base, AuditMixin):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_assets_tenant_name"),
        Index("ix_assets_tenant_type", "tenant_id", "type"),
        Index("ix_assets_tenant_site", "tenant_id", "site"),
        Index("ix_assets_tenant_layer", "tenant_id", "layer"),
        Index("ix_assets_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    name: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType, name="asset_type"))
    layer: Mapped[Layer] = mapped_column(SQLEnum(Layer, name="asset_layer"))
    site: Mapped[str] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[AssetStatus] = mapped_column(
        SQLEnum(AssetStatus, name="asset_status"),
        default=AssetStatus.Active,
    )
    criticality: Mapped[Criticality] = mapped_column(
        SQLEnum(Criticality, name="asset_criticality"),
        default=Criticality.Medium,
    )

    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(128), nullable=True)

    owner_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    owner_team: Mapped[str | None] = mapped_column(String(128), nullable=True)

    sector_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sectors.id"), nullable=True, index=True
    )
    sector: Mapped["Sector | None"] = relationship(back_populates="assets")

    hierarchy_level: Mapped[HierarchyLevel | None] = mapped_column(
        SQLEnum(HierarchyLevel, name="hierarchy_level"), nullable=True
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent: Mapped["Asset | None"] = relationship(
        "Asset",
        remote_side="Asset.id",
        back_populates="children",
    )
    children: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="parent",
        cascade="save-update",
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
