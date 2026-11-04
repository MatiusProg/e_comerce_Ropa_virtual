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
  /** Nulo cuando lo que ganó es el precio mayorista (CU-31). */
  promocion_id: number | null;
  nombre: string;
  /**
   * 3ra presentación · CU-31. Uno solo, el que deja el precio más bajo
   * (RN-15): la promoción (manual o de fuera de temporada) o el mayorista.
   */
  tipo?: 'PROMOCION' | 'MAYORISTA';
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
  /** 3ra presentación · CU-32: la cargó el Administrador o la creó la regla. */
  origen?: 'MANUAL' | 'AUTOMATICA';
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
