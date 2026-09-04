import { Routes } from '@angular/router';

/**
 * Mapa de rutas de la aplicación web.
 *
 * Sigue el diagrama de navegación de
 * `docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` §3.2. Las rutas se van
 * agregando por área a medida que avanzan los casos de uso; las áreas de
 * administración, sucursal, caja, tienda y reportes llegan después.
 *
 * Regla de navegación (§3.2): toda ruta distinta de inicio de sesión y
 * registro exige token vigente. La guarda que lo impone se agrega con CU-02.
 */
export const routes: Routes = [
  // --- Público (sin sesión) ---------------------------------------------
  {
    path: 'login',
    title: 'Iniciar sesión · FashionStore',
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'registro',
    title: 'Crear cuenta · FashionStore',
    loadComponent: () => import('./features/auth/registro/registro').then((m) => m.Registro),
  },

  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
