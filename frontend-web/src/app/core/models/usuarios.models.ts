/**
 * CU-03 · Gestionar usuarios y roles — modelos del contrato.
 *
 * Espejo de los esquemas de `backend/app/modules/seguridad/schemas.py`.
 */
import type { Rol } from './auth.models';

/** Un rol asignable. `exige_sucursal` decide si el formulario pide sucursal. */
export interface RolAsignable {
  id: number;
  nombre: Rol;
  descripcion: string | null;
  exige_sucursal: boolean;
}

/** Fila del listado de usuarios. */
export interface UsuarioResumen {
  id: number;
  correo: string;
  nombres: string;
  apellidos: string;
  rol: Rol;
  sucursal_id: number | null;
  sucursal: string | null;
  activo: boolean;
  creado_en: string;
}

/** Página del listado. */
export interface PaginaUsuarios {
  items: UsuarioResumen[];
  total: number;
  pagina: number;
  tamano: number;
  paginas: number;
}

/** Filtros del listado (paso 2 del flujo principal). */
export interface FiltrosUsuarios {
  busqueda?: string;
  rol?: string;
  activo?: boolean;
  pagina?: number;
  tamano?: number;
}

/** Alta de usuario. */
export interface UsuarioCrear {
  nombres: string;
  apellidos: string;
  correo: string;
  contrasena: string;
  rol: Rol;
  sucursal_id?: number | null;
  documento?: string | null;
  fecha_ingreso?: string | null;
}

/**
 * Edición. Todo opcional: solo viaja lo que cambió.
 * La contraseña se omite si no se quiere cambiar (flujo alternativo 3a).
 */
export interface UsuarioEditar {
  nombres?: string;
  apellidos?: string;
  correo?: string;
  contrasena?: string;
  rol?: Rol;
  sucursal_id?: number | null;
}

/** Etiqueta legible de cada rol, para no mostrar el código en mayúsculas. */
export const ETIQUETA_ROL: Record<Rol, string> = {
  ADMINISTRADOR: 'Administrador',
  CLIENTE: 'Cliente',
  ENCARGADO: 'Encargado de sucursal',
  CAJERO: 'Cajero',
  PROVEEDOR: 'Proveedor',
};
