import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Cáscara del área de administración.
 *
 * La navegación sigue el árbol del Administrador en el diagrama de navegación
 * §3.2. Las entradas que todavía no tienen caso de uso implementado aparecen
 * deshabilitadas: se habilitan con CU-06 a CU-09. Mostrarlas desde ahora deja
 * ver el mapa completo del área sin fingir que ya funcionan.
 */
@Component({
  selector: 'app-admin-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatIconModule,
    MatToolbarModule,
  ],
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
})
export class AdminLayout {
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
