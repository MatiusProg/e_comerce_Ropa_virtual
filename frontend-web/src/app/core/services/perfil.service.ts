import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  CambioContrasena,
  Direccion,
  DireccionCrear,
  Perfil,
  PerfilEditar,
} from '../models/perfil.models';

/**
 * Errores previstos de CU-04, traducidos desde el código HTTP.
 *
 * `contrasena-actual` es el que importa: la excepción E1 devuelve el control al
 * paso 3c, así que el diálogo necesita distinguirlo para marcar ese campo y no
 * cerrarse.
 */
export type ErrorPerfil =
  | { tipo: 'correo-duplicado'; mensaje: string }
  | { tipo: 'documento-duplicado'; mensaje: string }
  | { tipo: 'contrasena-actual'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * CU-04 · Gestionar perfil del cliente.
 *
 * Ningún método recibe el identificador del cliente: el servidor lo resuelve
 * desde el token. Por eso tampoco hay forma de pedir el perfil de otro.
 */
@Injectable({ providedIn: 'root' })
export class PerfilService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/perfil`;

  /** Pasos 1 y 2 del flujo principal. */
  obtener(): Observable<Perfil> {
    return this.http
      .get<Perfil>(this.base)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Pasos 3 a 5: solo viajan los campos que se modificaron. */
  editar(datos: PerfilEditar): Observable<Perfil> {
    return this.http
      .patch<Perfil>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3a. Devuelve la lista completa ya reordenada. */
  agregarDireccion(datos: DireccionCrear): Observable<Direccion[]> {
    return this.http
      .post<Direccion[]>(`${this.base}/direcciones`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  marcarPredeterminada(id: number): Observable<Direccion[]> {
    return this.http
      .patch<Direccion[]>(`${this.base}/direcciones/${id}/predeterminada`, {})
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3b. La confirmación previa la pide la pantalla. */
  eliminarDireccion(id: number): Observable<Direccion[]> {
    return this.http
      .delete<Direccion[]>(`${this.base}/direcciones/${id}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Flujo alternativo 3c. Al cambiarla, el servidor revoca las sesiones. */
  cambiarContrasena(datos: CambioContrasena): Observable<void> {
    return this.http
      .put<void>(`${this.base}/contrasena`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  private traducir(error: HttpErrorResponse): ErrorPerfil {
    const detalle: string =
      typeof error.error?.detail === 'string' ? error.error.detail : '';

    // Excepción E2.
    if (error.status === 409) {
      if (detalle.includes('documento')) {
        return { tipo: 'documento-duplicado', mensaje: detalle };
      }
      return { tipo: 'correo-duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
      // Excepción E1: el servidor la devuelve como 422 con este texto.
      if (detalle.includes('contraseña actual')) {
        return { tipo: 'contrasena-actual', mensaje: detalle };
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
