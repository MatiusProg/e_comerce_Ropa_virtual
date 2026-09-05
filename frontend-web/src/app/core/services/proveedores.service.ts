import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  AccesoProveedor,
  FiltrosProveedores,
  Proveedor,
  ProveedorCrear,
  ProveedorEditar,
} from '../models/proveedores.models';

/**
 * Errores previstos de CU-07, traducidos desde el código HTTP.
 *
 * `identificacion-duplicada` y `correo-duplicado` se distinguen porque marcan
 * campos distintos, y en dos formularios distintos: la identificación está en
 * el formulario del proveedor y el correo en el de habilitar acceso.
 */
export type ErrorProveedores =
  | { tipo: 'identificacion-duplicada'; mensaje: string }
  | { tipo: 'correo-duplicado'; mensaje: string }
  | { tipo: 'acceso-ya-habilitado'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** P2 · Organización — CU-07 Gestionar proveedores. */
@Injectable({ providedIn: 'root' })
export class ProveedoresService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/organizacion/proveedores`;
  private readonly baseMiFicha = `${environment.apiUrl}/organizacion/mi-ficha`;

  listar(filtros: FiltrosProveedores = {}): Observable<Proveedor[]> {
    let params = new HttpParams();
    if (filtros.busqueda) params = params.set('busqueda', filtros.busqueda);
    if (filtros.activo !== undefined) params = params.set('activo', filtros.activo);
    return this.http
      .get<Proveedor[]>(this.base, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  crear(datos: ProveedorCrear): Observable<Proveedor> {
    return this.http
      .post<Proveedor>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  editar(id: number, datos: ProveedorEditar): Observable<Proveedor> {
    return this.http
      .patch<Proveedor>(`${this.base}/${id}`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3b: la baja no borra, conserva los productos históricos. */
  cambiarEstado(id: number, activo: boolean): Observable<Proveedor> {
    return this.http
      .patch<Proveedor>(`${this.base}/${id}/estado`, { activo })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3c. */
  habilitarAcceso(id: number, datos: AccesoProveedor): Observable<Proveedor> {
    return this.http
      .post<Proveedor>(`${this.base}/${id}/acceso`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Los datos del proveedor que porta el token. Solo para el rol Proveedor. */
  miFicha(): Observable<Proveedor> {
    return this.http
      .get<Proveedor>(this.baseMiFicha)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorProveedores {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    if (error.status === 404) {
      return { tipo: 'no-encontrado', mensaje: detalle || 'El registro ya no existe.' };
    }

    if (error.status === 409) {
      if (detalle.includes('identificación')) {
        return { tipo: 'identificacion-duplicada', mensaje: detalle };
      }
      if (detalle.includes('acceso habilitado')) {
        return { tipo: 'acceso-ya-habilitado', mensaje: detalle };
      }
      return { tipo: 'correo-duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
      // FastAPI manda `detail` como lista en los errores de validación, así
      // que `detalle` queda vacío y se usa el mensaje genérico.
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
