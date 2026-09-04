import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

/**
 * CU-02 · Iniciar sesión — «boundary» FormularioLogin.
 *
 * Marcador de posición: existe para que CU-01 tenga a dónde derivar en el
 * paso 8 y en la excepción E1. El formulario, la emisión del token y la guarda
 * por rol llegan con CU-02.
 */
@Component({
  selector: 'app-login',
  imports: [RouterLink, MatButtonModule, MatCardModule],
  template: `
    <div class="pantalla">
      <mat-card class="tarjeta" appearance="outlined">
        <mat-card-header>
          <mat-card-title>Iniciar sesión</mat-card-title>
          <mat-card-subtitle>Pendiente — CU-02</mat-card-subtitle>
        </mat-card-header>
        <mat-card-actions>
          <a matButton routerLink="/registro">Crear una cuenta</a>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: `
    .pantalla {
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100dvh;
      padding: 2rem 1rem;
      box-sizing: border-box;
      background-color: var(--mat-sys-surface-container-low);
    }
    .tarjeta {
      width: 100%;
      max-width: 420px;
      padding-bottom: 0.5rem;
    }
  `,
})
export class Login {}
