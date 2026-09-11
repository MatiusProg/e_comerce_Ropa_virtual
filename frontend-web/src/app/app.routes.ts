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
    title: 'Iniciar sesión · Violet Boutique',
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'registro',
    title: 'Crear cuenta · Violet Boutique',
    loadComponent: () => import('./features/auth/registro/registro').then((m) => m.Registro),
  },

  // --- Ciclo 2 · Karen · La vitrina, también sin sesión ------------------
  // CU-17 y CU-18 son públicos a propósito: el flujo principal no tiene
  // precondición de sesión y el RF07 pide que el cliente consulte el catálogo
  // desde la web y el móvil. Exigir token obligaría a registrarse para mirar
  // una prenda. Lo que se ofrece ya está acotado en el servidor —solo producto
  // activo con variantes activas— y los esquemas públicos no exponen proveedor
  // ni precio base.
  {
    path: 'tienda',
    title: 'Catálogo · Violet Boutique',
    loadComponent: () =>
      import('./features/tienda/catalogo/catalogo').then((m) => m.Catalogo),
  },
  {
    path: 'tienda/producto/:id',
    title: 'Prenda · Violet Boutique',
    loadComponent: () => import('./features/tienda/ficha/ficha').then((m) => m.Ficha),
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
        title: 'Administración · Violet Boutique',
        loadComponent: () =>
          import('./shared/bienvenida/bienvenida').then((m) => m.Bienvenida),
      },
      {
        path: 'usuarios',
        title: 'Usuarios · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/usuarios/usuarios').then((m) => m.Usuarios),
      },
      {
        path: 'sucursales',
        title: 'Sucursales · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/sucursales/sucursales').then((m) => m.Sucursales),
      },
      {
        path: 'ciudades',
        title: 'Ciudades · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/ciudades/ciudades').then((m) => m.Ciudades),
      },
      {
        path: 'empleados',
        title: 'Empleados · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/empleados/empleados').then((m) => m.Empleados),
      },
      {
        path: 'proveedores',
        title: 'Proveedores · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/proveedores/proveedores').then((m) => m.Proveedores),
      },
      {
        path: 'maestros',
        title: 'Maestros del catálogo · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/maestros/maestros').then((m) => m.Maestros),
      },
      {
        path: 'temporadas',
        title: 'Temporadas · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/temporadas/temporadas').then((m) => m.Temporadas),
      },
      // --- Ciclo 2 · Karen -------------------------------------------------
      // Se agrega al final del bloque y sin reordenar lo anterior, que es el
      // protocolo de archivos compartidos del ciclo (§5 del acuerdo).
      {
        path: 'productos',
        title: 'Productos · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/productos/productos').then((m) => m.Productos),
      },
      {
        // CU-14. Ruta aparte de `inventario`, que es de CU-13 y CU-15: aquélla
        // sirve para operar sobre una tienda y ésta para mirar la red entera.
        path: 'consolidado',
        title: 'Inventario consolidado · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/consolidado/consolidado').then((m) => m.Consolidado),
      },
      // --- Ciclo 2 · P4 Inventario (CU-13, CU-15) ---
      {
        path: 'inventario',
        title: 'Inventario · Violet Boutique',
        loadComponent: () =>
          import('./features/admin/inventario/inventario').then((m) => m.Inventario),
      },
    ],
  },
  {
    path: 'mi-cuenta',
    title: 'Mi perfil · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CLIENTE')],
    loadComponent: () =>
      import('./features/cliente/perfil/perfil').then((m) => m.Perfil),
  },
  // --- Ciclo 2 · P4 para el Encargado (CU-13 y CU-16) ---
  //
  // Van ANTES de 'sucursal' a propósito: esa ruta no declara hijos, así que si
  // quedara primero consumiría el prefijo y estas no se resolverían nunca.
  //
  // `disponibilidad` es CU-16 y tiene pantalla propia: está organizada
  // alrededor del saldo de un local —alertas arriba, listado abajo—, mientras
  // que la del Administrador lo está alrededor del movimiento. Comparten los
  // diálogos y el servicio, que es donde vive lo que de verdad se repite.
  //
  // `inventario` reusa la pantalla del Administrador para que el Encargado
  // registre sus ingresos (CU-13) y lea su historial. El alcance no lo decide
  // la ruta sino el servidor: el ámbito viaja en el token.
  {
    path: 'sucursal/disponibilidad',
    title: 'Disponibilidad · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('ENCARGADO')],
    loadComponent: () =>
      import('./features/sucursal/disponibilidad/disponibilidad').then(
        (m) => m.Disponibilidad,
      ),
  },
  {
    path: 'sucursal/inventario',
    title: 'Inventario de la sucursal · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('ENCARGADO')],
    loadComponent: () =>
      import('./features/admin/inventario/inventario').then((m) => m.Inventario),
  },
  {
    path: 'sucursal',
    title: 'Sucursal · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('ENCARGADO')],
    loadComponent: inicio,
  },
  {
    path: 'caja',
    title: 'Caja · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('CAJERO')],
    loadComponent: inicio,
  },
  {
    path: 'proveedor',
    title: 'Proveedor · Violet Boutique',
    canActivate: [sesionGuard, rolGuard('PROVEEDOR')],
    loadComponent: inicio,
  },

  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
