import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  PaginaDePrendas,
  ReservaPorCobrar,
  Ticket,
  VentaPresencial,
} from '../models/pos.models';

/**
 * Los errores del mostrador, traducidos a algo que se pueda decidir.
 *
 * Cada variante existe porque la pantalla **hace algo distinto** con ella, no
 * por catalogar códigos HTTP: `sin-turno` manda a abrir caja, `precio-cambio`
 * refresca el ticket, `sin-stock` marca la línea. Un único `mensaje` obligaría
 * a leer el texto para decidir, que es exactamente lo que no hay que hacer.
 */
export type ErrorPos =
  | { tipo: 'sin-turno'; mensaje: string }
  | { tipo: 'precio-cambio'; mensaje: string }
  | { tipo: 'sin-stock'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'rechazado'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class PosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/pos`;

  prendas(busqueda: string, pagina = 1, tamano = 20): Observable<PaginaDePrendas> {
    let params = new HttpParams().set('pagina', pagina).set('tamano', tamano);
    const limpia = busqueda.trim();
    if (limpia) params = params.set('busqueda', limpia);
    return this.http
      .get<PaginaDePrendas>(`${this.base}/prendas`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  reservasPorCobrar(): Observable<ReservaPorCobrar[]> {
    return this.http
      .get<ReservaPorCobrar[]>(`${this.base}/reservas`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cobrar(datos: VentaPresencial): Observable<Ticket> {
    return this.http
      .post<Ticket>(`${this.base}/ventas`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * La URL del comprobante, para abrirlo en otra pestaña.
   *
   * No se descarga con `HttpClient`: el PDF necesita el token en la cabecera y
   * un `window.open` directo iría sin él. Quien la use tiene que pedirlo como
   * blob y abrirlo; por eso existe `comprobante()` acá abajo.
   */
  comprobante(codigo: string): Observable<Blob> {
    return this.http
      .get(`${this.base}/ventas/${codigo}/comprobante`, { responseType: 'blob' })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorPos {
    const detalle: unknown = error.error?.detail;
    const texto = typeof detalle === 'string' ? detalle : '';

    if (error.status === 409) {
      // El servidor manda tres cosas distintas con 409. Se separan por lo que
      // la pantalla tiene que hacer, no por el código.
      if (texto.toLowerCase().includes('turno')) {
        return { tipo: 'sin-turno', mensaje: texto };
      }
      if (texto.toLowerCase().includes('total cambió')) {
        return { tipo: 'precio-cambio', mensaje: texto };
      }
      return { tipo: 'sin-stock', mensaje: texto || 'No alcanza el stock.' };
    }
    if (error.status === 404) {
      return { tipo: 'no-existe', mensaje: texto || 'Eso no existe en su sucursal.' };
    }
    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: texto || 'El mostrador es del Cajero.' };
    }
    if (error.status === 422) {
      return { tipo: 'rechazado', mensaje: texto || 'Revise los datos del cobro.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: texto || 'No se pudo registrar la venta.' };
  }
}
