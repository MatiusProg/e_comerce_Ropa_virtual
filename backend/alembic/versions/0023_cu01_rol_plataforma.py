"""0023 - CU-01 Gestionar empresas: el rol del administrador de la plataforma.

`ADMIN_PLATAFORMA` opera por encima de las empresas: registra empresas, define
planes y asigna suscripciones. No pertenece a ninguna empresa
(`usuario.empresa_id` en NULL) y trabaja en modo plataforma (ver
app/core/tenencia.py).

La cuenta NO se crea acá: una migración no puede llevar una contraseña. La
crea `python -m app.db.seed_plataforma` con PLATAFORMA_ADMIN_CORREO y
PLATAFORMA_ADMIN_CLAVE.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023_cu01_rol_plataforma"
down_revision: str | None = "0022_multitenant_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO rol (nombre, descripcion) "
        "SELECT 'ADMIN_PLATAFORMA', 'Administra la plataforma SaaS: empresas, planes y suscripciones' "
        "WHERE NOT EXISTS (SELECT 1 FROM rol WHERE nombre = 'ADMIN_PLATAFORMA')"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM rol WHERE nombre = 'ADMIN_PLATAFORMA' "
        "AND NOT EXISTS (SELECT 1 FROM usuario u WHERE u.rol_id = rol.id)"
    )
