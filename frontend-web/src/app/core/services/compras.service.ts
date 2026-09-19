import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { Pedido } from '../models/pedidos.models';

/** Una página del historial. Espejo de `PaginaCompras`. */
export interface PaginaCompras {
  total: number;
  pagina: number;
  tamano: number;
  items: Pedido[];
}

export type ErrorCompras =
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'sin-pagar'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-29 — el cliente HTTP del historial de compras.
 *
 * Reusa el modelo `Pedido` de CU-27: la ficha de una compra y la de un pedido
 * son la misma cosa. Declarar un modelo paralelo obligaría a mantener dos formas
 * sincronizadas, y el día que una gane un campo la otra lo perdería sin que nada
 * avise.
 */
@Injectable({ providedIn: 'root' })
export class ComprasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/tienda/compras`;

  listar(pagina = 1, tamano = 10): Observable<PaginaCompras> {
    return this.http
      .get<PaginaCompras>(this.base, { params: { pagina, tamano } })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * El comprobante en PDF.
   *
   * Se pide como `blob` y no como JSON: el cuerpo son bytes, y dejar que
   * Angular intente interpretarlos como texto los corrompe.
   *
   * **No se usa un `<a href>` directo** aunque sería más simple: el endpoint
   * exige el token, y un enlace del navegador no pasa por el interceptor que lo
   * adjunta. Se descarga con `HttpClient` y se guarda desde memoria.
   */
  comprobante(codigo: string): Observable<Blob> {
    return this.http
      .get(`${this.base}/${encodeURIComponent(codigo)}/comprobante`, {
        responseType: 'blob',
      })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorCompras {
    const detalle: unknown = error.error?.detail;
    const texto = typeof detalle === 'string' ? detalle : '';

    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: texto || 'Las compras son del Cliente.' };
    }
    if (error.status === 404) {
      return { tipo: 'no-existe', mensaje: 'No encontramos esa compra.' };
    }
    if (error.status === 409) {
      return {
        tipo: 'sin-pagar',
        mensaje: texto || 'Esa compra todavía no se pagó, así que no tiene comprobante.',
      };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: texto || 'No se pudo consultar sus compras.' };
  }
}
