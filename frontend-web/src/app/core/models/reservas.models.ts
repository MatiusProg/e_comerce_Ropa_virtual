/**
 * CU-22 a CU-25 · Reservas — modelos del contrato.
 *
 * Espejo de `backend/app/modules/reservas/schemas.py`.
 *
 * Archivo propio, por el mismo motivo que los de inventario y productos: así
 * ninguna rama comparte líneas con otra durante el ciclo (§5 del acuerdo).
 */

/** Los cinco estados del ciclo de vida. Ver el diagrama en `models.py`. */
export type EstadoReserva =
  | 'PENDIENTE'
  | 'PREPARADA'
  | 'ATENDIDA'
  | 'CANCELADA'
  | 'EXPIRADA';

/** Los dos estados en los que la reserva sigue reteniendo stock y probador. */
export const ESTADOS_VIVOS: EstadoReserva[] = ['PENDIENTE', 'PREPARADA'];

export type ResultadoPrueba = 'LLEVA' | 'NO_LLEVA';

// --- CU-22 · Crear reserva ------------------------------------------------

export interface LineaReserva {
  variante_id: number;
  cantidad: number;
}

export interface ReservaCrear {
  sucursal_id: number;
  /**
   * **Con desfase horario, y conservando la hora de pared.**
   *
   * El servidor compara esta hora contra el horario de atención de la sucursal,
   * que es un `TIME` sin zona —«abre a las nueve» en esa tienda—. Mandarla
   * convertida a UTC con `toISOString()` haría que una reserva de las 15:00
   * llegara como 19:00 y una tienda que cierra a las 18:00 la rechazara.
   * Ver `conDesfase()` en el formulario.
   */
  franja_inicio: string;
  franja_fin: string;
  lineas: LineaReserva[];
}

export interface LineaReservaDetalle {
  id: number;
  variante_id: number;
  sku: string;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  /** Lo escribe CU-24 al atender. Nulo mientras la reserva sigue viva. */
  resultado_prueba: ResultadoPrueba | null;
}

export interface Reserva {
  id: number;
  cliente_id: number;
  sucursal_id: number;
  sucursal: string;
  ciudad: string;
  franja_inicio: string;
  franja_fin: string;
  estado: EstadoReserva;
  /** Nota de **cierre**: la escribe CU-23 al cancelar o CU-24 al atender. */
  observacion: string | null;
  creado_en: string;
  unidades: number;
  lineas: LineaReservaDetalle[];
}

/** Fila del listado. La misma para el Cliente y para el Encargado. */
export interface ReservaResumen {
  id: number;
  sucursal_id: number;
  sucursal: string;
  ciudad: string;
  franja_inicio: string;
  franja_fin: string;
  estado: EstadoReserva;
  prendas: number;
  unidades: number;
  /** Solo lo usa el panel del Encargado (CU-24): a quién está atendiendo. */
  cliente: string | null;
}

export interface PaginaReservas {
  total: number;
  pagina: number;
  tamano: number;
  items: ReservaResumen[];
}

export interface FiltrosReservas {
  estado?: EstadoReserva;
  /** true: solo PENDIENTE o PREPARADA; false: las cerradas. */
  vivas?: boolean;
  pagina?: number;
  tamano?: number;
}

// --- CU-23 · Cancelar -----------------------------------------------------

export interface CancelarReserva {
  /** Opcional: cancelar no es un trámite. */
  motivo?: string | null;
}

// --- CU-24 · Atender ------------------------------------------------------

export interface ResultadoLinea {
  detalle_id: number;
  resultado: ResultadoPrueba;
}

export interface AtenderReserva {
  /** Tienen que venir **todas** las líneas: cerrar a medias dejaría stock
   *  apartado en una reserva ya cerrada, y no lo libera nadie. */
  resultados: ResultadoLinea[];
  observacion?: string | null;
}

// --- CU-25 · Expiración ---------------------------------------------------

/** Lo que hizo una corrida de la tarea. Ver por qué informa en la ficha. */
export interface Expiracion {
  encontradas: number;
  expiradas: number;
  unidades_liberadas: number;
  reservas: number[];
  /** Hasta qué instante se consideró vencida una reserva. */
  corte: string;
}
