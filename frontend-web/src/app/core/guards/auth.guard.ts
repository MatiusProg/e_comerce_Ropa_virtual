import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs/operators';

import { Rol } from '../models/auth.models';
import { AuthService } from '../services/auth.service';

/**
 * Exige sesión vigente.
 *
 * Regla de navegación de §3.2: toda ruta distinta de inicio de sesión y
 * registro exige token vigente; si falta o expiró, se redirige a inicio de
 * sesión **conservando la ruta destino** para volver a ella después
 * (flujo alternativo 6a de CU-02).
 *
 * Si todavía no se resolvió quién es el usuario —el caso de recargar la página
 * con un token guardado— se le pregunta al servidor antes de decidir. Es lo que
 * evita el parpadeo al login en cada F5.
 */
export const sesionGuard: CanActivateFn = (_ruta, estado) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const alLogin = () =>
    router.createUrlTree(['/login'], { queryParams: { destino: estado.url } });

  if (auth.autenticado()) {
    return true;
  }

  if (!auth.token) {
    return alLogin();
  }

  return auth.restaurarSesion().pipe(map((usuario) => (usuario ? true : alLogin())));
};

/**
 * Exige que el usuario tenga uno de los roles indicados.
 *
 * Es la contracara en la web de `requiere_roles(...)` del backend. Ojo: esto
 * es comodidad de navegación, NO seguridad — quien controla de verdad es el
 * backend. Acá solo se evita mostrar una pantalla que igual no cargaría datos.
 */
export function rolGuard(...roles: Rol[]): CanActivateFn {
  return (_ruta, estado) => {
    const auth = inject(AuthService);
    const router = inject(Router);

    const permitir = () => {
      const rol = auth.rol();
      if (rol && roles.includes(rol)) {
        return true;
      }
      // Tiene sesión pero no el rol: se lo manda a su propia área, no al
      // login, que sería confuso —ya está autenticado—.
      return router.createUrlTree([auth.inicioDelRol()]);
    };

    if (auth.autenticado()) {
      return permitir();
    }

    if (!auth.token) {
      return router.createUrlTree(['/login'], { queryParams: { destino: estado.url } });
    }

    return auth.restaurarSesion().pipe(
      map((usuario) =>
        usuario
          ? permitir()
          : router.createUrlTree(['/login'], { queryParams: { destino: estado.url } }),
      ),
    );
  };
}
