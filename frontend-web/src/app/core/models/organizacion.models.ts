/**
 * P2 · Organización — modelos del contrato.
 *
 * Espejo de los esquemas de `backend/app/modules/organizacion/schemas.py`.
 * Cubre CU-05; CU-06 y CU-07 agregan los suyos cuando les toque.
 */

/**
 * Sucursal reducida a lo que hace falta para elegirla en un selector.
 *
 * Es el subconjunto de `Sucursal` que usa el formulario de CU-03. El endpoint
 * es el mismo y devuelve la fila completa: acá solo se declara lo que ese
 * formulario lee.
 */
export interface SucursalBreve {
  id: number;
  nombre: string;
  ciudad: string;
}

/** Fila del listado de ciudades, con el recuento de sus sucursales. */
export interface Ciudad {
  id: number;
  nombre: string;
  departamento: string;
  /** Total, incluidas las dadas de baja: mientras haya alguna no se puede eliminar. */
  sucursales: number;
  /** Solo las activas: son las que disparan la excepción E2. */
  sucursales_activas: number;
}

/** Alta de ciudad (flujo alternativo 3a). */
export interface CiudadCrear {
  nombre: string;
  departamento: string;
}

/** Edición de ciudad. Solo viaja lo que cambió. */
export interface CiudadEditar {
  nombre?: string;
  departamento?: string;
}

/**
 * Fila del listado de sucursales (paso 2 del flujo principal).
 *
 * Los horarios llegan del servidor como `HH:MM:SS`; el campo `<input
 * type="time">` los quiere como `HH:MM`. La conversión vive en el formulario.
 */
export interface Sucursal {
  id: number;
  nombre: string;
  ciudad_id: number;
  ciudad: string;
  direccion: string;
  telefono: string | null;
  horario_apertura: string;
  horario_cierre: string;
  capacidad_vestidores: number;
  activa: boolean;
}

/** Alta de sucursal (paso 4). */
export interface SucursalCrear {
  ciudad_id: number;
  nombre: string;
  direccion: string;
  telefono?: string | null;
  horario_apertura: string;
  horario_cierre: string;
  capacidad_vestidores: number;
  activa?: boolean;
}

/** Edición de sucursal (flujo alternativo 3b). */
export interface SucursalEditar {
  ciudad_id?: number;
  nombre?: string;
  direccion?: string;
  telefono?: string | null;
  horario_apertura?: string;
  horario_cierre?: string;
  capacidad_vestidores?: number;
}

/** Filtros del listado de sucursales (paso 2). */
export interface FiltrosSucursales {
  busqueda?: string;
  ciudad_id?: number;
  activa?: boolean;
}

/**
 * Capacidad mínima de vestidores (excepción E3).
 *
 * Igual a `CAPACIDAD_VESTIDORES_MINIMA` del backend. Se valida en los dos
 * lados: acá para señalar el campo sin ir al servidor, allá porque el cliente
 * no es de fiar.
 */
export const CAPACIDAD_VESTIDORES_MINIMA = 1;
