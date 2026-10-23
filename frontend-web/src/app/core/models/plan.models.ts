/**
 * 2do parcial · CU-05 Verificar límites y funciones del plan — el rechazo.
 *
 * Espejo de `RechazoDelPlan.cuerpo()` en
 * `backend/app/modules/plataforma/verificador.py`. Llega con status 403.
 *
 * `detail` sigue siendo un mensaje listo para mostrar, así que los servicios
 * que ya muestran el `detail` de un error no necesitan cambiar. `codigo` es
 * para la pantalla que quiera ofrecer ver los planes (3a del CU-05).
 */
import type { HttpErrorResponse } from '@angular/common/http';

export type CodigoDelPlan = 'plan_limit' | 'sin_suscripcion';

export interface RechazoDelPlan {
  detail: string;
  codigo: CodigoDelPlan;
  /** Solo en el 4a: el máximo del plan y lo que ya se usó. */
  limite?: number;
  uso?: number;
}

/** Si el error es un rechazo del plan, lo devuelve; si no, `null`. */
export function rechazoDelPlan(error: HttpErrorResponse): RechazoDelPlan | null {
  const cuerpo = error.error as Partial<RechazoDelPlan> | null;
  if (error.status !== 403 || !cuerpo) return null;
  return cuerpo.codigo === 'plan_limit' || cuerpo.codigo === 'sin_suscripcion'
    ? (cuerpo as RechazoDelPlan)
    : null;
}
