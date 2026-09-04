import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Ciudad,
  CiudadCrear,
  CiudadEditar,
  FiltrosSucursales,
  Sucursal,
  SucursalBreve,
  SucursalCrear,
  SucursalEditar,
} from '../models/organizacion.models';

/**
 * Errores previstos de CU-05, traducidos desde el código HTTP.
 *
 * `ciudad-con-sucursales` es el que importa: la excepción E2 pide decir que
 * primero hay que dar de baja las sucursales, y la interfaz necesita
 * distinguirlo de un conflicto cualquiera para explicar la salida.
 */
export type ErrorOrganizacion =
  | { tipo: 'nombre-duplicado'; mensaje: string }
  | { tipo: 'ciudad-con-sucursales'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * P2 · Organización — CU-05 Gestionar ciudades y sucursales.
 *
 * El listado de sucursales es un solo endpoint: sirve al paso 2 del caso de
 * uso y, con `activa=true`, al selector del formulario de CU-03.
 */
@Injectable({ providedIn: 'root' })
export class OrganizacionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/organizacion`;

  // --- Selector de CU-03 -------------------------------------------------

  /**
   * Sucursales activas, para poblar el selector del formulario de usuarios.
   *
   * El `activa=true` es obligatorio: sin él el endpoint devuelve también las
   * dadas de baja, y CU-03 rechaza asignar un empleado a una sucursal inactiva.
   */
  sucursales(): Observable<SucursalBreve[]> {
    return this.http.get<SucursalBreve[]>(`${this.base}/sucursales`, {
      params: new HttpParams().set('activa', true),
    });
  }

  // --- CU-05 Ciudades (flujo alternativo 3a) -----------------------------

  listarCiudades(busqueda?: string): Observable<Ciudad[]> {
    let params = new HttpParams();
    if (busqueda) params = params.set('busqueda', busqueda);
    return this.http
      .get<Ciudad[]>(`${this.base}/ciudades`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearCiudad(datos: CiudadCrear): Observable<Ciudad> {
    return this.http
      .post<Ciudad>(`${this.base}/ciudades`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarCiudad(id: number, datos: CiudadEditar): Observable<Ciudad> {
    return this.http
      .patch<Ciudad>(`${this.base}/ciudades/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  eliminarCiudad(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/ciudades/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- CU-05 Sucursales --------------------------------------------------

  listarSucursales(filtros: FiltrosSucursales = {}): Observable<Sucursal[]> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.ciudad_id !== undefined) params = params.set('ciudad_id', filtros.ciudad_id);
    if (filtros.activa !== undefined) params = params.set('activa', filtros.activa);
    return this.http
      .get<Sucursal[]>(`${this.base}/sucursales`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crearSucursal(datos: SucursalCrear): Observable<Sucursal> {
    return this.http
      .post<Sucursal>(`${this.base}/sucursales`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editarSucursal(id: number, datos: SucursalEditar): Observable<Sucursal> {
    return this.http
      .patch<Sucursal>(`${this.base}/sucursales/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3c: la baja no borra, marca la sucursal como inactiva. */
  cambiarEstadoSucursal(id: number, activa: boolean): Observable<Sucursal> {
    return this.http
      .patch<Sucursal>(`${this.base}/sucursales/${id}/estado`, { activa })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Traducción de errores ---------------------------------------------

  private traducir(error: HttpErrorResponse): ErrorOrganizacion {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 404) {
      return { tipo: 'no-encontrado', mensaje: detalle || 'El registro ya no existe.' };
    }

    if (error.status === 409) {
      if (detalle.includes('sucursales')) {
        // Excepción E2, y también el caso de la ciudad con historial.
        return { tipo: 'ciudad-con-sucursales', mensaje: detalle };
      }
      return { tipo: 'nombre-duplicado', mensaje: detalle };
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
