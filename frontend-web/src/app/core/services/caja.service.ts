import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { AbrirTurno, Caja, CerrarTurno, Turno } from '../models/caja.models';

export type ErrorCaja =
  | { tipo: 'ocupada'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-30 — el cliente HTTP de la caja.
 *
 * EL TURNO ABIERTO VIVE EN UNA SEÑAL COMPARTIDA
 * ----------------------------------------------
 * Porque **CU-31 lo va a necesitar**: una venta presencial exige un turno
 * abierto —lo dice el CHECK `turno_segun_canal` del esquema— y la pantalla del
 * punto de venta tiene que saber si hay uno sin volver a preguntarlo.
 *
 * Con dos consultas separadas, abrir el turno en una pestaña y vender en otra
 * dejaría a la segunda creyendo que no hay turno. La señal es lo que mantiene a
 * las dos pantallas diciendo lo mismo.
 */
@Injectable({ providedIn: 'root' })
export class CajaService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/caja`;

  private readonly _turno = signal<Turno | null>(null);
  /** El turno abierto de quien está usando el sistema, o nada. */
  readonly turno = this._turno.asReadonly();

  cajas(): Observable<Caja[]> {
    return this.http
      .get<Caja[]>(`${this.base}/cajas`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Consulta el turno abierto y actualiza la señal. */
  miTurno(): Observable<Turno | null> {
    return this.http.get<Turno | null>(`${this.base}/turnos/mio`).pipe(
      tap((t) => this._turno.set(t)),
      catchError((e) => throwError(() => this.traducir(e))),
    );
  }

  abrir(datos: AbrirTurno): Observable<Turno> {
    return this.http.post<Turno>(`${this.base}/turnos`, datos).pipe(
      tap((t) => this._turno.set(t)),
      catchError((e) => throwError(() => this.traducir(e))),
    );
  }

  cerrar(turnoId: number, datos: CerrarTurno): Observable<Turno> {
    return this.http.post<Turno>(`${this.base}/turnos/${turnoId}/cierre`, datos).pipe(
      // Cerrado deja de ser «el turno abierto»: la señal vuelve a nada para que
      // el punto de venta sepa que ya no se puede cobrar.
      tap(() => this._turno.set(null)),
      catchError((e) => throwError(() => this.traducir(e))),
    );
  }

  private traducir(error: HttpErrorResponse): ErrorCaja {
    const detalle: unknown = error.error?.detail;
    const texto = typeof detalle === 'string' ? detalle : '';

    if (error.status === 409) {
      return { tipo: 'ocupada', mensaje: texto || 'Esa caja ya está abierta.' };
    }
    if (error.status === 403) {
      return { tipo: 'sin-permiso', mensaje: texto || 'La caja es del Cajero.' };
    }
    if (error.status === 404) {
      return { tipo: 'no-existe', mensaje: texto || 'No existe esa caja.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: texto || 'No se pudo operar la caja.' };
  }
}
