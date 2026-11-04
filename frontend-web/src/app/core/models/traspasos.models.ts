/**
 * 3ra presentación · CU-33 a CU-35 — traspasos entre sucursales.
 * Espejo de `backend/app/modules/traspasos/schemas.py`.
 */

export type EstadoTraspaso = 'SOLICITADO' | 'APROBADO' | 'ENVIADO' | 'RECIBIDO' | 'RECHAZADO';
export type TipoTraspaso = 'PEDIDO' | 'ORDEN' | 'SUGERIDO';
export type AccionTraspaso = 'APROBAR' | 'RECHAZAR' | 'ENVIAR' | 'RECIBIR';
export type Bandeja = 'ENTRANTES' | 'SALIENTES';

export interface SucursalDelTraspaso {
  id: number;
  nombre: string;
}

export interface Traspaso {
  id: number;
  tipo: TipoTraspaso;
  estado: EstadoTraspaso;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  origen: SucursalDelTraspaso;
  destino: SucursalDelTraspaso;
  cantidad: number;
  cantidad_solicitada: number;
  motivo: string | null;
  motivo_rechazo: string | null;
  solicitado_por: string | null;
  creado_en: string;
  aprobado_por: string | null;
  aprobado_en: string | null;
  enviado_por: string | null;
  enviado_en: string | null;
  recibido_por: string | null;
  recibido_en: string | null;
  rechazado_por: string | null;
  rechazado_en: string | null;
  /** Lo que puede hacer quien consulta, ya resuelto por el servidor. */
  acciones: AccionTraspaso[];
}

export interface PaginaTraspasos {
  total: number;
  pagina: number;
  tamano: number;
  items: Traspaso[];
}

export interface FiltrosTraspasos {
  bandeja?: Bandeja | null;
  estado?: EstadoTraspaso | null;
  abiertos?: boolean;
  pagina?: number;
  tamano?: number;
}

export interface SolicitarTraspaso {
  variante_id: number;
  sucursal_origen_id: number;
  /** Solo el administrador; al encargado le vale la suya. */
  sucursal_destino_id?: number | null;
  cantidad: number;
  motivo?: string | null;
  desde_sugerencia?: boolean;
}

export interface PrendaPedible {
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  disponible: number;
}

export interface OrigenPosible {
  sucursal_id: number;
  sucursal: string;
  disponible: number;
}

export interface PuntaSugerida {
  sucursal_id: number;
  sucursal: string;
  disponible: number;
  vendidas: number;
  stock_minimo: number;
  en_traspaso: number;
}

export interface TraspasoSugerido {
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  origen: PuntaSugerida;
  destino: PuntaSugerida;
  cantidad_sugerida: number;
  razon: string;
}

export interface Sugerencias {
  dias: number;
  generado_en: string;
  items: TraspasoSugerido[];
}
