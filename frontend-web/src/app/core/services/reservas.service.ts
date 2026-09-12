import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  AtenderReserva,
  CancelarReserva,
  Expiracion,
  FiltrosReservas,
  PaginaReservas,
  Reserva,
  ReservaCrear,
} from '../models/reservas.models';

/**
 * Errores previstos de CU-22 a CU-25, traducidos desde el código HTTP.
 *
 * Se distinguen y no se colapsan en «error» porque cada uno lleva a una acción
 * distinta:
 *
 * - `sin-stock` (E9) es la carrera perdida contra otro cliente —el riesgo R5—
 *   y la pantalla tiene que ofrecer volver a mirar la disponibilidad.
 * - `sin-probadores` (E6) manda a elegir otra franja, no otra prenda.
 * - `franja-invalida` (E3, E4, E5, E8) devuelve el control al selector de hora.
 * - `estado-final` (E10) casi siempre significa que la pantalla está vieja: lo
 *   que corresponde es refrescar, no reintentar.
 * - `lineas-invalidas` trae **qué** prendas fallaron, para señalarlas.
 */
export type ErrorReservas =
  | { tipo: 'lineas-invalidas'; mensaje: string; variantes: number[] }
  | { tipo: 'resultados-incompletos'; mensaje: string; detalles: number[] }
  | { tipo: 'sin-stock'; mensaje: string }
  | { tipo: 'sin-probadores'; mensaje: string }
  | { tipo: 'franja-invalida'; mensaje: string }
  | { tipo: 'estado-final'; mensaje: string }
  | { tipo: 'no-encontrada'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'sin-ficha'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class ReservasService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  // --- Cliente · CU-22 y CU-23 -------------------------------------------

  crear(datos: ReservaCrear): Observable<Reserva> {
    return this.http
      .post<Reserva>(`${this.base}/reservas`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  misReservas(filtros: FiltrosReservas = {}): Observable<PaginaReservas> {
    return this.http
      .get<PaginaReservas>(`${this.base}/reservas`, { params: this.parametros(filtros) })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  obtener(id: number): Observable<Reserva> {
    return this.http
      .get<Reserva>(`${this.base}/reservas/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cancelar(id: number, datos: CancelarReserva = {}): Observable<Reserva> {
    return this.http
      .patch<Reserva>(`${this.base}/reservas/${id}/cancelacion`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Sucursal · CU-24 ---------------------------------------------------

  deMiSucursal(filtros: FiltrosReservas = {}): Observable<PaginaReservas> {
    return this.http
      .get<PaginaReservas>(`${this.base}/sucursal/reservas`, {
        params: this.parametros(filtros),
      })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  obtenerDeSucursal(id: number): Observable<Reserva> {
    return this.http
      .get<Reserva>(`${this.base}/sucursal/reservas/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  preparar(id: number): Observable<Reserva> {
    return this.http
      .patch<Reserva>(`${this.base}/sucursal/reservas/${id}/preparacion`, {})
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  atender(id: number, datos: AtenderReserva): Observable<Reserva> {
    return this.http
      .patch<Reserva>(`${this.base}/sucursal/reservas/${id}/atencion`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Mantenimiento · CU-25 ---------------------------------------------

  /**
   * Dispara una corrida de la expiración.
   *
   * En producción la llama un planificador; se expone acá para poder mostrar el
   * efecto en vivo y porque devuelve **qué hizo**, no un «listo».
   */
  expirarVencidas(): Observable<Expiracion> {
    return this.http
      .post<Expiracion>(`${this.base}/mantenimiento/reservas/expiracion`, {})
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Internos -----------------------------------------------------------

  private parametros(filtros: FiltrosReservas): HttpParams {
    let params = new HttpParams();
    if (filtros.estado) params = params.set('estado', filtros.estado);
    if (filtros.vivas !== undefined) params = params.set('vivas', filtros.vivas);
    if (filtros.pagina) params = params.set('pagina', filtros.pagina);
    if (filtros.tamano) params = params.set('tamano', filtros.tamano);
    return params;
  }

  private traducir(error: HttpErrorResponse): ErrorReservas {
    const bruto = error.error?.detail;
    const detalle: string = typeof bruto === 'string' ? bruto : '';

    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: detalle || 'No tiene permisos para esta operación.',
      };
    }

    if (error.status === 404) {
      // El servidor devuelve el mismo 404 para «no existe» y «es de otro
      // cliente», a propósito: un 403 confirmaría que esa reserva existe.
      return { tipo: 'no-encontrada', mensaje: detalle || 'No encontramos esa reserva.' };
    }

    if (error.status === 409) {
      if (detalle.includes('probadores')) {
        return { tipo: 'sin-probadores', mensaje: detalle };
      }
      if (detalle.includes('ficha de cliente')) {
        return { tipo: 'sin-ficha', mensaje: detalle };
      }
      if (detalle.includes('unidades') || detalle.includes('disponible')) {
        return { tipo: 'sin-stock', mensaje: detalle };
      }
      // Ya fue atendida, ya estaba cancelada, ya venció, ya estaba preparada.
      return {
        tipo: 'estado-final',
        mensaje: detalle || 'Esa reserva ya no admite esta operación.',
      };
    }

    if (error.status === 422) {
      // E1 y E11 viajan como objeto y no como texto: traen qué falló.
      if (bruto && typeof bruto === 'object') {
        if (Array.isArray(bruto.variantes)) {
          return {
            tipo: 'lineas-invalidas',
            mensaje: bruto.mensaje ?? 'Hay prendas que no se pueden reservar.',
            variantes: bruto.variantes,
          };
        }
        if (Array.isArray(bruto.detalles)) {
          return {
            tipo: 'resultados-incompletos',
            mensaje: bruto.mensaje ?? 'Faltan resultados.',
            detalles: bruto.detalles,
          };
        }
      }
      if (
        detalle.includes('franja') ||
        detalle.includes('anticipación') ||
        detalle.includes('atiende') ||
        detalle.includes('pasó')
      ) {
        return { tipo: 'franja-invalida', mensaje: detalle };
      }
      // FastAPI manda `detail` como lista en los errores de esquema.
      return {
        tipo: 'validacion',
        mensaje: detalle || 'Revise los datos del formulario.',
      };
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
