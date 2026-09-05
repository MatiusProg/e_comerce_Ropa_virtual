import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Coleccion,
  ColeccionCrear,
  ColeccionEditar,
  FiltrosColecciones,
  FiltrosTemporadas,
  Temporada,
  TemporadaCrear,
  TemporadaEditar,
} from '../models/temporadas.models';

/**
 * Errores previstos de CU-09, traducidos desde el código HTTP.
 *
 * `solapamiento` es el que importa: la excepción E2 no es un rechazo sino una
 * advertencia que se puede confirmar, así que la interfaz necesita
 * distinguirlo de un 409 cualquiera para poder ofrecer «guardar igual».
 * `con-colecciones` es la E3, que sí es un rechazo pero ofrece cerrar.
 */
export type ErrorTemporadas =
  | { tipo: 'solapamiento'; mensaje: string }
  | { tipo: 'nombre-duplicado'; mensaje: string }
  | { tipo: 'con-colecciones'; mensaje: string }
  | { tipo: 'rango-invalido'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** Marca que el backend antepone al 409 de solapamiento. */
const MARCA_SOLAPAMIENTO = 'SOLAPAMIENTO:';

@Injectable({ providedIn: 'root' })
export class TemporadasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/catalogo`;

  // --- Temporadas --------------------------------------------------------

  listarTemporadas(filtros: FiltrosTemporadas = {}): Observable<Temporada[]> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.activa !== undefined) params = params.set('activa', filtros.activa);
    return this.http
      .get<Temporada[]>(`${this.base}/temporadas`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearTemporada(datos: TemporadaCrear): Observable<Temporada> {
    return this.http
      .post<Temporada>(`${this.base}/temporadas`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarTemporada(id: number, datos: TemporadaEditar): Observable<Temporada> {
    return this.http
      .patch<Temporada>(`${this.base}/temporadas/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3b: cerrar o reabrir. */
  cambiarEstadoTemporada(
    id: number,
    activa: boolean,
    confirmarSolapamiento = false,
  ): Observable<Temporada> {
    return this.http
      .patch<Temporada>(`${this.base}/temporadas/${id}/estado`, {
        activa,
        confirmar_solapamiento: confirmarSolapamiento,
      })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Excepción E3: falla si la temporada tiene colecciones. */
  eliminarTemporada(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/temporadas/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Colecciones (flujo alternativo 1a) --------------------------------

  listarColecciones(filtros: FiltrosColecciones = {}): Observable<Coleccion[]> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.temporada_id !== undefined)
      params = params.set('temporada_id', filtros.temporada_id);
    if (filtros.activa !== undefined) params = params.set('activa', filtros.activa);
    return this.http
      .get<Coleccion[]>(`${this.base}/colecciones`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearColeccion(datos: ColeccionCrear): Observable<Coleccion> {
    return this.http
      .post<Coleccion>(`${this.base}/colecciones`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarColeccion(id: number, datos: ColeccionEditar): Observable<Coleccion> {
    return this.http
      .patch<Coleccion>(`${this.base}/colecciones/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cambiarEstadoColeccion(id: number, activa: boolean): Observable<Coleccion> {
    return this.http
      .patch<Coleccion>(`${this.base}/colecciones/${id}/estado`, { activa })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Traducción de errores ---------------------------------------------

  private traducir(error: HttpErrorResponse): ErrorTemporadas {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 404) {
      return { tipo: 'no-encontrado', mensaje: detalle || 'El registro ya no existe.' };
    }

    if (error.status === 409) {
      if (detalle.startsWith(MARCA_SOLAPAMIENTO)) {
        // Se quita la marca: es para la interfaz, no para el usuario.
        return {
          tipo: 'solapamiento',
          mensaje: detalle.slice(MARCA_SOLAPAMIENTO.length).trim(),
        };
      }
      if (detalle.includes('colecciones asociadas')) {
        return { tipo: 'con-colecciones', mensaje: detalle };
      }
      return { tipo: 'nombre-duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
      // FastAPI manda `detail` como lista en los errores de validación de
      // esquema, así que `detalle` queda vacío y se usa el genérico.
      return {
        tipo: detalle ? 'rango-invalido' : 'validacion',
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
