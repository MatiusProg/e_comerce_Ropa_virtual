import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Cáscara del área del Encargado de Sucursal.
 *
 * Existe por una razón concreta: sus tres pantallas —CU-16 disponibilidad,
 * CU-24 reservas del local y el inventario de la sucursal (CU-13/CU-15)— ya
 * estaban terminadas y montadas en sus rutas, pero **no había cómo llegar a
 * ellas**. `/sucursal` caía en la pantalla genérica de bienvenida, la misma que
 * usan Caja y Proveedor, que no tiene navegación y seguía diciendo que «sus
 * funciones propias llegan con el Ciclo 2». Llegaron; faltaba la puerta.
 *
 * Es el espejo de `AdminLayout` y comparte su estructura a propósito: quien
 * aprendió a moverse en un área se mueve igual en la otra.
 *
 * **El alcance no lo decide esta barra**, lo decide el servidor con el ámbito
 * del token: el Encargado ve su sucursal y el Administrador la red entera
 * aunque entren a la misma pantalla. Por eso `sucursal/inventario` reusa el
 * componente del Administrador en vez de duplicarlo.
 */
@Component({
  selector: 'app-sucursal-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatIconModule,
    MatToolbarModule,
  ],
  templateUrl: './sucursal-layout.html',
  styleUrl: './sucursal-layout.scss',
})
export class SucursalLayout {
  private readonly auth = inject(AuthService);

  protected readonly usuario = this.auth.usuario;

  protected readonly iniciales = computed(() => {
    const u = this.usuario();
    if (!u) return '';
    return `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase();
  });

  protected salir(): void {
    this.auth.cerrarSesion();
  }
}
