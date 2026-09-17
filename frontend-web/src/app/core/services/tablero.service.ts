import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { ConsultaTablero, Tablero } from '../models/tablero.models';

export type ErrorTablero =
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-36 — el cliente HTTP del tablero de indicadores.
 *
 * Servicio propio y no un método dentro de otro: P11 tiene dos casos de uso
 * —CU-36 y CU-37, que exporta a PDF y Excel— y cada uno con su contrato. Es la
 * misma razón por la que `ConsolidadoService` no vive dentro de
 * `InventarioService`.
 *
 * **Un solo `GET` trae el tablero entero.** Seis peticiones serían seis viajes
 * que recorren lo mismo, y abrirían la posibilidad de que dos tarjetas de la
 * misma pantalla muestren períodos distintos si una llega tarde.
 */
@Injectable({ providedIn: 'root' })
export class TableroService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/reportes`;

  consultar(consulta: ConsultaTablero = {}): Observable<Tablero> {
    let params = new HttpParams();
    if (consulta.desde) params = params.set('desde', consulta.desde);
    if (consulta.hasta) params = params.set('hasta', consulta.hasta);
    if (consulta.sucursal_id) params = params.set('sucursal_id', consulta.sucursal_id);
    return this.http
      .get<Tablero>(`${this.base}/tablero`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorTablero {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: 'El tablero de indicadores es del Administrador.',
      };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return {
      tipo: 'sistema',
      mensaje: detalle || 'No se pudo consultar el tablero.',
    };
  }
}
