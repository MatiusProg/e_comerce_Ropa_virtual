import { Component, computed, effect, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from './core/services/auth.service';
import { MarcaService } from './core/services/marca.service';

@Component({
  imports: [RouterOutlet],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  private readonly auth = inject(AuthService);
  private readonly marca = inject(MarcaService);

  /** La empresa de la sesión: cambia al entrar o salir, y con ella la tienda. */
  private readonly empresaDeLaSesion = computed(() => this.auth.usuario()?.empresa?.id ?? null);

  constructor() {
    // 2do parcial · CU-12 (1.11): la marca de la tienda que se mira. Se vuelve
    // a pedir cuando cambia la empresa de la sesión.
    effect(() => {
      this.empresaDeLaSesion();
      this.marca.cargar();
    });
  }
}
