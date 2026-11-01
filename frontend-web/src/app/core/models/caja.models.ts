/**
 * CU-30 · Abrir y cerrar caja — modelos del contrato.
 *
 * Espejo de `backend/app/modules/caja/schemas.py`.
 *
 * El backend es de Mateo; esta mitad —la web— es de Karen, con el mismo reparto
 * que CU-27.
 */

/** Una caja de la sucursal, con si alguien más la tiene abierta. */
export interface Caja {
  id: number;
  nombre: string;
  /**
   * Si otra persona la tiene abierta.
   *
   * **Se informa en vez de esconder la caja**: el cajero necesita saber que
   * existe y está ocupada, no que desapareció.
   */
  ocupada: boolean;
}

/** Una línea del arqueo: cuánto entró por cada método de cobro. */
export interface LineaDeArqueo {
  metodo: string;
  ventas: number;
  total: string;
}

export interface Turno {
  id: number;
  caja_id: number;
  caja_nombre: string;
  sucursal_nombre: string;
  abierto_en: string;
  cerrado_en: string | null;

  monto_apertura: string;

  /** Lo que entró al cajón en efectivo durante el turno. */
  efectivo_cobrado: string;
  /**
   * Lo que salió del cajón por devoluciones (CU-32).
   *
   * Solo cuenta las de ventas cobradas en efectivo: lo devuelto de un cobro
   * con tarjeta nunca entró al cajón y no puede salir de él.
   */
  devoluciones: string;
  /**
   * CU-20: efectivo de ventas sin conexión que el servidor RECHAZÓ. No hay
   * venta, pero el billete está en el cajón hasta que el encargado se lo
   * devuelve al cliente.
   */
  por_devolver: string;
  por_devolver_cantidad: number;
  /** CU-20: ventas sin conexión ya confirmadas. Ya están en `efectivo_cobrado`. */
  ventas_offline: number;
  ventas_offline_total: string;
  /** `apertura + efectivo − devoluciones + cambios + por devolver`. */
  monto_esperado: string;

  /** Lo que la persona contó. Nulo mientras el turno sigue abierto. */
  monto_cierre: string | null;
  /** `contado − esperado`. Positivo es que sobra. Nulo hasta cerrar. */
  diferencia: string | null;

  por_metodo: LineaDeArqueo[];
}

export interface AbrirTurno {
  caja_id: number;
  monto_apertura: string;
}

export interface CerrarTurno {
  monto_cierre: string;
}
