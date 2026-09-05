import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface DatosConfirmacion {
  titulo: string;
  mensaje: string;
  confirmar: string;
  /** Tiñe la acción de rojo cuando es destructiva o difícil de revertir. */
  peligrosa?: boolean;
}

/**
 * Diálogo de confirmación reutilizable.
 *
 * Toda acción difícil de revertir pasa por acá: desactivar una cuenta y
 * eliminarla. El caso de uso lo pide explícitamente en el flujo 3b.
 */
@Component({
  selector: 'app-confirmacion',
  imports: [MatButtonModule, MatDialogModule, MatIconModule],
  template: `
    <h2 mat-dialog-title class="vb-titulo">
      <mat-icon [class.peligro]="datos.peligrosa">
        {{ datos.peligrosa ? 'warning_amber' : 'help_outline' }}
      </mat-icon>
      {{ datos.titulo }}
    </h2>

    <mat-dialog-content>
      <p>{{ datos.mensaje }}</p>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(false)">Cancelar</button>
      <button
        matButton="filled"
        type="button"
        [class.boton-peligro]="datos.peligrosa"
        [class.vb-boton-marca]="!datos.peligrosa"
        (click)="ref.close(true)"
      >
        {{ datos.confirmar }}
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    h2 {
      display: flex;
      align-items: center;
      gap: 0.55rem;
      color: var(--vb-malva-oscuro);
    }
    mat-icon.peligro {
      color: var(--mat-sys-error);
    }
    p {
      margin: 0;
      line-height: 1.6;
      color: var(--mat-sys-on-surface-variant);
    }
    .boton-peligro {
      background: var(--mat-sys-error);
      color: var(--mat-sys-on-error);
    }
  `,
})
export class Confirmacion {
  protected readonly ref = inject(MatDialogRef<Confirmacion, boolean>);
  protected readonly datos = inject<DatosConfirmacion>(MAT_DIALOG_DATA);
}
