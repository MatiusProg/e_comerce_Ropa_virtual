/**
 * CU-09 · Gestionar temporadas y colecciones — modelos del contrato.
 *
 * Espejo de `backend/app/modules/catalogo/temporadas_schemas.py`.
 *
 * Archivo propio y no dentro de un `catalogo.models.ts` compartido: el CU-08
 * se está implementando en paralelo sobre ese paquete, y así las dos ramas no
 * comparten ninguna línea. Es la misma separación que se usó en P2.
 */

/** Fila del listado de temporadas (paso 2 del flujo principal). */
export interface Temporada {
  id: number;
  nombre: string;
  descripcion: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  /** Abierta o cerrada. Es la columna que guarda el flujo alternativo 3b. */
  activa: boolean;
  /**
   * Abierta **y** corriendo hoy. No es una columna: la calcula el servidor en
   * cada consulta, así no puede quedar desactualizada al pasar la fecha de fin.
   */
  vigente: boolean;
  colecciones: number;
  colecciones_activas: number;
}

/**
 * Alta de temporada.
 *
 * `confirmar_solapamiento` implementa la excepción E2: el primer envío se
 * rechaza con 409 si el rango se cruza con otra temporada abierta, y el
 * segundo —con este campo en true— la guarda igual.
 */
export interface TemporadaCrear {
  nombre: string;
  descripcion?: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  activa?: boolean;
  confirmar_solapamiento?: boolean;
}

/** Edición (flujo alternativo 3a). Solo viaja lo que cambió. */
export interface TemporadaEditar {
  nombre?: string;
  descripcion?: string | null;
  fecha_inicio?: string;
  fecha_fin?: string;
  confirmar_solapamiento?: boolean;
}

/** Fila del listado de colecciones (flujo alternativo 1a). */
export interface Coleccion {
  id: number;
  temporada_id: number;
  temporada: string;
  nombre: string;
  descripcion: string | null;
  activa: boolean;
}

/** Alta de colección. */
export interface ColeccionCrear {
  temporada_id: number;
  nombre: string;
  descripcion?: string | null;
  activa?: boolean;
}

/** Edición de colección. */
export interface ColeccionEditar {
  temporada_id?: number;
  nombre?: string;
  descripcion?: string | null;
}

/** Filtros de los dos listados. */
export interface FiltrosTemporadas {
  busqueda?: string;
  activa?: boolean;
}

export interface FiltrosColecciones {
  busqueda?: string;
  temporada_id?: number;
  activa?: boolean;
}
