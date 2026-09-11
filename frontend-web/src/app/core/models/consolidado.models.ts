/**
 * CU-14 · Consultar inventario consolidado — modelos del contrato.
 *
 * Espejo de `backend/app/modules/inventario/consolidado_schemas.py`.
 *
 * Archivo propio y no dentro de `inventario.models.ts`, que es de CU-13 y
 * CU-15: la forma es distinta —acá la fila es la **variante**, con su reparto
 * entre sucursales adentro; allá es el par (variante, sucursal)— y son de
 * personas distintas, así que ninguna rama comparte líneas con otra.
 */

/** Los estados que el enunciado pide distinguir. */
export type EstadoExistencia =
  | 'disponible'
  | 'reservada'
  | 'agotada'
  /**
   * Declarado en el contrato y **hoy nunca devuelto**: ningún caso de uso
   * anuncia mercadería en camino —CU-13 registra la que ya llegó—. Es el
   * agujero H1 del análisis de alcance; lo cerraría el CU-39 propuesto.
   */
  | 'proxima_a_ingresar';

export interface SaldoEnSucursal {
  sucursal_id: number;
  sucursal: string;
  cantidad_disponible: number;
  cantidad_reservada: number;
}

/** Una variante con su saldo sumado y su reparto entre sucursales. */
export interface ExistenciaConsolidada {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  total_disponible: number;
  total_reservado: number;
  /** Lo que hay físicamente en la red: disponible + reservado. */
  total_fisico: number;
  estado: EstadoExistencia;
  /** En cuántas sucursales hay algo. Es la lectura rápida del desbalance. */
  sucursales_con_saldo: number;
  sucursales: SaldoEnSucursal[];
}

export interface PaginaInventarioConsolidado {
  total: number;
  pagina: number;
  tamano: number;
  items: ExistenciaConsolidada[];
}

/** Los totales de la cabecera. Se calculan sobre todo lo filtrado, no sobre la página. */
export interface ResumenInventario {
  variantes: number;
  total_disponible: number;
  total_reservado: number;
  agotadas: number;
}

export interface InventarioConsolidado {
  listado: PaginaInventarioConsolidado;
  resumen: ResumenInventario;
}

export type OrdenConsolidado =
  | 'prenda'
  | 'disponible_asc'
  | 'disponible_desc'
  | 'sucursales';

export interface ConsultaConsolidado {
  busqueda?: string;
  sucursal_id?: number;
  producto_id?: number;
  estado?: EstadoExistencia;
  orden?: OrdenConsolidado;
  pagina?: number;
  tamano?: number;
}
