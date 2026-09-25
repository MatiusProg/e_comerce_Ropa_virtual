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

  /** Los días que la tienda da para volver. Es política, no constante. */
  plazo_dias: number;
  /** El instante exacto en que se cierra. `creado_en + plazo_dias`. */
  vence_en: string;
  /**
   * Si hoy todavía se puede devolver o cambiar contra esta venta.
   *
   * Una venta vencida se encuentra igual, a propósito: el cajero necesita
   * poder abrirla para explicarle al cliente por qué no se puede y desde
   * cuándo. Lo que la pantalla hace con esto es apagar los botones, no
   * esconder la venta.
   */
  dentro_de_plazo: boolean;
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


/* =====================================================================
 * El segundo flujo: cambiar una prenda por otra
 * ===================================================================== */

export interface LineaLlevada {
  variante_id: number;
  cantidad: number;
}

export interface Cambio {
  venta_codigo: string;
  motivo: string;
  /** Lo que vuelve. */
  devueltas: LineaDevolucion[];
  /** Lo que se lleva. */
  llevadas: LineaLlevada[];
  /**
   * Cómo se salda la diferencia. Va **solo si hay diferencia**: mandarlo
   * cuando el cambio sale parejo lo rechaza el servidor, porque quedaría en la
   * base un método de pago contra plata que no se movió.
   */
  metodo_diferencia?: string;
  /**
   * Guarda contra un precio movido, igual que `total_esperado` en CU-31. Si la
   * pantalla calculó una diferencia y el servidor otra —una promoción que
   * empezó en el medio—, se rechaza en vez de cobrar callado algo que el
   * cliente no vio.
   */
  diferencia_esperada?: string;
}

export interface LineaComprobanteCambio {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: string;
  descuento_unitario: string;
  subtotal: string;
}

export interface ComprobanteCambio {
  id: number;
  /** La venta original, la que trajo la prenda devuelta. */
  venta_codigo: string;
  /** La venta NUEVA. La prenda que sale se vendió, y tiene su comprobante. */
  venta_nueva_codigo: string;
  comprobante_numero: string;
  caja_nombre: string;
  motivo: string;
  creado_en: string;

  devueltas: LineaDevuelta[];
  valor_devuelto: string;

  llevadas: LineaComprobanteCambio[];
  total_llevado: string;

  /** `total_llevado − valor_devuelto`, CON SIGNO. */
  diferencia: string;
  /**
   * CLIENTE, TIENDA o NADIE.
   *
   * Lo resuelve el servidor y no la pantalla a propósito: el signo de un
   * número es fácil de leer al revés cuando hay que decidir entre «cobrar» y
   * «entregar» con el cliente esperando.
   */
  a_favor_de: 'CLIENTE' | 'TIENDA' | 'NADIE';
  metodo_diferencia: string | null;
  /** Si esa diferencia movió billetes. Falso con tarjeta, QR y sin diferencia. */
  toca_el_cajon: boolean;
}

/** Una prenda que el cliente se lleva, mientras se arma el cambio. */
export interface PrendaQueSeLleva {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  /** Precio de lista. El descuento de CU-12 va aparte. */
  precio: string;
  descuento_unitario: string;
  cantidad: number;
  disponible: number;
}
