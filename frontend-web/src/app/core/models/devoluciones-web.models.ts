/**
 * CU-24 y CU-25 · Devoluciones por la web — modelos del contrato.
 *
 * Espejo de `backend/app/modules/devoluciones_web/schemas.py`. El dinero viaja
 * como `string`.
 */

export interface PedidoDeSucursal {
  codigo: string;
  estado: 'PAGADA' | 'ENTREGADA';
  modalidad_entrega: string | null;
  cliente: string | null;
  total: string;
  unidades: number;
  creado_en: string;
  entregado_en: string | null;
}

export interface OpcionDeCambio {
  variante_id: number;
  sku: string;
  talla: string;
  color: string;
  precio: string;
  disponible: number;
}

export interface LineaDevolvibleWeb {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  vendidas: number;
  comprometidas: number;
  devolvibles: number;
  precio_pagado: string;
  opciones_de_cambio: OpcionDeCambio[];
}

export interface PedidoDevolvible {
  codigo: string;
  sucursal: string;
  entregado_en: string;
  ventana_horas: number;
  vence_en: string;
  dentro_de_plazo: boolean;
  lineas: LineaDevolvibleWeb[];
}

export type TipoSolicitud = 'DEVOLUCION' | 'CAMBIO';
export type EstadoSolicitud = 'PENDIENTE' | 'APROBADA' | 'RECHAZADA' | 'COMPLETADA';

export interface SolicitudIn {
  venta_codigo: string;
  tipo: TipoSolicitud;
  motivo: string;
  lineas: { variante_id: number; cantidad: number; variante_nueva_id?: number | null }[];
}

export interface LineaSolicitud {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_pagado: string;
  variante_nueva_id: number | null;
  talla_nueva: string | null;
  color_nueva: string | null;
  precio_nuevo: string | null;
}

export interface Solicitud {
  id: number;
  venta_codigo: string;
  sucursal: string;
  cliente: string;
  tipo: TipoSolicitud;
  estado: EstadoSolicitud;
  motivo: string;
  respuesta: string | null;
  creado_en: string;
  atendida_en: string | null;
  lineas: LineaSolicitud[];
  valor_devuelto: string;
  valor_nuevo: string | null;
  diferencia: string | null;
  /** CU-25: la nota que la cerró, su estado y el reembolso. */
  devolucion_id: number | null;
  numero_nota: string | null;
  nota_estado: 'ABIERTA' | 'CERRADA' | null;
  conforme: boolean | null;
  reembolso_monto: string | null;
  reembolso_referencia: string | null;
}

export const ROTULO_SOLICITUD: Record<EstadoSolicitud, string> = {
  PENDIENTE: 'Esperando a la tienda',
  APROBADA: 'Aprobada',
  RECHAZADA: 'Rechazada',
  COMPLETADA: 'Completada',
};
