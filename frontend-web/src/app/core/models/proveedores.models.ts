/**
 * CU-07 · Gestionar proveedores — modelos del contrato.
 *
 * Espejo de `backend/app/modules/organizacion/proveedores_schemas.py`.
 *
 * Archivo propio y no dentro de `organizacion.models.ts` por el mismo motivo
 * que en el backend: el CU-06 se está implementando en paralelo sobre ese
 * archivo, y así las dos ramas no comparten ninguna línea.
 */

/** Fila del listado de proveedores (paso 2 del flujo principal). */
export interface Proveedor {
  id: number;
  razon_social: string;
  identificacion_tributaria: string;
  contacto: string | null;
  telefono: string | null;
  /** Correo de contacto comercial. No sirve para iniciar sesión. */
  correo: string | null;
  direccion: string | null;
  activo: boolean;

  /** Vínculo con un usuario del sistema (flujo alternativo 3c). */
  usuario_id: number | null;
  tiene_acceso: boolean;
  /** Correo con el que inicia sesión, si tiene acceso habilitado. */
  correo_acceso: string | null;
}

/** Alta de proveedor (paso 4). */
export interface ProveedorCrear {
  razon_social: string;
  identificacion_tributaria: string;
  contacto?: string | null;
  telefono?: string | null;
  correo?: string | null;
  direccion?: string | null;
  activo?: boolean;
}

/** Edición (flujo alternativo 3a). Solo viaja lo que cambió. */
export interface ProveedorEditar {
  razon_social?: string;
  identificacion_tributaria?: string;
  contacto?: string | null;
  telefono?: string | null;
  correo?: string | null;
  direccion?: string | null;
}

/** Habilitar acceso al Proveedor (flujo alternativo 3c). */
export interface AccesoProveedor {
  correo: string;
  contrasena: string;
  nombres: string;
  apellidos: string;
}

/** Filtros del listado. */
export interface FiltrosProveedores {
  busqueda?: string;
  activo?: boolean;
}
