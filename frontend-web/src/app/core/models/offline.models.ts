import type { Descuento } from './promociones.models';

/**
 * CU-13 a CU-19 · Trabajar sin conexión — modelos del contrato.
 *
 * Espejo de `backend/app/modules/offline/schemas.py`. El dinero viaja como
 * `string`, igual que en el mostrador (`pos.models.ts`).
 */

export interface SucursalOffline {
  id: number;
  nombre: string;
  horario_apertura: string;
  horario_cierre: string;
}

export interface PrendaOffline {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  precio: string;
  descuento: Descuento | null;
  /** El saldo al descargar, menos lo que se vendió en este dispositivo. */
  disponible: number;
}

export interface ClienteOffline {
  id: number;
  nombre: string;
  documento: string | null;
}

/** CU-13: lo que el cajero se lleva al navegador para vender sin red. */
export interface PaqueteDeMostrador {
  generado_en: string;
  /** Pasada esta hora, se avisa que los datos pueden estar viejos (RF-13). */
  vigente_hasta: string;
  empresa_id: number;
  usuario_id: number;
  sucursal: SucursalOffline;
  turno_caja_id: number;
  caja_nombre: string;
  prendas: PrendaOffline[];
  clientes: ClienteOffline[];
}

export type MetodoOffline = 'EFECTIVO' | 'QR';

export interface LineaOffline {
  variante_id: number;
  cantidad: number;
  precio_unitario: string;
  descuento_unitario: string;
}

export interface PagoOffline {
  metodo: MetodoOffline;
  monto: string;
  referencia?: string | null;
}

/** Lo que viaja al servidor en CU-17. */
export interface OperacionOfflineIn {
  uuid: string;
  tipo: 'VENTA' | 'RESERVA';
  creada_en: string;
  lineas: LineaOffline[];
  pago?: PagoOffline | null;
  turno_caja_id?: number | null;
  sucursal_id?: number | null;
  cliente_id?: number | null;
  franja_inicio?: string | null;
  franja_fin?: string | null;
}

/**
 * Los estados de RF-20, del lado del dispositivo.
 *
 * `local` y `enviada` solo existen acá: al servidor la operación llega ya
 * enviada y sale decidida. `en_conflicto` es la que el servidor no pudo
 * decidir porque el pedido mismo falló (un 4xx que no es un rechazo): queda
 * en la cola, a la vista, y NO se borra (RNF06).
 */
export type EstadoLocal = 'local' | 'enviada' | 'confirmada' | 'rechazada' | 'en_conflicto';

/** Una operación guardada en IndexedDB, con lo que se sabe de ella. */
export interface OperacionGuardada {
  uuid: string;
  estado: EstadoLocal;
  operacion: OperacionOfflineIn;
  /** Para mostrar en la cola sin recalcular. */
  resumen: string;
  total: string;
  intentos: number;
  motivo: string | null;
  venta_codigo: string | null;
  requiere_devolucion: boolean;
  actualizada_en: string;
}

/** La respuesta del servidor por cada operación (CU-17). */
export interface ResultadoSincronizacion {
  uuid: string;
  tipo: string;
  estado: 'CONFIRMADA' | 'RECHAZADA';
  motivo: string | null;
  venta_codigo: string | null;
  reserva_id: number | null;
  requiere_devolucion: boolean;
  devuelta: boolean;
  repetida: boolean;
  recibida_en: string;
}

export interface LoteOut {
  resultados: ResultadoSincronizacion[];
  confirmadas: number;
  rechazadas: number;
}

/** CU-19: una operación ya sincronizada, vista por el encargado. */
export interface OperacionDeSucursal extends ResultadoSincronizacion {
  sucursal_id: number;
  usuario: string;
  creada_en_cliente: string;
  intentos: number;
  metodo_pago: string | null;
  monto_cobrado: string | null;
  referencia_pago: string | null;
  devuelto_en: string | null;
  metodo_devolucion: string | null;
  referencia_devolucion: string | null;
}

export interface DevolucionIn {
  metodo: MetodoOffline;
  referencia?: string | null;
  observacion?: string | null;
}
