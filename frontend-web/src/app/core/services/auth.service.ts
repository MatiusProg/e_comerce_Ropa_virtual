import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { ClienteRegistradoOut, ClienteRegistroIn } from '../models/auth.models';

/**
 * Errores previstos del registro, traducidos desde el código HTTP.
 * El componente decide cómo mostrarlos; el servicio no conoce la interfaz.
 */
export type ErrorRegistro =
  | { tipo: 'correo-duplicado'; mensaje: string }
  | { tipo: 'documento-duplicado'; mensaje: string }
  | { tipo: 'datos-invalidos'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * P1 · Seguridad y Usuarios — acceso a los endpoints de `/auth`.
 *
 * Realiza CU-01. CU-02 (login/logout) se agrega en el siguiente paso, junto
 * con el almacenamiento del token y el interceptor.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/auth`;

  /** CU-01 · Registrar cliente. */
  registrar(datos: ClienteRegistroIn): Observable<ClienteRegistradoOut> {
    return this.http
      .post<ClienteRegistradoOut>(`${this.base}/registro`, datos)
      .pipe(catchError((error: HttpErrorResponse) => throwError(() => this.traducir(error))));
  }

  /**
   * Convierte la respuesta de error en algo que el componente pueda mostrar.
   *
   * El 409 puede venir por correo o por documento; se distinguen por el texto
   * del `detail` que emite el router, para poder ofrecer «iniciar sesión» solo
   * cuando corresponde (excepción E1 de CU-01).
   */
  private traducir(error: HttpErrorResponse): ErrorRegistro {
    const detalle: string = error.error?.detail ?? '';

    if (error.status === 409) {
      return detalle.includes('documento')
        ? { tipo: 'documento-duplicado', mensaje: detalle }
        : { tipo: 'correo-duplicado', mensaje: detalle };
    }

    if (error.status === 422) {
      return {
        tipo: 'datos-invalidos',
        mensaje: 'Revise los datos del formulario.',
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
      mensaje: detalle || 'Ocurrió un error al procesar el registro.',
    };
  }
}
