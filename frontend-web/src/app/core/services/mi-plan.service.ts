import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { MiPlan } from '../models/mi-plan.models';

export type ErrorMiPlan =
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** CU-04 · el cliente HTTP de «Mi plan». Un solo `GET` trae la pantalla entera. */
@Injectable({ providedIn: 'root' })
export class MiPlanService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/plataforma/mi-plan`;

  consultar(): Observable<MiPlan> {
    return this.http
      .get<MiPlan>(this.url)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorMiPlan {
    const detalle: string = typeof error.error?.detail === 'string' ? error.error.detail : '';
    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: detalle || 'Solo el administrador de la empresa ve su plan.' };
    }
    if (error.status === 0) {
      return { tipo: 'sistema', mensaje: 'No se pudo contactar al servidor. Verifique su conexión.' };
    }
    return { tipo: 'sistema', mensaje: detalle || 'No se pudo consultar el plan.' };
  }
}
