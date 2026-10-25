import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import type {
  CiudadPublica,
  Contratacion,
  Contratar,
  PlanPublico,
  SlugVerificado,
} from '../models/contratacion.models';

/**
 * Errores previstos del CU-11. El formulario reacciona distinto a cada uno:
 * vuelve al slug con sugerencias (5a), se queda en el pago (6a) o marca el
 * correo.
 */
export type ErrorContratacion =
  | { tipo: 'slug-ocupado'; mensaje: string; sugerencias: string[] }
  | { tipo: 'pago-rechazado'; mensaje: string }
  | { tipo: 'correo-repetido'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** P12 · CU-11 Contratar un plan desde la web. Público: no lleva sesión. */
@Injectable({ providedIn: 'root' })
export class ContratacionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/contratar`;

  planes(): Observable<PlanPublico[]> {
    return this.http.get<PlanPublico[]>(`${this.base}/planes`).pipe(catchError((e) => this.traducir(e)));
  }

  ciudades(): Observable<CiudadPublica[]> {
    return this.http
      .get<CiudadPublica[]>(`${this.base}/ciudades`)
      .pipe(catchError((e) => this.traducir(e)));
  }

  verificarSlug(valor: string): Observable<SlugVerificado> {
    const params = new HttpParams().set('valor', valor);
    return this.http
      .get<SlugVerificado>(`${this.base}/slug`, { params })
      .pipe(catchError((e) => this.traducir(e)));
  }

  contratar(datos: Contratar): Observable<Contratacion> {
    return this.http.post<Contratacion>(this.base, datos).pipe(catchError((e) => this.traducir(e)));
  }

  private traducir(e: HttpErrorResponse): Observable<never> {
    const cuerpo = e.error ?? {};
    const detalle = typeof cuerpo.detail === 'string' ? cuerpo.detail : null;
    let error: ErrorContratacion;
    if (cuerpo.codigo === 'slug_ocupado') {
      error = { tipo: 'slug-ocupado', mensaje: detalle ?? '', sugerencias: cuerpo.sugerencias ?? [] };
    } else if (cuerpo.codigo === 'pago_rechazado') {
      error = { tipo: 'pago-rechazado', mensaje: detalle ?? 'El pago fue rechazado.' };
    } else if (cuerpo.codigo === 'correo_repetido') {
      error = { tipo: 'correo-repetido', mensaje: detalle ?? 'Ese correo ya tiene una cuenta.' };
    } else if (e.status === 422) {
      error = { tipo: 'validacion', mensaje: detalle ?? 'Revise los datos del formulario.' };
    } else {
      error = { tipo: 'sistema', mensaje: 'No se pudo completar la operación. Intente de nuevo.' };
    }
    return throwError(() => error);
  }
}
