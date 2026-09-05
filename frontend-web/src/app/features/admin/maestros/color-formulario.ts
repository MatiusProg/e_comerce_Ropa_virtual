import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { MaestrosService, type ErrorMaestros } from '../../../core/services/maestros.service';
import { HEXADECIMAL_PATRON, type Color } from '../../../core/models/maestros.models';

export interface DatosColor {
  /** null = alta; con valor = edición. */
  color: Color | null;
}

/**
 * Alta y edición de un color — flujo alternativo 1b del CU-08.
 *
 * El valor se elige con el selector nativo del navegador y también se puede
 * escribir a mano: quien tiene el código de la marca lo pega, y quien no, lo
 * busca visualmente. Los dos campos están atados al mismo valor.
 */
@Component({
  selector: 'app-color-formulario',
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

    <h2 mat-dialog-title class="vb-titulo">
      {{ esEdicion ? 'Editar color' : 'Nuevo color' }}
    </h2>

    <mat-dialog-content>
      @if (error(); as e) {
        <div class="aviso" role="alert">
          <mat-icon>error_outline</mat-icon>
          <span>{{ e }}</span>
        </div>
      }

      <form [formGroup]="formulario" (ngSubmit)="guardar()" novalidate id="formulario-color">
        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Nombre</mat-label>
          <input matInput formControlName="nombre" />
          @if (formulario.controls.nombre.hasError('required')) {
            <mat-error>Ingresá el nombre.</mat-error>
          } @else if (formulario.controls.nombre.hasError('duplicado')) {
            <!-- Excepción E1. -->
            <mat-error>Ya existe un color con ese nombre.</mat-error>
          }
        </mat-form-field>

        <div class="fila-color">
          <label class="selector">
            <span class="etiqueta">Muestra</span>
            <input
              type="color"
              [value]="formulario.controls.hexadecimal.value"
              (input)="elegirDelSelector($any($event.target).value)"
              aria-label="Elegir color"
            />
          </label>

          <mat-form-field appearance="outline" class="campo-hex">
            <mat-label>Valor hexadecimal</mat-label>
            <input matInput formControlName="hexadecimal" maxlength="7" />
            <mat-hint>Formato #RRGGBB, por ejemplo #C9A227.</mat-hint>
            @if (formulario.controls.hexadecimal.hasError('required')) {
              <mat-error>Indicá el color.</mat-error>
            } @else if (formulario.controls.hexadecimal.hasError('pattern')) {
              <mat-error>Tiene que ser #RRGGBB, con seis dígitos.</mat-error>
            }
          </mat-form-field>
        </div>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(false)">Cancelar</button>
      <button
        matButton="filled"
        type="submit"
        form="formulario-color"
        class="vb-boton-marca"
        [disabled]="guardando()"
      >
        {{ esEdicion ? 'Guardar cambios' : 'Crear color' }}
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
    form {
      display: flex;
      flex-direction: column;
      gap: 0.1rem;
    }
    .ancho-completo {
      width: 100%;
    }
    .fila-color {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
    }
    .selector {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      flex: none;
      padding-top: 0.35rem;
    }
    .selector .etiqueta {
      font-size: 0.78rem;
      color: var(--mat-sys-on-surface-variant);
    }
    .selector input[type='color'] {
      width: 3.5rem;
      height: 3.5rem;
      padding: 0;
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: var(--vb-radio-chico);
      background: none;
      cursor: pointer;
    }
    .campo-hex {
      flex: 1 1 auto;
      min-width: 0;
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
    }
    .aviso mat-icon {
      flex: none;
    }
  `,
})
export class ColorFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(MaestrosService);

  protected readonly ref = inject(MatDialogRef<ColorFormulario, boolean>);
  protected readonly datos = inject<DatosColor>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.datos.color !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    nombre: [
      this.datos.color?.nombre ?? '',
      [Validators.required, Validators.maxLength(40)],
    ],
    hexadecimal: [
      this.datos.color?.hexadecimal ?? '#8E4A67',
      [Validators.required, Validators.pattern(HEXADECIMAL_PATRON)],
    ],
  });

  /**
   * El selector nativo devuelve el valor en minúsculas.
   *
   * Se guarda en mayúsculas para que coincida con lo que devuelve el servidor
   * y el campo de texto no parpadee entre dos formas del mismo color.
   */
  protected elegirDelSelector(valor: string): void {
    this.formulario.controls.hexadecimal.setValue(valor.toUpperCase());
    this.formulario.controls.hexadecimal.markAsDirty();
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    const alTerminar = {
      next: () => {
        this.guardando.set(false);
        this.ref.close(true);
      },
      error: (e: ErrorMaestros) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        if (e.tipo === 'duplicado') {
          this.formulario.controls.nombre.setErrors({ duplicado: true });
        }
      },
    };

    const datos = {
      nombre: v.nombre.trim(),
      hexadecimal: v.hexadecimal.toUpperCase(),
    };

    if (this.esEdicion) {
      this.api.editarColor(this.datos.color!.id, datos).subscribe(alTerminar);
    } else {
      this.api.crearColor({ ...datos, activo: true }).subscribe(alTerminar);
    }
  }
}
