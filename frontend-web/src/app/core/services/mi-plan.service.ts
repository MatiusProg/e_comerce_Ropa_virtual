import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

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

  /**
   * ¿El plan vigente incluye esta función? Para mostrar el candado ANTES del
   * clic. `null` si no se pudo saber: la pantalla sigue como siempre y el
   * servidor es el que decide (CU-05).
   */
  incluye(codigo: string): Observable<boolean | null> {
    return this.http.get<MiPlan>(this.url).pipe(
      map((p) => {
        const f = p.plan?.funciones.find((x) => x.codigo === codigo);
        return f ? f.incluida : null;
      }),
      catchError(() => of(null)),
    );
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
