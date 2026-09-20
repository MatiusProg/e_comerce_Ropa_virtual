/**
 * CU-12 · Gestionar promociones — modelos del contrato.
 *
 * Espejo de `backend/app/modules/catalogo/promociones_schemas.py`.
 *
 * El dinero y el porcentaje viajan como `string`: el servidor los manda como
 * `Decimal` serializado y convertirlos a `number` acá reintroduciría el error
 * de coma flotante que el backend evitó a propósito.
 */

/** Sobre qué se define la promoción. Los tres alcances del RF35. */
export type Alcance = 'PRODUCTO' | 'CATEGORIA' | 'TEMPORADA';

/**
 * El descuento que se le está aplicando a una prenda, y por qué.
 *
 * Aparece en la vitrina, en la ficha, en el carrito y en el mostrador. Lleva el
 * NOMBRE de la promoción y no solo el porcentaje: quien ve «−20 %» sin saber de
 * qué se pregunta si es un error.
 */
export interface Descuento {
  promocion_id: number;
  nombre: string;
  porcentaje: string;
  /** Lo que se descuenta por unidad, en dinero y ya redondeado. */
  monto_unitario: string;
  /** `precio − monto_unitario`. Es lo que se cobra. */
  precio_final: string;
}

export interface Promocion {
  id: number;
  nombre: string;
  alcance: Alcance;
  objetivo_id: number;
  /** «Camisas», «Verano 2026». Resuelto en el servidor. */
  objetivo_nombre: string;
  porcentaje: string;
  desde: string;
  hasta: string | null;
  activa: boolean;
  /**
   * Si HOY está descontando.
   *
   * **No es lo mismo que `activa`**: una promoción activa que empieza el mes
   * que viene no está descontando nada, y sin distinguirlas el Administrador
   * cree que algo está roto.
   */
  vigente: boolean;
}

export interface PaginaPromociones {
  total: number;
  pagina: number;
  tamano: number;
  items: Promocion[];
}

export interface CrearPromocion {
  nombre: string;
  alcance: Alcance;
  objetivo_id: number;
  porcentaje: string;
  desde: string;
  hasta: string | null;
  activa: boolean;
}

export interface EditarPromocion {
  nombre?: string;
  porcentaje?: string;
  desde?: string;
  hasta?: string;
  /**
   * Para borrar la fecha de fin hay que pedirlo.
   *
   * En una edición parcial «no vino» y «vino en nulo» son lo mismo, así que
   * mandar `hasta: null` se lee como «no la toques».
   */
  quitar_hasta?: boolean;
}
