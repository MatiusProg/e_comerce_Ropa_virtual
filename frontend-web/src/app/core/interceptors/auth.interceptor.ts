import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthService } from '../services/auth.service';

/** Endpoints que no llevan token: son justamente los que sirven para obtenerlo. */
const PUBLICOS = ['/auth/login', '/auth/registro'];

/**
 * Adjunta `Authorization: Bearer <token>` a cada petición a la API y reacciona
 * al 401.
 *
 * El 401 se trata acá y no en cada componente porque puede llegar en cualquier
 * momento: el backend revoca la sesión al cerrarla o al desactivar la cuenta, y
 * a partir de ahí TODA petición falla. Sin este manejo, la aplicación quedaría
 * mostrando una pantalla que ya no puede cargar nada.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const esPublico = PUBLICOS.some((ruta) => req.url.includes(ruta));
  const token = auth.token;

  const peticion =
    token && !esPublico
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

  return next(peticion).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !esPublico) {
        auth.descartarSesion();
        // Se conserva la ruta destino para volver a ella tras autenticarse
        // (flujo alternativo 6a de CU-02).
        router.navigate(['/login'], {
          queryParams: { destino: router.url },
        });
      }
      return throwError(() => error);
    }),
  );
};
