import type { HttpErrorResponse } from '@angular/common/http';

/**
 * 2do parcial · CU-13 · ¿La petición no llegó al servidor?
 *
 * SIN RED NO SIEMPRE ES `status 0`
 * --------------------------------
 * Sin service worker, una petición que no llega falla con `status 0`. CON el
 * service worker de la PWA, el worker la intercepta —también las de la API,
 * aunque sea de otro origen— y, si la red falla, responde él mismo un
 * **504 Gateway Timeout**. Mirar solo el 0 hacía que, sin red, restaurar la
 * sesión leyera ese 504 como «token inválido» y la borrara: el cajero quedaba
 * en el login justo cuando no podía iniciar sesión. Se descubrió probando la
 * PWA con el backend apagado.
 */
export function sinRespuesta(error: HttpErrorResponse): boolean {
  return error.status === 0 || error.status === 504;
}
