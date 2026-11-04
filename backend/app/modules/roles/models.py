"""
P17 - Roles y permisos por empresa / CU-41  |  capa: modelo

`rol_empresa`: un rol propio de una empresa, que parte de un rol base del
personal y conserva solo algunos de sus permisos (ver `app/core/permisos.py`).
`rol_empresa_permiso`: qué permisos del catálogo tiene cada rol propio.

Las dos son tablas de empresa (RLS). El catálogo de permisos NO es una tabla:
lo define el sistema en código, porque cada permiso tiene que corresponder a
rutas que el backend sabe cuidar; la columna `permiso` guarda su código y el
servicio valida que exista.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base, DeEmpresa


class RolEmpresa(DeEmpresa, Auditoria, Base):
    __tablename__ = "rol_empresa"
    __table_args__ = (
        CheckConstraint(
            "rol_base IN ('ADMINISTRADOR', 'ENCARGADO', 'CAJERO')", name="rol_base_valido"
        ),
        UniqueConstraint("empresa_id", "nombre", name="uq_rol_empresa_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[str | None] = mapped_column(String(150))
    #: No se cambia después del alta: el personal que lo tiene es de ese rol.
    rol_base: Mapped[str] = mapped_column(String(15))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    permisos: Mapped[list["RolEmpresaPermiso"]] = relationship(
        back_populates="rol", cascade="all, delete-orphan", lazy="selectin"
    )


class RolEmpresaPermiso(DeEmpresa, Base):
    __tablename__ = "rol_empresa_permiso"
    __table_args__ = (
        UniqueConstraint("rol_empresa_id", "permiso", name="uq_rol_empresa_permiso"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rol_empresa_id: Mapped[int] = mapped_column(
        ForeignKey("rol_empresa.id", ondelete="CASCADE"), index=True
    )
    permiso: Mapped[str] = mapped_column(String(60))

    rol: Mapped[RolEmpresa] = relationship(back_populates="permisos")


__all__ = ["RolEmpresa", "RolEmpresaPermiso"]
