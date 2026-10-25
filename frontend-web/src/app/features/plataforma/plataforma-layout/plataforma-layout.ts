import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Cáscara del área del administrador de la plataforma (2do parcial).
 *
 * Está por encima de las empresas: no ve el catálogo ni las ventas de ninguna,
 * solo las empresas, sus planes y sus suscripciones. Comparte los estilos con
 * la cáscara de administración para que las dos áreas se vean de la misma
 * familia.
 */
@Component({
  selector: 'app-plataforma-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatButtonModule, MatIconModule, MatToolbarModule],
  template: `
    <mat-toolbar class="barra">
      <span class="logotipo vb-titulo">Violet Boutique</span>
      <span class="etiqueta-area">Plataforma</span>
      <span class="separador"></span>
      @if (usuario(); as u) {
        <span class="identidad">
          <span class="avatar">{{ iniciales() }}</span>
          <span class="datos">
            <span class="nombre">{{ u.nombres }} {{ u.apellidos }}</span>
            <span class="rol">Administrador de la plataforma</span>
          </span>
        </span>
        <button matIconButton type="button" (click)="salir()" aria-label="Cerrar sesión">
          <mat-icon>logout</mat-icon>
        </button>
      }
    </mat-toolbar>

    <nav class="navegacion" aria-label="Secciones de la plataforma">
      <a routerLink="/plataforma/empresas" routerLinkActive="activo">
        <mat-icon>domain</mat-icon>
        Empresas
      </a>
      <a routerLink="/plataforma/ciudades" routerLinkActive="activo">
        <mat-icon>location_city</mat-icon>
        Ciudades
      </a>
    </nav>

    <main class="contenido">
      <router-outlet />
    </main>
  `,
  styleUrl: '../../admin/admin-layout/admin-layout.scss',
})
export class PlataformaLayout {
  private readonly auth = inject(AuthService);

  protected readonly usuario = this.auth.usuario;
  protected readonly iniciales = computed(() => {
    const u = this.usuario();
    return u ? `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase() : '';
  });

  protected salir(): void {
    this.auth.cerrarSesion();
  }
}
