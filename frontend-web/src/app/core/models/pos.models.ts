import type { Descuento } from './promociones.models';

/**
 * CU-31 · Registrar venta presencial — modelos del contrato.
 *
 * Espejo de `backend/app/modules/pos/schemas.py`.
 *
 * El dinero viaja como `string`, nunca como `number`: el servidor lo manda como
 * `Decimal` serializado y convertirlo a `number` acá reintroduciría el error de
 * coma flotante que el backend evitó a propósito. Se formatea para mostrar y se
 * devuelve tal cual vino.
 */

/** Una prenda que se puede vender ahora mismo en esta sucursal. */
export interface PrendaEnMostrador {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  /** El precio vigente, SIN descuento. Se congela recién al vender. */
  precio: string;
  /**
   * La promoción vigente, o nada (CU-12).
   *
   * **Tiene que llegar hasta acá.** La pantalla arma su total con estos
   * precios y lo manda como `total_esperado`; sin el descuento su total sería
   * mayor que el del servidor y CU-31 rechazaría con 409 *toda* venta de una
   * prenda en promoción.
   */
  descuento: Descuento | null;
  disponible: number;
}

export interface PaginaDePrendas {
  total: number;
  pagina: number;
  tamano: number;
  items: PrendaEnMostrador[];
}

/** Una prenda que el cliente se llevó de su reserva, con su precio de hoy. */
export interface LineaDeReserva {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  /** Precio de lista. El descuento va aparte, como en la búsqueda. */
  precio: string;
  descuento: Descuento | null;
  /** Ya con el descuento aplicado. */
  subtotal: string;
}

/**
 * Una reserva ya atendida cuyo cobro todavía no se registró.
 *
 * Solo trae las líneas con resultado `LLEVA`: lo que el cliente devolvió a la
 * percha no se cobra.
 */
export interface ReservaPorCobrar {
  reserva_id: number;
  cliente: string;
  atendida_en: string;
  lineas: LineaDeReserva[];
  total: string;
}

export type MetodoDePago = 'EFECTIVO' | 'TARJETA' | 'QR';

export interface LineaVenta {
  variante_id: number;
  cantidad: number;
}

export interface VentaPresencial {
  metodo_pago: MetodoDePago;
  /** Camino A: el cajero buscó las prendas. Excluyente con `reserva_id`. */
  lineas?: LineaVenta[];
  /** Camino B: se cobra una reserva ya atendida. */
  reserva_id?: number;
  /** Lo que la pantalla mostró. Si el precio cambió, el servidor avisa. */
  total_esperado?: string;
  /** Con cuánto paga el cliente. Solo sirve para el vuelto; no se guarda. */
  monto_recibido?: string;
}

export interface LineaVendida {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: string;
  subtotal: string;
}

/** El ticket. Es lo que la pantalla muestra después de cobrar. */
export interface Ticket {
  codigo: string;
  estado: string;
  metodo_pago: string;
  sucursal_nombre: string;
  caja_nombre: string;
  /** Nulo en una venta anónima, que es el caso corriente del mostrador. */
  cliente: string | null;
  reserva_id: number | null;
  lineas: LineaVendida[];
  subtotal: string;
  descuento: string;
  total: string;
  monto_recibido: string | null;
  vuelto: string | null;
  comprobante_numero: string;
  creado_en: string;
}

/**
 * Una línea del ticket mientras se arma, antes de cobrar.
 *
 * Vive solo en la pantalla: el servidor no sabe nada de esto hasta que se
 * confirma. Lleva la prenda entera y no solo su identificador porque la tabla
 * tiene que poder dibujarse sin volver a buscar nada.
 */
export interface LineaEnCurso {
  prenda: PrendaEnMostrador;
  cantidad: number;
}
