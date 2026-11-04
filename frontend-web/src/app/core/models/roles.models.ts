/**
 * 3ra presentación · CU-41 Gestionar roles y permisos de la empresa.
 * Espejo de `backend/app/modules/roles/schemas.py`.
 */

export type RolBase = 'ADMINISTRADOR' | 'ENCARGADO' | 'CAJERO';

export interface PermisoDelCatalogo {
  codigo: string;
  nombre: string;
  area: string;
  roles_base: RolBase[];
  funcion: string | null;
  /** RN-22: si el plan de la empresa la incluye. */
  incluido_en_plan: boolean;
}

export interface RolEmpresa {
  id: number;
  nombre: string;
  descripcion: string | null;
  rol_base: RolBase;
  activo: boolean;
  permisos: string[];
  personas: number;
}

export interface GuardarRol {
  nombre: string;
  descripcion: string | null;
  rol_base: RolBase;
  permisos: string[];
}

export interface Persona {
  usuario_id: number;
  nombre: string;
  correo: string;
  rol_base: RolBase;
  sucursal: string | null;
  rol_empresa_id: number | null;
  rol_empresa: string | null;
}
