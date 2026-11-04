/**
 * 3ra presentación · CU-31 Gestionar ofertas y precios mayoristas y CU-32
 * Aplicar ofertas de fuera de temporada.
 * Espejo de `backend/app/modules/catalogo/ofertas_schemas.py`.
 *
 * El dinero y el porcentaje viajan como `string`, igual que en promociones.
 */

export interface Mayorista {
  id: number;
  producto_id: number;
  producto: string;
  precio_base: string;
  cantidad_minima: number;
  precio_unitario: string;
  activo: boolean;
}

export interface PaginaMayoristas {
  total: number;
  pagina: number;
  tamano: number;
  items: Mayorista[];
}

export interface CrearMayorista {
  producto_id: number;
  cantidad_minima: number;
  precio_unitario: string;
}

export interface EditarMayorista {
  cantidad_minima?: number;
  precio_unitario?: string;
}

export interface ReglaFueraDeTemporada {
  activa: boolean;
  dias_desde_fin: number;
  existencia_minima: number;
  porcentaje: string;
  /** Nunca se guardó: son los valores con que arranca la empresa. */
  por_omision?: boolean;
}

export type SituacionCandidata = 'NUEVA' | 'VIGENTE' | 'APAGADA' | 'CREADA';

export interface Candidata {
  producto_id: number;
  producto: string;
  temporada: string;
  fin_de_temporada: string;
  dias_desde_fin: number;
  disponible: number;
  situacion: SituacionCandidata;
  promocion_id: number | null;
}

export interface Aplicacion {
  hoy: string;
  regla_activa: boolean;
  creadas: number;
  cerradas: number;
  ya_vigentes: number;
  apagadas_por_admin: number;
  candidatas: Candidata[];
}
