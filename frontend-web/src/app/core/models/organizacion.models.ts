/**
 * P2 · Organización — modelos del contrato.
 *
 * Por ahora solo lo que CU-03 necesita para asignar sucursal. El resto llega
 * con CU-05, CU-06 y CU-07.
 */

/** Sucursal reducida a lo que hace falta para elegirla en un selector. */
export interface SucursalBreve {
  id: number;
  nombre: string;
  ciudad: string;
}
