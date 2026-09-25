/**
 * CU-36 · Consultar tablero de indicadores — modelos del contrato.
 *
 * Espejo de `backend/app/modules/reportes/tablero_schemas.py`.
 *
 * El bloque `ventas` viaja **siempre**, con `disponible: false` mientras no
 * exista la migración `0006_ciclo3_ventas`. Está declarado acá desde el primer
 * día por la misma razón que en el backend: cuando aterrice, la pantalla no
 * cambia. Ver la cabecera del archivo de esquemas.
 */

/** Cuántas reservas hay en cada estado dentro del período. */
export interface ReservasPorEstado {
  pendientes: number;
  preparadas: number;
  atendidas: number;
  canceladas: number;
  expiradas: number;
  /** La suma de los cinco. */
  total: number;
  /**
   * Las que siguen vivas: pendientes + preparadas. **No es `pendientes`**: una
   * reserva preparada también está esperando a que el cliente llegue.
   */
  abiertas: number;
}

/**
 * Qué pasa con las reservas que ya se cerraron.
 *
 * Las tasas son `number | null`, y el nulo importa: «todavía no se cerró
 * ninguna» y «se cerraron diez y ninguna se atendió» son cosas opuestas.
 * Pintar 0 % en la primera deja el tablero en rojo el día que se estrena.
 */
export interface Conversion {
  cerradas: number;
  atendidas: number;
  /** `atendidas / cerradas`, de 0 a 100. Mide si la gente aparece. */
  tasa_atencion: number | null;
  lineas_probadas: number;
  lineas_llevadas: number;
  /** `llevadas / probadas`. Mide si la prenda convence una vez puesta. */
  tasa_prueba: number | null;
}

/** Una prenda dentro de un ranking, con sus dos lecturas. */
export interface PrendaRankeada {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  unidades: number;
  /**
   * En cuántas reservas distintas apareció. Veinte unidades en una reserva no
   * es lo mismo que veinte en veinte, y el ranking por unidades no deja verlo.
   */
  reservas: number;
}

/**
 * El estado del stock **ahora mismo**. No depende del período.
 *
 * Un saldo es una foto del instante, no un acumulado. La pantalla lo rotula
 * como «ahora» y no como parte del rango de fechas.
 */
export interface SaludInventario {
  total_disponible: number;
  total_reservado: number;
  /** Filas (variante, sucursal) en punto de reposición. La regla es de CU-16. */
  en_alerta: number;
  variantes_sin_stock: number;
}

export interface AlertaStock {
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  sucursal_id: number;
  sucursal: string;
  cantidad_disponible: number;
  stock_minimo: number;
}

/**
 * Los cuatro indicadores que dependen de la tabla de ventas.
 *
 * `disponible` es lo único que la pantalla mira para decidir si dibuja las
 * tarjetas o el aviso.
 */
export interface IndicadoresVentas {
  disponible: boolean;
  /**
   * El dinero viaja como **cadena**, no como número.
   *
   * Es la misma regla que el resto del proyecto: con `number` el JSON pasa por
   * el `float` de JavaScript y 150.55 deja de ser 150.55. El pipe de moneda
   * acepta la cadena tal cual, así que la pantalla no cambia.
   */
  monto_hoy: string | null;
  monto_periodo: string | null;
  cantidad_periodo: number | null;
  ticket_promedio: string | null;

  /**
   * Neto de devoluciones (CU-32).
   *
   * `monto_periodo` sigue siendo lo VENDIDO en bruto y no cambió de
   * significado: una devolución no corrige la venta. Lo que faltaba era poder
   * restarle lo que volvió a la percha, que hasta el 24/09/2026 no figuraba en
   * ningún lado —el tablero informaba como vendido algo que estaba de vuelta—.
   *
   * Hacen falta los tres y no sólo el neto: «vendimos 10.000 y devolvieron
   * 200» y «vendimos 10.000 y devolvieron 4.000» dan el mismo neto y no son la
   * misma situación.
   */
  devuelto_hoy: string | null;
  devuelto_periodo: string | null;
  neto_periodo: string | null;
  neto_hoy: string | null;
  mas_vendidas: PrendaRankeada[];
  /** Por qué no hay datos, en una frase. Nulo cuando `disponible` es true. */
  motivo: string | null;
}

/** El período que efectivamente se consultó, ya resuelto por el servicio. */
export interface PeriodoTablero {
  desde: string;
  hasta: string;
  sucursal_id: number | null;
  sucursal: string | null;
}

export interface Tablero {
  periodo: PeriodoTablero;
  /** Cuándo se calculó, para que la pantalla diga desde cuándo no se refresca. */
  calculado_en: string;
  reservas: ReservasPorEstado;
  conversion: Conversion;
  mas_reservadas: PrendaRankeada[];
  inventario: SaludInventario;
  alertas: AlertaStock[];
  ventas: IndicadoresVentas;
}

/** Lo que la pantalla puede acotar. Los tres son opcionales. */
export interface ConsultaTablero {
  desde?: string;
  hasta?: string;
  sucursal_id?: number;
}
