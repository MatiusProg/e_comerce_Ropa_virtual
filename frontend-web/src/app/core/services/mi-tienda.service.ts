import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { ColoresMarca, MarcaEmpresa } from '../models/mi-tienda.models';
import { rechazoDelPlan } from '../models/plan.models';

/** Errores previstos del CU-12, traducidos desde el código HTTP. */
export type ErrorMiTienda =
  /** 1a: el plan no incluye la marca propia (CU-05). */
  | { tipo: 'plan'; mensaje: string }
  /** 4a: el logo no es una imagen válida. */
  | { tipo: 'imagen'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** CU-12 · el cliente HTTP de «Mi tienda». */
@Injectable({ providedIn: 'root' })
export class MiTiendaService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/plataforma/mi-tienda`;

  obtener(): Observable<MarcaEmpresa> {
    return this.http.get<MarcaEmpresa>(this.base).pipe(catchError((e) => this.fallar(e)));
  }

  guardarColores(colores: ColoresMarca): Observable<MarcaEmpresa> {
    return this.http
      .put<MarcaEmpresa>(`${this.base}/colores`, colores)
      .pipe(catchError((e) => this.fallar(e)));
  }

  subirLogo(archivo: File): Observable<MarcaEmpresa> {
    const datos = new FormData();
    datos.append('archivo', archivo);
    return this.http
      .post<MarcaEmpresa>(`${this.base}/logo`, datos)
      .pipe(catchError((e) => this.fallar(e)));
  }

  quitarLogo(): Observable<MarcaEmpresa> {
    return this.http
      .delete<MarcaEmpresa>(`${this.base}/logo`)
      .pipe(catchError((e) => this.fallar(e)));
  }

  private fallar(error: HttpErrorResponse): Observable<never> {
    return throwError(() => this.traducir(error));
  }

  private traducir(error: HttpErrorResponse): ErrorMiTienda {
    const detalle: string = typeof error.error?.detail === 'string' ? error.error.detail : '';
    const plan = rechazoDelPlan(error);
    if (plan) {
      return { tipo: 'plan', mensaje: plan.detail };
    }
    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: detalle || 'Solo el administrador de la empresa.' };
    }
    if (error.status === 422) {
      return {
        tipo: 'imagen',
        mensaje: detalle || 'El logo tiene que ser una imagen PNG, JPEG o WEBP.',
      };
    }
    if (error.status === 0) {
      return { tipo: 'sistema', mensaje: 'No se pudo contactar al servidor. Verifique su conexión.' };
    }
    return { tipo: 'sistema', mensaje: detalle || 'No se pudo guardar la marca.' };
  }
}
