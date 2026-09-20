import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  ComprobanteDevolucion,
  Devolucion,
  VentaDevolvible,
} from '../models/devoluciones.models';

export type ErrorDevolucion =
  | { tipo: 'sin-turno'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'se-pasa'; mensaje: string }
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

  private traducir(error: HttpErrorResponse): ErrorDevolucion {
    const detalle: unknown = error.error?.detail;
    const texto = typeof detalle === 'string' ? detalle : '';

    if (error.status === 409) {
      // El servidor manda dos cosas con 409: «no tiene turno» y «se pasa de lo
      // devolvible». Se separan por lo que la pantalla hace con cada una.
      if (texto.toLowerCase().includes('turno')) {
        return { tipo: 'sin-turno', mensaje: texto };
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
