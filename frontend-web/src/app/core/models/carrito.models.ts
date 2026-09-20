import type { Descuento } from './promociones.models';

/**
 * P7 · Ventas — CU-26 Gestionar carrito de compras.
 *
 * Espejo exacto de `backend/app/modules/ventas/carrito_schemas.py`. Si cambia
 * uno, cambia el otro: son las dos caras del mismo contrato (RNF07).
 */

/** Una prenda del carrito, con todo lo que hace falta para pintarla. */
export interface LineaCarrito {
  variante_id: number;
  producto_id: number;
  sku: string;
  producto_nombre: string;
  talla_codigo: string | null;
  color_nombre: string | null;
  color_hexadecimal: string | null;
  imagen_url: string | null;

  cantidad: number;
  /**
   * Precio **vigente** de la variante, no el que tenía al agregarla. El
   * carrito no guarda precios: es una intención, no un contrato, y el precio se
   * fija al generar el pedido (CU-27).
   */
  precio_unitario: string;
  /** La promoción vigente que ganó para esta prenda, o nada (CU-12). */
  descuento: Descuento | null;
  /** Ya con el descuento aplicado. */
  subtotal: string;

  /**
   * `false` si la prenda dejó de ofrecerse después de agregarla. La línea NO
   * se borra sola —el cliente tiene que ver que estaba ahí— y no suma al total.
   */
  disponible: boolean;
  /**
   * Unidades en toda la red. Es un aviso, no una reserva: el carrito no
   * inmoviliza inventario —eso es CU-22— y la validación de verdad es de CU-27.
   */
  stock_total: number;
}

/**
 * El carrito completo.
 *
 * Un carrito vacío **no es un 404**: es un carrito con cero líneas, que es el
 * estado normal de quien todavía no agregó nada.
 */
export interface Carrito {
  lineas: LineaCarrito[];
  /** Prendas distintas. Es lo que va en la burbuja del ícono. */
  items: number;
  /** Unidades en total, sumando cantidades. Cuenta también las no disponibles. */
  unidades: number;
  /** Suma de los subtotales de las líneas disponibles. */
  total: string;
  /** Cuántas líneas dejaron de ofrecerse. Si es > 0 la pantalla lo dice arriba. */
  no_disponibles: number;
}

/** Cuerpo de POST /tienda/carrito/items. **Suma** a lo que ya hubiera. */
export interface AgregarAlCarrito {
  variante_id: number;
  cantidad: number;
}

/**
 * Tope de unidades por línea. Replica `CANTIDAD_MAXIMA` del backend.
 *
 * No sale de una regla de negocio escrita: existe para que un dedo apoyado en
 * el botón de sumar no deje un carrito con miles de unidades.
 */
export const CANTIDAD_MAXIMA = 20;

/** Un carrito vacío, para pintar la pantalla antes de la primera respuesta. */
export const CARRITO_VACIO: Carrito = {
  lineas: [],
  items: 0,
  unidades: 0,
  total: '0.00',
  no_disponibles: 0,
};
