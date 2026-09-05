import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  ProveedoresService,
  type ErrorProveedores,
} from '../../../core/services/proveedores.service';
import {
  CONTRASENA_LONGITUD_MINIMA,
  CONTRASENA_PATRON,
} from '../../../core/models/auth.models';
import type { Proveedor } from '../../../core/models/proveedores.models';

/**
 * Habilitar acceso al Proveedor (flujo alternativo 3c de CU-07).
 *
 * Crea un usuario con rol Proveedor vinculado a la ficha, con alcance limitado
 * a sus propios productos. El correo de acceso se pide aparte del de contacto:
 * el de contacto puede ser un buzón compartido, y este identifica a la persona
 * que inicia sesión.
 *
 * Plantilla en línea, como el formulario de ciudad: son cuatro campos y
 * separarla en tres archivos sería más ceremonia que ayuda.
 */
@Component({
  selector: 'app-acceso-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  template: `
    @if (guardando()) {
      <mat-progress-bar mode="indeterminate" />
    }

    <h2 mat-dialog-title class="vb-titulo">Habilitar acceso</h2>

    <mat-dialog-content>
      <p class="contexto">
        Se creará una cuenta con rol <strong>Proveedor</strong> vinculada a
        <strong>{{ proveedor.razon_social }}</strong
        >. Solo podrá ver sus propios productos.
      </p>

      @if (error(); as e) {
        <div class="aviso" role="alert">
          <mat-icon>error_outline</mat-icon>
          <span>{{ e }}</span>
        </div>
      }

      <form [formGroup]="formulario" (ngSubmit)="guardar()" novalidate id="formulario-acceso">
        <div class="fila">
          <mat-form-field appearance="outline">
            <mat-label>Nombres</mat-label>
            <input matInput formControlName="nombres" />
            @if (formulario.controls.nombres.hasError('required')) {
              <mat-error>Ingrese los nombres.</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Apellidos</mat-label>
            <input matInput formControlName="apellidos" />
            @if (formulario.controls.apellidos.hasError('required')) {
              <mat-error>Ingrese los apellidos.</mat-error>
            }
          </mat-form-field>
        </div>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Correo de acceso</mat-label>
          <input matInput type="email" formControlName="correo" autocomplete="off" />
          <mat-hint>Con este correo iniciará sesión.</mat-hint>
          @if (formulario.controls.correo.hasError('required')) {
            <mat-error>Ingrese el correo de acceso.</mat-error>
          } @else if (formulario.controls.correo.hasError('email')) {
            <mat-error>El correo no tiene un formato válido.</mat-error>
          } @else if (formulario.controls.correo.hasError('duplicado')) {
            <mat-error>Ese correo ya tiene una cuenta.</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Contraseña inicial</mat-label>
          <input
            matInput
            [type]="verContrasena() ? 'text' : 'password'"
            formControlName="contrasena"
            autocomplete="new-password"
          />
          <button
            matIconButton
            type="button"
            matSuffix
            (click)="verContrasena.set(!verContrasena())"
            [attr.aria-label]="verContrasena() ? 'Ocultar contraseña' : 'Mostrar contraseña'"
          >
            <mat-icon>{{ verContrasena() ? 'visibility_off' : 'visibility' }}</mat-icon>
          </button>
          <mat-hint>
            Mínimo {{ longitudMinima }} caracteres, con al menos una letra y un número.
          </mat-hint>
          @if (formulario.controls.contrasena.hasError('required')) {
            <mat-error>Ingrese una contraseña inicial.</mat-error>
          } @else if (formulario.controls.contrasena.hasError('minlength')) {
            <mat-error>Debe tener al menos {{ longitudMinima }} caracteres.</mat-error>
          } @else if (formulario.controls.contrasena.hasError('pattern')) {
            <mat-error>Debe incluir al menos una letra y un número.</mat-error>
          }
        </mat-form-field>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(false)">Cancelar</button>
      <button
        matButton="filled"
        type="submit"
        form="formulario-acceso"
        class="vb-boton-marca"
        [disabled]="guardando()"
      >
        Habilitar acceso
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    :host {
      display: block;
    }
    h2 {
      color: var(--vb-malva-oscuro);
      margin-bottom: 0.5rem;
    }
    mat-dialog-content {
      padding-top: 1rem;
    }
    .contexto {
      margin: 0 0 1rem;
      line-height: 1.55;
      color: var(--mat-sys-on-surface-variant);
    }
    form {
      display: flex;
      flex-direction: column;
      gap: 0.1rem;
    }
    .fila {
      display: flex;
      gap: 1rem;

      mat-form-field {
        flex: 1 1 0;
        min-width: 0;
      }
    }
    .ancho-completo {
      width: 100%;
    }
    .aviso {
      display: flex;
      align-items: flex-start;
      gap: 0.55rem;
      padding: 0.8rem 1rem;
      border-radius: var(--vb-radio-chico);
      margin-bottom: 1rem;
      font-size: 0.92rem;
      line-height: 1.45;
      background: var(--mat-sys-error-container);
      color: var(--mat-sys-on-error-container);

      mat-icon {
        flex: none;
      }
    }
    @media (max-width: 560px) {
      .fila {
        flex-direction: column;
        gap: 0;
      }
    }
  `,
})
export class AccesoFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ProveedoresService);

  protected readonly ref = inject(MatDialogRef<AccesoFormulario, boolean>);
  protected readonly proveedor = inject<Proveedor>(MAT_DIALOG_DATA);

  protected readonly longitudMinima = CONTRASENA_LONGITUD_MINIMA;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly verContrasena = signal(false);

  protected readonly formulario = this.fb.nonNullable.group({
    nombres: ['', [Validators.required, Validators.maxLength(80)]],
    apellidos: ['', [Validators.required, Validators.maxLength(80)]],
    // Se propone el correo de contacto, que suele ser el mismo; el
    // Administrador puede cambiarlo.
    correo: [
      this.proveedor.correo ?? '',
      [Validators.required, Validators.email, Validators.maxLength(120)],
    ],
    contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(CONTRASENA_LONGITUD_MINIMA),
        Validators.pattern(CONTRASENA_PATRON),
      ],
    ],
  });

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    this.api
      .habilitarAcceso(this.proveedor.id, {
        nombres: v.nombres.trim(),
        apellidos: v.apellidos.trim(),
        correo: v.correo.trim().toLowerCase(),
        contrasena: v.contrasena,
      })
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.ref.close(true);
        },
        error: (e: ErrorProveedores) => {
          this.guardando.set(false);
          this.error.set(e.mensaje);
          if (e.tipo === 'correo-duplicado') {
            this.formulario.controls.correo.setErrors({ duplicado: true });
          }
        },
      });
  }
}
