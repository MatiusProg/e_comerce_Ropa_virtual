import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Empleado,
  EmpleadoCrear,
  EmpleadoEditar,
  FiltrosEmpleados,
  UsuarioVinculable,
} from '../models/empleados.models';

/**
 * Errores previstos de CU-06, traducidos desde el código HTTP.
 *
 * `documento-duplicado` y `sucursal-inactiva` son los que importan: las
 * excepciones E1 y E2 devuelven el control al formulario, así que la interfaz
 * necesita distinguirlas para señalar el campo sin cerrar el diálogo.
 */
export type ErrorEmpleados =
  | { tipo: 'documento-duplicado'; mensaje: string }
  | { tipo: 'correo-duplicado'; mensaje: string }
  | { tipo: 'sucursal-inactiva'; mensaje: string }
  | { tipo: 'no-vinculable'; mensaje: string }
  | { tipo: 'ya-dado-de-baja'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-06 · Gestionar empleados.
 *
 * Archivo propio, y no métodos nuevos en `OrganizacionService`, para que el
 * CU-07 pueda avanzar en paralelo sin que compartamos archivo.
 */
@Injectable({ providedIn: 'root' })
export class EmpleadosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/organizacion/empleados`;

  listar(filtros: FiltrosEmpleados = {}): Observable<Empleado[]> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.sucursal_id !== undefined) {
      params = params.set('sucursal_id', filtros.sucursal_id);
    }
    if (filtros.cargo) params = params.set('cargo', filtros.cargo);
    if (filtros.activo !== undefined) params = params.set('activo', filtros.activo);

    return this.http
      .get<Empleado[]>(this.base, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Cuentas existentes sin ficha de empleado (flujo alternativo 3c). */
  usuariosVinculables(): Observable<UsuarioVinculable[]> {
    return this.http
      .get<UsuarioVinculable[]>(`${this.base}/usuarios-vinculables`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crear(datos: EmpleadoCrear): Observable<Empleado> {
    return this.http
      .post<Empleado>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3a. Cambiar cargo o sucursal revoca las sesiones. */
  editar(id: number, datos: EmpleadoEditar): Observable<Empleado> {
    return this.http
      .patch<Empleado>(`${this.base}/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3b. Sin fecha, el servidor usa la de hoy. */
  darDeBaja(id: number, fecha_baja?: string): Observable<Empleado> {
    return this.http
      .patch<Empleado>(`${this.base}/${id}/baja`, { fecha_baja: fecha_baja ?? null })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorEmpleados {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 409) {
      if (detalle.includes('documento')) {
        // Excepción E1.
        return { tipo: 'documento-duplicado', mensaje: detalle };
      }
      if (detalle.includes('dado de baja')) {
        return { tipo: 'ya-dado-de-baja', mensaje: detalle };
      }
      return { tipo: 'correo-duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
      if (detalle.includes('dada de baja')) {
        // Excepción E2.
        return { tipo: 'sucursal-inactiva', mensaje: detalle };
      }
      if (detalle.includes('vincular')) {
        return { tipo: 'no-vinculable', mensaje: detalle };
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
