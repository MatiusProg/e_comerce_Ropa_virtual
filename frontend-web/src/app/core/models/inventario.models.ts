/**
 * CU-13, CU-15 y CU-16 · Inventario — modelos del contrato.
 *
 * Espejo de `backend/app/modules/inventario/schemas.py`.
 *
 * Archivo propio y no dentro de uno compartido, por el mismo motivo que los de
 * productos y temporadas: así ninguna rama comparte líneas con otra durante el
 * ciclo (§5 del acuerdo de organización).
 *
 * Las cantidades sí viajan como `number`, a diferencia de los precios de
 * CU-10: son unidades enteras, no importes, y no hay redondeo binario que
 * temer.
 */

/** Cómo se nombra una prenda en el depósito: por SKU, no por identificador. */
export interface VarianteResumen {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
}

/** Saldo de una variante en una sucursal. */
export interface Existencia extends VarianteResumen {
  existencia_id: number;
  sucursal_id: number;
  sucursal: string;
  cantidad_disponible: number;
  cantidad_reservada: number;
  /**
   * Lo que hay físicamente en el local: disponible + reservada. Es el número
   * contra el que se compara un conteo físico, y viaja calculado para que la
   * pantalla no tenga que deducir esa regla por su cuenta.
   */
  cantidad_fisica: number;

  /** Umbral de reposición que fijó el Encargado (CU-16). Cero = sin alerta. */
  stock_minimo: number;
  /**
   * Si esta prenda está en alerta. Viaja calculado por el mismo motivo que
   * `cantidad_fisica`: la regla —hay alerta cuando el umbral es mayor que cero
   * y el disponible no lo supera— es del negocio, no de la pantalla. Si cada
   * cliente la dedujera por su cuenta, la web y el móvil terminarían avisando
   * cosas distintas.
   */
  bajo_minimo: boolean;
}

// --- CU-16 · Disponibilidad de la sucursal -------------------------------

/**
 * El Encargado fija el punto de reposición de una prenda.
 *
 * Viaja solo el umbral: es el único campo de una existencia que una persona
 * edita a mano. Las dos cantidades no se tocan por esta puerta ni por ninguna
 * otra que no genere un movimiento.
 */
export interface StockMinimoCrear {
  stock_minimo: number;
}

// --- CU-13 · Ingreso de mercadería ---------------------------------------

export interface LineaIngreso {
  variante_id: number;
  cantidad: number;
}

export interface IngresoCrear {
  sucursal_id: number;
  proveedor_id: number;
  referencia: string | null;
  observacion: string | null;
  lineas: LineaIngreso[];
}

export interface LineaIngresoRegistrada extends VarianteResumen {
  cantidad: number;
  /** Cuánto quedó disponible después del ingreso. */
  disponible_resultante: number;
}

/** Comprobante del ingreso recién registrado. */
export interface IngresoRegistrado {
  registrado_en: string;
  sucursal_id: number;
  sucursal: string;
  proveedor_id: number;
  proveedor: string;
  referencia: string | null;
  usuario_id: number | null;
  usuario: string | null;
  unidades: number;
  lineas: LineaIngresoRegistrada[];
}

/**
 * Fila del historial de ingresos.
 *
 * No corresponde a una fila de ninguna tabla: el backend agrupa los
 * movimientos de tipo INGRESO por proveedor, sucursal, remito, usuario e
 * instante de transacción. Por eso el detalle se pide con esos mismos datos y
 * no con un identificador.
 */
export interface IngresoResumen {
  registrado_en: string;
  sucursal_id: number;
  sucursal: string;
  proveedor_id: number | null;
  proveedor: string | null;
  referencia: string | null;
  usuario_id: number | null;
  usuario: string | null;
  lineas: number;
  unidades: number;
}

export interface PaginaIngresos {
  total: number;
  pagina: number;
  tamano: number;
  items: IngresoResumen[];
}

export interface FiltrosIngresos {
  sucursal_id?: number;
  proveedor_id?: number;
  pagina?: number;
  tamano?: number;
}

// --- CU-15 · Movimientos --------------------------------------------------

/** Los tres tipos que una persona puede originar. El resto los genera el sistema. */
export type TipoManual = 'INGRESO' | 'TRANSFERENCIA' | 'AJUSTE';

export type TipoMovimiento =
  | TipoManual
  | 'RESERVA'
  | 'LIBERACION'
  | 'VENTA'
  | 'DEVOLUCION';

/** Fila del historial. `cantidad` conserva el signo: positiva entra, negativa sale. */
export interface Movimiento extends VarianteResumen {
  id: number;
  creado_en: string;
  tipo: TipoMovimiento;
  cantidad: number;
  motivo: string | null;
  referencia: string | null;
  existencia_id: number;
  sucursal_id: number;
  sucursal: string;
  proveedor_id: number | null;
  proveedor: string | null;
  usuario_id: number | null;
  usuario: string | null;
}

export interface PaginaMovimientos {
  total: number;
  pagina: number;
  tamano: number;
  items: Movimiento[];
}

export interface FiltrosMovimientos {
  sucursal_id?: number;
  variante_id?: number;
  tipo?: TipoMovimiento;
  desde?: string;
  hasta?: string;
  pagina?: number;
  tamano?: number;
}

/**
 * Ajuste por conteo físico.
 *
 * Se envía **lo contado**, no la diferencia: nadie cuenta «menos tres
 * camisas», cuenta «hay diecisiete». Y lo contado incluye lo reservado, porque
 * una prenda apartada sigue estando en la percha.
 */
export interface AjusteCrear {
  variante_id: number;
  sucursal_id: number;
  cantidad_contada: number;
  motivo: string;
}

export interface AjusteRegistrado {
  movimiento: Movimiento;
  existencia: Existencia;
  /** Diferencia con signo entre lo contado y lo que decía el sistema. */
  diferencia: number;
}

export interface TransferenciaCrear {
  variante_id: number;
  sucursal_origen_id: number;
  sucursal_destino_id: number;
  cantidad: number;
  motivo: string;
}

/** Las dos puntas de la transferencia, para que se pueda verificar de un vistazo. */
export interface TransferenciaRegistrada {
  salida: Movimiento;
  entrada: Movimiento;
  origen: Existencia;
  destino: Existencia;
}

export interface FiltrosExistencias {
  sucursal_id?: number;
  producto_id?: number;
  solo_con_saldo?: boolean;
}
