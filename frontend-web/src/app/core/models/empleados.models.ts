/**
 * CU-06 · Gestionar empleados — modelos del contrato.
 *
 * Espejo de `backend/app/modules/organizacion/empleados/schemas.py`. Si cambia
 * uno, cambia el otro: son las dos caras del mismo contrato (RNF07).
 *
 * Archivo propio, y no un bloque más en `organizacion.models.ts`, por el mismo
 * motivo que el subpaquete del backend: el CU-07 se desarrolla en paralelo
 * sobre el mismo paquete. Ver §6.11.5 de `docs/06-decisiones-tecnicas.md`.
 */
import type { Rol } from './auth.models';

/** Los dos cargos que admite la tabla (CHECK `ck_empleado_cargo`). */
export type Cargo = 'ENCARGADO' | 'CAJERO';

/** Cómo se nombra cada cargo en la interfaz. */
export const ETIQUETA_CARGO: Record<Cargo, string> = {
  ENCARGADO: 'Encargado de sucursal',
  CAJERO: 'Cajero',
};

/** Fila del listado de empleados (paso 2 del flujo principal). */
export interface Empleado {
  id: number;
  usuario_id: number;
  nombres: string;
  apellidos: string;
  correo: string;
  documento: string;
  telefono: string | null;
  cargo: Cargo;
  sucursal_id: number;
  sucursal: string;
  ciudad: string;
  fecha_ingreso: string;
  fecha_baja: string | null;
  /** En actividad: no tiene fecha de baja. */
  activo: boolean;
  /**
   * Estado de la cuenta. Puede diferir de `activo`: dar de baja al empleado
   * desactiva su usuario, pero desactivar el usuario desde CU-03 no da de baja
   * al empleado.
   */
  usuario_activo: boolean;
}

/** Cuenta existente sin ficha de empleado (flujo alternativo 3c). */
export interface UsuarioVinculable {
  id: number;
  correo: string;
  nombres: string;
  apellidos: string;
  rol: Rol;
}

/**
 * Alta de un empleado. Los dos caminos de la ficha son excluyentes:
 * o `usuario_id`, o los cuatro datos de la cuenta nueva.
 */
export interface EmpleadoCrear {
  documento: string;
  telefono: string | null;
  cargo: Cargo;
  sucursal_id: number;
  fecha_ingreso: string;
  usuario_id?: number;
  nombres?: string;
  apellidos?: string;
  correo?: string;
  contrasena?: string;
}

/** Edición y reasignación (flujo alternativo 3a). Solo viaja lo que cambió. */
export interface EmpleadoEditar {
  documento?: string;
  telefono?: string | null;
  cargo?: Cargo;
  sucursal_id?: number;
  fecha_ingreso?: string;
  nombres?: string;
  apellidos?: string;
}

/** Filtros del listado (paso 2). */
export interface FiltrosEmpleados {
  busqueda?: string;
  sucursal_id?: number;
  cargo?: Cargo;
  activo?: boolean;
}
