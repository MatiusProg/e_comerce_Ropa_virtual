"""
P17 - Roles y permisos por empresa / CU-41  |  capa: esquemas
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

RolBase = Literal["ADMINISTRADOR", "ENCARGADO", "CAJERO"]


class PermisoOut(BaseModel):
    codigo: str
    nombre: str
    area: str
    roles_base: list[str]
    funcion: str | None
    #: RN-22: si el plan de la empresa la incluye. Sin función, siempre True.
    incluido_en_plan: bool


class RolIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=40)
    descripcion: str | None = Field(default=None, max_length=150)
    rol_base: RolBase
    permisos: list[str] = Field(default_factory=list, max_length=60)

    @field_validator("nombre")
    @classmethod
    def _recortar(cls, v: str) -> str:
        return " ".join(v.split())


class RolEditarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=40)
    descripcion: str | None = Field(default=None, max_length=150)
    permisos: list[str] | None = Field(default=None, max_length=60)


class EstadoIn(BaseModel):
    activo: bool


class RolOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    rol_base: str
    activo: bool
    permisos: list[str]
    personas: int


class PersonaOut(BaseModel):
    """Alguien del personal, con su rol base y su rol propio si tiene."""

    usuario_id: int
    nombre: str
    correo: str
    rol_base: str
    sucursal: str | None
    rol_empresa_id: int | None
    rol_empresa: str | None


class AsignacionIn(BaseModel):
    usuario_id: int = Field(ge=1)
    #: Nulo: le quita el rol propio y vuelve a tener todo lo de su rol base.
    rol_empresa_id: int | None = Field(default=None, ge=1)
