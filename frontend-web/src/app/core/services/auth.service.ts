import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, of, tap, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  ClienteRegistradoOut,
  ClienteRegistroIn,
  INICIO_POR_ROL,
  LoginIn,
  RecuperacionAceptadaOut,
  RecuperacionConfirmarIn,
  RecuperacionSolicitudIn,
  TokenOut,
  UsuarioAutenticado,
} from '../models/auth.models';

/** Errores previstos del registro (CU-01), traducidos desde el código HTTP. */
export type ErrorRegistro =
  | { tipo: 'correo-duplicado'; mensaje: string }
  | { tipo: 'documento-duplicado'; mensaje: string }
  | { tipo: 'datos-invalidos'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/** Errores previstos del inicio de sesión (CU-02). */
export type ErrorLogin =
  | { tipo: 'credenciales'; mensaje: string }
  | { tipo: 'desactivada'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * Errores previstos de la confirmación de recuperación (CU-41).
 *
 * La SOLICITUD no tiene errores previstos: responde lo mismo exista o no la
 * cuenta, así que solo puede fallar por red o por un fallo del servidor.
 */
export type ErrorRecuperacion =
  | { tipo: 'enlace-invalido'; mensaje: string }
  | { tipo: 'desactivada'; mensaje: string }
  | { tipo: 'datos-invalidos'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

const CLAVE_TOKEN = 'fs.token';

/**
 * P1 · Seguridad y Usuarios — CU-01 y CU-02.
 *
 * Guarda el token en `localStorage` para que la sesión sobreviva a recargar la
 * página. El usuario NO se guarda ahí: se vuelve a pedir a `/auth/yo` al
 * arrancar, porque el navegador es del usuario y lo que diga no es confiable —
 * y además el token pudo haber sido revocado desde otro lado.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly base = `${environment.apiUrl}/auth`;

  private readonly _usuario = signal<UsuarioAutenticado | null>(null);

  /** Usuario de la sesión en curso, o null. */
  readonly usuario = this._usuario.asReadonly();
  readonly autenticado = computed(() => this._usuario() !== null);
  readonly rol = computed(() => this._usuario()?.rol ?? null);

  get token(): string | null {
    try {
      return localStorage.getItem(CLAVE_TOKEN);
    } catch {
      // Modo privado o almacenamiento bloqueado: se sigue sin sesión.
      return null;
    }
  }

  private guardarToken(token: string): void {
    try {
      localStorage.setItem(CLAVE_TOKEN, token);
    } catch {
      /* sin persistencia: la sesión dura lo que dure la pestaña */
    }
  }

  private borrarToken(): void {
    try {
      localStorage.removeItem(CLAVE_TOKEN);
    } catch {
      /* nada que borrar */
    }
  }

  /** Ruta de inicio del rol de la sesión actual. */
  inicioDelRol(): string {
    const rol = this._usuario()?.rol;
    return rol ? INICIO_POR_ROL[rol] : '/login';
  }

  // --- CU-01 Registrar cliente -------------------------------------------

  registrar(datos: ClienteRegistroIn): Observable<ClienteRegistradoOut> {
    return this.http
      .post<ClienteRegistradoOut>(`${this.base}/registro`, datos)
      .pipe(
        catchError((e: HttpErrorResponse) => throwError(() => this.traducirRegistro(e))),
      );
  }

  // --- CU-02 Iniciar y cerrar sesión -------------------------------------

  iniciarSesion(datos: LoginIn): Observable<UsuarioAutenticado> {
    return this.http.post<TokenOut>(`${this.base}/login`, datos).pipe(
      tap((r) => {
        this.guardarToken(r.access_token);
        this._usuario.set(r.usuario);
      }),
      map((r) => r.usuario),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirLogin(e))),
    );
  }

  /**
   * Cierra la sesión en el servidor y limpia el estado local.
   *
   * El estado local se limpia SIEMPRE, aunque la llamada falle: si el token ya
   * no servía, insistir no tiene sentido y dejar al usuario "adentro" sería
   * peor que cerrarle la sesión de más.
   */
  cerrarSesion(): void {
    const terminar = () => {
      this.borrarToken();
      this._usuario.set(null);
      this.router.navigate(['/login']);
    };
    this.http.post<void>(`${this.base}/logout`, {}).subscribe({
      next: terminar,
      error: terminar,
    });
  }

  /**
   * Restaura la sesión al arrancar la aplicación, preguntándole al servidor.
   *
   * Devuelve el usuario o null; nunca falla. Un token revocado o vencido se
   * descarta acá, que es exactamente lo que hace que cerrar sesión en una
   * pestaña se note en la otra.
   */
  restaurarSesion(): Observable<UsuarioAutenticado | null> {
    if (!this.token) {
      return of(null);
    }
    return this.http.get<UsuarioAutenticado>(`${this.base}/yo`).pipe(
      tap((u) => this._usuario.set(u)),
      catchError(() => {
        this.borrarToken();
        this._usuario.set(null);
        return of(null);
      }),
    );
  }

  /** Descarta la sesión sin llamar al servidor. La usa el interceptor ante un 401. */
  descartarSesion(): void {
    this.borrarToken();
    this._usuario.set(null);
  }

  // --- CU-41 Recuperar contraseña ----------------------------------------

  /**
   * Pide el enlace de recuperación (paso 2).
   *
   * No traduce ningún error de negocio porque el servidor no expone ninguno:
   * responde 202 exista o no la cuenta. Ver `RecuperacionAceptadaOut`.
   */
  solicitarRecuperacion(
    datos: RecuperacionSolicitudIn,
  ): Observable<RecuperacionAceptadaOut> {
    return this.http
      .post<RecuperacionAceptadaOut>(`${this.base}/recuperacion`, datos)
      .pipe(
        catchError((e: HttpErrorResponse) =>
          throwError(() => this.traducirRecuperacion(e)),
        ),
      );
  }

  /**
   * Canjea el enlace y fija la contraseña nueva (paso 6).
   *
   * Al volver, todas las sesiones de esa cuenta quedaron revocadas en el
   * servidor —incluida la de esta pestaña, si la había—. Por eso se descarta
   * también la sesión local: dejarla puesta mostraría una sesión que ya no
   * existe y cada llamada siguiente daría 401.
   */
  confirmarRecuperacion(datos: RecuperacionConfirmarIn): Observable<void> {
    return this.http
      .post<void>(`${this.base}/recuperacion/confirmar`, datos)
      .pipe(
        tap(() => this.descartarSesion()),
        catchError((e: HttpErrorResponse) =>
          throwError(() => this.traducirRecuperacion(e)),
        ),
      );
  }

  // --- Traducción de errores ---------------------------------------------

  private traducirRegistro(error: HttpErrorResponse): ErrorRegistro {
    const detalle: string = error.error?.detail ?? '';

    if (error.status === 409) {
      return detalle.includes('documento')
        ? { tipo: 'documento-duplicado', mensaje: detalle }
        : { tipo: 'correo-duplicado', mensaje: detalle };
    }
    if (error.status === 422) {
      return { tipo: 'datos-invalidos', mensaje: 'Revise los datos del formulario.' };
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

  private traducirLogin(error: HttpErrorResponse): ErrorLogin {
    const detalle: string = error.error?.detail ?? '';

    if (error.status === 401) {
      return {
        tipo: 'credenciales',
        mensaje: detalle || 'El correo o la contraseña son incorrectos.',
      };
    }
    if (error.status === 403) {
      return {
        tipo: 'desactivada',
        mensaje: detalle || 'Su cuenta está desactivada. Contacte al administrador.',
      };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: detalle || 'No se pudo iniciar sesión.' };
  }

  private traducirRecuperacion(error: HttpErrorResponse): ErrorRecuperacion {
    const detalle: string = error.error?.detail ?? '';

    if (error.status === 400) {
      // Un solo mensaje para «no existe», «ya se usó» y «venció»: es lo que
      // responde el servidor, y distinguirlos diría si ese enlace existió.
      return {
        tipo: 'enlace-invalido',
        mensaje:
          detalle ||
          'El enlace no es válido, ya fue utilizado o venció. Solicite uno nuevo.',
      };
    }
    if (error.status === 403) {
      return {
        tipo: 'desactivada',
        mensaje: detalle || 'Su cuenta está desactivada. Contacte al administrador.',
      };
    }
    if (error.status === 422) {
      return { tipo: 'datos-invalidos', mensaje: 'Revise los datos del formulario.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return {
      tipo: 'sistema',
      mensaje: detalle || 'No se pudo completar la recuperación.',
    };
  }
}
