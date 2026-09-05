import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Categoria,
  CategoriaCrear,
  CategoriaEditar,
  Color,
  ColorCrear,
  ColorEditar,
  Talla,
  TallaCrear,
  TallaEditar,
} from '../models/maestros.models';

/**
 * Errores previstos de CU-08, traducidos desde el código HTTP.
 *
 * `no-eliminable` es el que importa: la excepción E3 pide que, cuando no se
 * puede borrar, se ofrezca desactivar en su lugar. La interfaz necesita
 * distinguirlo de un conflicto cualquiera para poder ofrecer esa salida.
 */
export type ErrorMaestros =
  | { tipo: 'duplicado'; mensaje: string }
  | { tipo: 'ciclo'; mensaje: string }
  | { tipo: 'no-eliminable'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** CU-08 · Maestros del catálogo: categorías, tallas y colores. */
@Injectable({ providedIn: 'root' })
export class MaestrosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/catalogo`;

  // --- Categorías --------------------------------------------------------

  /** Devuelve el árbol ya armado por el servidor. */
  categorias(): Observable<Categoria[]> {
    return this.http
      .get<Categoria[]>(`${this.base}/categorias`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearCategoria(datos: CategoriaCrear): Observable<Categoria> {
    return this.http
      .post<Categoria>(`${this.base}/categorias`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarCategoria(id: number, datos: CategoriaEditar): Observable<Categoria> {
    return this.http
      .patch<Categoria>(`${this.base}/categorias/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cambiarEstadoCategoria(id: number, activo: boolean): Observable<Categoria> {
    return this.http
      .patch<Categoria>(`${this.base}/categorias/${id}/estado`, { activo })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminarCategoria(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/categorias/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Tallas ------------------------------------------------------------

  tallas(tipo_prenda?: string): Observable<Talla[]> {
    let params = new HttpParams();
    if (tipo_prenda) params = params.set('tipo_prenda', tipo_prenda);

    return this.http
      .get<Talla[]>(`${this.base}/tallas`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Tipos ya usados, para que el formulario los ofrezca. */
  tiposDePrenda(): Observable<string[]> {
    return this.http
      .get<string[]>(`${this.base}/tallas/tipos`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearTalla(datos: TallaCrear): Observable<Talla> {
    return this.http
      .post<Talla>(`${this.base}/tallas`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarTalla(id: number, datos: TallaEditar): Observable<Talla> {
    return this.http
      .patch<Talla>(`${this.base}/tallas/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cambiarEstadoTalla(id: number, activo: boolean): Observable<Talla> {
    return this.http
      .patch<Talla>(`${this.base}/tallas/${id}/estado`, { activo })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminarTalla(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/tallas/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Colores -----------------------------------------------------------

  colores(): Observable<Color[]> {
    return this.http
      .get<Color[]>(`${this.base}/colores`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearColor(datos: ColorCrear): Observable<Color> {
    return this.http
      .post<Color>(`${this.base}/colores`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarColor(id: number, datos: ColorEditar): Observable<Color> {
    return this.http
      .patch<Color>(`${this.base}/colores/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cambiarEstadoColor(id: number, activo: boolean): Observable<Color> {
    return this.http
      .patch<Color>(`${this.base}/colores/${id}/estado`, { activo })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminarColor(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/colores/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorMaestros {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 409) {
      if (detalle.includes('dependencias')) {
        // Excepción E3: la interfaz usa esto para ofrecer desactivar.
        return { tipo: 'no-eliminable', mensaje: detalle };
      }
      // Excepción E1.
      return { tipo: 'duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
      if (detalle.includes('rama')) {
        // Excepción E2.
        return { tipo: 'ciclo', mensaje: detalle };
      }
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
