import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Cáscara del área de Caja.
 *
 * **Es la cuarta vez que este hueco aparece, y la última que faltaba.**
 * `/proveedor` caía en la bienvenida genérica hasta CU-38, `/sucursal` hasta el
 * PR #29, y `/caja` llevaba desde el Ciclo 1 igual: un Cajero iniciaba sesión y
 * aterrizaba en una pantalla que no decía nada de su trabajo.
 *
 * La lección ya costó tres veces: **una pantalla montada no está entregada si
 * no hay cómo llegar a ella.**
 *
 * Es el espejo de `AdminLayout`, `SucursalLayout` y `ProveedorLayout` a
 * propósito: quien aprendió a moverse en un área se mueve igual en la otra.
 */
@Component({
  selector: 'app-caja-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatIconModule,
    MatToolbarModule,
  ],
  templateUrl: './caja-layout.html',
  styleUrl: './caja-layout.scss',
})
export class CajaLayout {
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
