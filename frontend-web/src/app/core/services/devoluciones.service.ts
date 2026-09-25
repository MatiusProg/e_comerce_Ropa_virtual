import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Cambio,
  ComprobanteCambio,
  ComprobanteDevolucion,
  Devolucion,
  VentaDevolvible,
} from '../models/devoluciones.models';

export type ErrorDevolucion =
  | { tipo: 'sin-turno'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'se-pasa'; mensaje: string }
  /** La venta es más vieja que el plazo que la tienda da para volver. */
  | { tipo: 'fuera-de-plazo'; mensaje: string }
  /** La diferencia que calculó la pantalla ya no es la del servidor. */
  | { tipo: 'diferencia-movida'; mensaje: string }
  | { tipo: 'rechazado'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class DevolucionesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/pos/devoluciones`;

  /** La venta y lo que todavía queda por devolver de ella. */
  buscarVenta(codigo: string): Observable<VentaDevolvible> {
    return this.http
      .get<VentaDevolvible>(`${this.base}/ventas/${encodeURIComponent(codigo)}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  registrar(datos: Devolucion): Observable<ComprobanteDevolucion> {
    return this.http
      .post<ComprobanteDevolucion>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Cambia una prenda por otra: las dos puntas en una sola operación. */
  registrarCambio(datos: Cambio): Observable<ComprobanteCambio> {
    return this.http
      .post<ComprobanteCambio>(`${this.base}/cambios`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorDevolucion {
    const detalle: unknown = error.error?.detail;
    const texto = typeof detalle === 'string' ? detalle : '';

    if (error.status === 409) {
      // El servidor manda cuatro cosas con 409, y la pantalla hace algo
      // distinto con cada una: sin turno manda a abrir caja, fuera de plazo
      // apaga los botones, la diferencia movida obliga a recalcular, y «se
      // pasa» recarga la ficha porque alguien devolvió en el medio.
      const minusculas = texto.toLowerCase();
      if (minusculas.includes('turno')) {
        return { tipo: 'sin-turno', mensaje: texto };
      }
      if (minusculas.includes('plazo')) {
        return { tipo: 'fuera-de-plazo', mensaje: texto };
      }
      if (minusculas.includes('diferencia cambió')) {
        return { tipo: 'diferencia-movida', mensaje: texto };
      }
      return { tipo: 'se-pasa', mensaje: texto || 'Eso ya se devolvió.' };
    }
    if (error.status === 404) {
      return {
        tipo: 'no-existe',
        mensaje: texto || 'No hay ninguna venta con ese código en su sucursal.',
      };
    }
    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: texto || 'Las devoluciones son del Cajero.' };
    }
    if (error.status === 422) {
      return { tipo: 'rechazado', mensaje: texto || 'Revise los datos de la devolución.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: texto || 'No se pudo registrar la devolución.' };
  }
}
