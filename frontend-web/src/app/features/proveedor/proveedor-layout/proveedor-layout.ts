import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Cáscara del área del Proveedor.
 *
 * Existe por la misma razón que `SucursalLayout`, y la lección ya costó una
 * vez: **una pantalla montada no está entregada si no hay cómo llegar a ella.**
 * Hasta CU-38, `/proveedor` caía en la pantalla genérica de bienvenida —la
 * misma que usa Caja—, sin navegación y sin nada propio. El Proveedor era un
 * actor principal que no iniciaba ningún caso de uso.
 *
 * Es el espejo de `AdminLayout` y `SucursalLayout` a propósito: quien aprendió
 * a moverse en un área se mueve igual en la otra.
 *
 * *Mi ficha* apunta a CU-07, que ya existía: el Proveedor podía consultar sus
 * propios datos y tampoco tenía cómo llegar.
 */
@Component({
  selector: 'app-proveedor-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatIconModule,
    MatToolbarModule,
  ],
  templateUrl: './proveedor-layout.html',
  styleUrl: './proveedor-layout.scss',
})
export class ProveedorLayout {
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
