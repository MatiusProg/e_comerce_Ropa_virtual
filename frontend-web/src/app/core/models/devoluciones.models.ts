/**
 * CU-32 · Registrar devolución — modelos del contrato.
 *
 * Espejo de `backend/app/modules/pos/devolucion_schemas.py`.
 *
 * LOS DOS NÚMEROS QUE NO SON EL MISMO
 * ------------------------------------
 * `valor_devuelto` es lo que valen las prendas que volvieron. `monto` es lo que
 * **sale del cajón**, y es cero cuando la venta se cobró con tarjeta o QR: esa
 * plata nunca entró al cajón, así que tampoco puede salir de él —el arqueo de
 * CU-30 resta justamente `monto`—.
 *
 * La pantalla necesita los dos: «son Bs 250» y «no los saque del cajón» son dos
 * frases distintas y las dos hacen falta.
 */

/** Una prenda de la venta y cuántas unidades todavía se pueden devolver. */
export interface LineaDevolvible {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  vendidas: number;
  devueltas: number;
  /** `vendidas − devueltas`. El tope de lo que se puede devolver hoy. */
  devolvibles: number;
  /** El precio congelado de la venta, no el vigente. */
  precio_unitario: string;
}

export interface VentaDevolvible {
  codigo: string;
  estado: string;
  metodo_pago: string;
  creado_en: string;
  cliente: string | null;
  total: string;
  /** Si el reintegro sale del cajón. Falso con tarjeta y QR. */
  sale_del_cajon: boolean;
  lineas: LineaDevolvible[];
}

export interface LineaDevolucion {
  variante_id: number;
  cantidad: number;
}

export interface Devolucion {
  venta_codigo: string;
  motivo: string;
  lineas: LineaDevolucion[];
}

export interface LineaDevuelta {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: string;
  subtotal: string;
}

export interface ComprobanteDevolucion {
  id: number;
  venta_codigo: string;
  caja_nombre: string;
  motivo: string;
  creado_en: string;
  lineas: LineaDevuelta[];
  /** Lo que valen las prendas que volvieron. Siempre. */
  valor_devuelto: string;
  /** Lo que sale del cajón. Cero si se cobró con tarjeta o QR. */
  monto: string;
  sale_del_cajon: boolean;
}

/** Cuántas unidades de cada línea se están devolviendo, mientras se arma. */
export interface LineaEnDevolucion {
  linea: LineaDevolvible;
  cantidad: number;
}
