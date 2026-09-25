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

/**
 * La raíz del sitio: la vitrina para el visitante, el área propia para quien
 * ya tiene sesión.
 *
 * Hasta el 25/09 la raíz mandaba siempre al login, y el catálogo —público a
 * propósito, RF07— no tenía ninguna puerta: había que escribir `/tienda` a
 * mano. Una tienda que recibe con un formulario de contraseña es al revés de
 * como se comporta una tienda. Quien trabaja en el sistema no pierde nada:
 * con la sesión abierta sigue cayendo en su área, como antes.
 */
export const inicioGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const aLaTienda = () => router.createUrlTree(['/tienda']);
  const aSuArea = () => router.createUrlTree([auth.inicioDelRol()]);

  if (auth.autenticado()) {
    return aSuArea();
  }

  if (!auth.token) {
    return aLaTienda();
  }

  return auth.restaurarSesion().pipe(map((usuario) => (usuario ? aSuArea() : aLaTienda())));
};

/**
 * A dónde ir después de iniciar sesión.
 *
 * Flujo alternativo 6a de CU-02 y 8a de CU-01: se vuelve a donde se estaba.
 * Con dos excepciones:
 *
 * - **La vitrina, solo para el Cliente.** El botón «Ingresar» del catálogo es
 *   la puerta de todos: por ahí entra también el cajero que abrió el sitio
 *   por la raíz. Devolverlo a la tienda lo dejaría en una pantalla que no es
 *   la suya; va a su área.
 * - **Solo rutas internas.** Un `destino` que no empieza con una sola barra
 *   —`https://…`, `//otro-sitio`— se descarta: el parámetro viaja en la URL y
 *   cualquiera puede escribirlo.
 */
export function destinoTrasLogin(destino: string | null, rol: Rol, inicioDelRol: string): string {
  if (!destino || !destino.startsWith('/') || destino.startsWith('//')) {
    return inicioDelRol;
  }
  if (destino.startsWith('/login') || destino.startsWith('/registro')) {
    return inicioDelRol;
  }
  if (destino.startsWith('/tienda') && rol !== 'CLIENTE') {
    return inicioDelRol;
  }
  return destino;
}
