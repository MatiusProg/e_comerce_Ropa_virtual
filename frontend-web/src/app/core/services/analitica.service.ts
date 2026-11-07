import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import type { ClienteSegmento, ResumenAnalitica } from '../models/analitica.models';

export type ErrorAnalitica =
  | { tipo: 'plan'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** CU-29 y CU-30 — el cliente HTTP de la analítica con ML. */
@Injectable({ providedIn: 'root' })
export class AnaliticaService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/analitica`;

  resumen(): Observable<ResumenAnalitica> {
    return this.http
      .get<ResumenAnalitica>(`${this.base}/resumen`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** CU-29. Entrena los dos modelos y devuelve el dashboard nuevo. */
  entrenar(semilla?: number): Observable<ResumenAnalitica> {
    return this.http
      .post<ResumenAnalitica>(`${this.base}/entrenamientos`, semilla == null ? {} : { semilla })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  clientes(): Observable<ClienteSegmento[]> {
    return this.http
      .get<ClienteSegmento[]>(`${this.base}/clientes`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  reporte(formato: 'pdf' | 'xlsx'): Observable<Blob> {
    return this.http
      .get(`${this.base}/reporte.${formato}`, { responseType: 'blob' })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorAnalitica {
    const cuerpo = error.error;
    const detalle = typeof cuerpo?.detail === 'string' ? cuerpo.detail : '';
    if (error.status === 403 && cuerpo?.codigo === 'plan_limit') {
      return {
        tipo: 'plan',
        mensaje: detalle || 'Su plan no incluye la analítica con ML.',
      };
    }
    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: 'La analítica es del Administrador.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: detalle || 'No se pudo completar la operación.' };
  }
}
