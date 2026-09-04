import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  FiltrosUsuarios,
  PaginaUsuarios,
  RolAsignable,
  UsuarioCrear,
  UsuarioEditar,
  UsuarioResumen,
} from '../models/usuarios.models';

/**
 * Errores previstos de CU-03, traducidos desde el código HTTP.
 *
 * `no-eliminable` es el que importa: el caso de uso pide que, cuando no se
 * puede borrar, se ofrezca desactivar en su lugar. La interfaz necesita
 * distinguirlo de un conflicto cualquiera para poder ofrecer esa salida.
 */
export type ErrorUsuarios =
  | { tipo: 'correo-duplicado'; mensaje: string }
  | { tipo: 'documento-duplicado'; mensaje: string }
  | { tipo: 'auto-operacion'; mensaje: string }
  | { tipo: 'no-eliminable'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/usuarios`;
  private readonly baseAuth = `${environment.apiUrl}/auth`;

  roles(): Observable<RolAsignable[]> {
    return this.http
      .get<RolAsignable[]>(`${this.baseAuth}/roles`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  listar(filtros: FiltrosUsuarios): Observable<PaginaUsuarios> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.rol) params = params.set('rol', filtros.rol);
    if (filtros.activo !== undefined) params = params.set('activo', filtros.activo);
    params = params.set('pagina', filtros.pagina ?? 1);
    params = params.set('tamano', filtros.tamano ?? 10);

    return this.http
      .get<PaginaUsuarios>(this.base, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crear(datos: UsuarioCrear): Observable<UsuarioResumen> {
    return this.http
      .post<UsuarioResumen>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editar(id: number, datos: UsuarioEditar): Observable<UsuarioResumen> {
    return this.http
      .patch<UsuarioResumen>(`${this.base}/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cambiarEstado(id: number, activo: boolean): Observable<UsuarioResumen> {
    return this.http
      .patch<UsuarioResumen>(`${this.base}/${id}/estado`, { activo })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminar(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorUsuarios {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 409) {
      if (detalle.includes('operaciones asociadas')) {
        return { tipo: 'no-eliminable', mensaje: detalle };
      }
      if (detalle.includes('propia cuenta')) {
        return { tipo: 'auto-operacion', mensaje: detalle };
      }
      if (detalle.includes('documento')) {
        return { tipo: 'documento-duplicado', mensaje: detalle };
      }
      return { tipo: 'correo-duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
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
