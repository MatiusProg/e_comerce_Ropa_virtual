import { Routes } from '@angular/router';

import { rolGuard, sesionGuard } from './core/guards/auth.guard';

/**
 * Mapa de rutas de la aplicación web.
 *
 * Sigue el diagrama de navegación de
 * `docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` §3.2. Las áreas se van
 * llenando a medida que avanzan los casos de uso; en el Ciclo 1 cada una es una
 * pantalla de bienvenida, suficiente para mostrar que la guarda por rol opera.
 *
 * Regla de navegación (§3.2): toda ruta distinta de inicio de sesión y registro
 * exige token vigente. Lo impone `sesionGuard`; el ámbito por rol, `rolGuard`.
 */
const inicio = () => import('./features/inicio/inicio').then((m) => m.Inicio);

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

  // --- Con sesión, una por rol ------------------------------------------
  {
    path: 'admin',
    canActivate: [sesionGuard, rolGuard('ADMINISTRADOR')],
    loadComponent: () =>
      import('./features/admin/admin-layout/admin-layout').then((m) => m.AdminLayout),
    children: [
      {
        path: '',
        pathMatch: 'full',
        title: 'Administración · FashionStore',
        loadComponent: () =>
          import('./shared/bienvenida/bienvenida').then((m) => m.Bienvenida),
      },
      {
        path: 'usuarios',
        title: 'Usuarios · FashionStore',
        loadComponent: () =>
          import('./features/admin/usuarios/usuarios').then((m) => m.Usuarios),
      },
      {
        path: 'sucursales',
        title: 'Sucursales · FashionStore',
        loadComponent: () =>
          import('./features/admin/sucursales/sucursales').then((m) => m.Sucursales),
      },
      {
        path: 'ciudades',
        title: 'Ciudades · FashionStore',
        loadComponent: () =>
          import('./features/admin/ciudades/ciudades').then((m) => m.Ciudades),
      },
      // CU-06 (empleados) entra aquí, entre ciudades y proveedores.
      {
        path: 'proveedores',
        title: 'Proveedores · FashionStore',
        loadComponent: () =>
          import('./features/admin/proveedores/proveedores').then((m) => m.Proveedores),
      },
    ],
  },
  {
    path: 'mi-cuenta',
    title: 'Mi cuenta · FashionStore',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: inicio,
  },
  {
    path: 'sucursal',
    title: 'Sucursal · FashionStore',
    canActivate: [sesionGuard, rolGuard('ENCARGADO')],
    loadComponent: inicio,
  },
  {
    path: 'caja',
    title: 'Caja · FashionStore',
    canActivate: [sesionGuard, rolGuard('CAJERO')],
    loadComponent: inicio,
  },
  {
    path: 'proveedor',
    title: 'Proveedor · FashionStore',
    canActivate: [sesionGuard, rolGuard('PROVEEDOR')],
    loadComponent: inicio,
  },

  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
