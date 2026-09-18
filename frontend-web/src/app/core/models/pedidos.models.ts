/**
 * CU-27 · Realizar pedido y pagar en línea — modelos del contrato.
 *
 * Espejo de `backend/app/modules/ventas/schemas.py`.
 *
 * El backend es de Mateo; esta mitad —la web— es de Karen. El acuerdo del
 * 17/09 repartió así este caso de uso: él el backend y el móvil, ella la web.
 *
 * EL FLUJO, EN CINCO PASOS
 * ------------------------
 *   1. `GET  /tienda/pedidos/opciones`  → qué puedo pedir y a dónde
 *   2. `POST /tienda/pedidos`           → se crea el pedido y devuelve `url_pago`
 *   3. el navegador se va a la pasarela
 *   4. el webhook firmado mueve el estado  (CU-28, de Mateo — no pasa por acá)
 *   5. `GET  /tienda/pedidos/{codigo}`  → qué dice la BASE del pedido
 *
 * El paso 5 es el que importa entender: **la pantalla de retorno no da el pago
 * por bueno**. Pregunta al backend y muestra lo que diga la venta. La URL por
 * la que el navegador volvió de la pasarela la puede escribir cualquiera a
 * mano; es la decisión D5 del análisis.
 */

import { LineaCarrito } from './carrito.models';

/** Cómo recibe el cliente lo que compró. Los valores son los de la base. */
export type ModalidadEntrega = 'RETIRO' | 'ENVIO';

/**
 * Los estados de una venta.
 *
 * `PENDIENTE_PAGO` la escribe CU-27; `PAGADA`, el webhook de CU-28;
 * `ENTREGADA`, CU-29; `CANCELADA`, el cliente o la barrida de vencidos.
 */
export type EstadoPedido = 'PENDIENTE_PAGO' | 'PAGADA' | 'ENTREGADA' | 'CANCELADA';

/** Una sucursal candidata para retirar, con si puede abastecer el pedido. */
export interface SucursalParaRetiro {
  id: number;
  nombre: string;
  direccion: string;
  ciudad: string;
  /** Si tiene stock de **todo** el carrito. Si es `false`, no se puede elegir. */
  abastece_todo: boolean;
  /** Qué le falta, para poder decirlo en vez de sólo deshabilitarla. */
  faltantes: string[];
}

export interface DireccionParaEnvio {
  id: number;
  alias: string;
  direccion: string;
  ciudad: string;
  referencia: string | null;
  predeterminada: boolean;
}

/**
 * Todo lo que la pantalla de confirmación necesita, en una sola petición.
 *
 * Viene junto a propósito: pedirlo en tres viajes dejaría la pantalla
 * pintándose por partes y abriría una ventana en la que el total podría
 * cambiar entre una consulta y la siguiente.
 */
export interface OpcionesDePedido {
  lineas: LineaCarrito[];
  total: string;
  unidades: number;

  /** Si es `false`, el botón de confirmar va deshabilitado y se dice por qué. */
  se_puede_pedir: boolean;
  motivo: string | null;

  sucursales: SucursalParaRetiro[];
  direcciones: DireccionParaEnvio[];

  /**
   * Si el proveedor de pago configurado mueve dinero de verdad.
   *
   * **Cuando es `false` la pantalla lo dice con todas las letras.** En la
   * demostración el pago es de mentira, y hacerlo pasar por real sería engañar
   * al tribunal.
   */
  pago_real: boolean;
  /** Cuántos minutos aguanta el pedido sin pagar antes de cancelarse solo. */
  minutos_para_pagar: number;
}

export interface CrearPedidoIn {
  modalidad_entrega: ModalidadEntrega;
  /** Obligatorio en RETIRO. En ENVIO la sucursal la elige el sistema. */
  sucursal_id?: number;
  /** Obligatorio en ENVIO. */
  direccion_id?: number;
  /**
   * El total que el cliente **vio** cuando pulsó confirmar.
   *
   * El carrito no congela precios —es una intención, no un contrato—, así que
   * entre que se miró el carrito y se confirmó, la tienda pudo cambiar un
   * precio. Sin este campo el sistema cobraría el precio nuevo callado y el
   * cliente se enteraría leyendo el comprobante. Con él, el servidor se planta
   * y devuelve 409 con el total nuevo.
   */
  total_esperado: string;
}

export interface LineaPedido {
  variante_id: number;
  sku: string;
  producto_nombre: string;
  talla_codigo: string | null;
  color_nombre: string | null;
  imagen_url: string | null;
  cantidad: number;
  precio_unitario: string;
  descuento_unitario: string;
  subtotal: string;
}

export interface Pedido {
  codigo: string;
  estado: EstadoPedido;
  canal: string;
  modalidad_entrega: ModalidadEntrega | null;

  sucursal_id: number;
  sucursal_nombre: string;
  /** Nula en un retiro. */
  direccion_envio: string | null;

  lineas: LineaPedido[];
  subtotal: string;
  descuento: string;
  total: string;

  creado_en: string;
  /** Hasta cuándo se puede pagar. Nula si el pedido ya dejó de esperar pago. */
  pagar_antes_de: string | null;
  /** Estado de la tabla `pago`. Nulo si todavía no se creó. */
  estado_pago: string | null;
}

export interface CrearPedidoRespuesta {
  pedido: Pedido;
  /** A dónde mandar el navegador. */
  url_pago: string;
  pago_real: boolean;
}

/**
 * El cuerpo del 409 cuando el total cambió entre mirar y confirmar.
 *
 * Trae el carrito al día para que la pantalla pueda mostrar **qué** cambió, no
 * sólo que cambió.
 */
export interface ConflictoDePrecio {
  detalle: string;
  total_esperado: string;
  total_actual: string;
  lineas: LineaCarrito[];
}
