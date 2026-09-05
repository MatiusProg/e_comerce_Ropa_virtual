import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { MaestrosService, type ErrorMaestros } from '../../../core/services/maestros.service';
import type { Talla } from '../../../core/models/maestros.models';

export interface DatosTalla {
  /** null = alta; con valor = edición. */
  talla: Talla | null;
  /** Tipos ya usados, para ofrecerlos y no reescribirlos. */
  tipos: string[];
}

/**
 * Alta y edición de una talla — flujo alternativo 1a del CU-08.
 *
 * El tipo de prenda se escribe con autocompletado sobre los ya usados: es texto
 * libre, y sin ofrecer los existentes la misma familia termina partida en
 * «SUPERIOR» y «PARTE SUPERIOR», con lo que las tallas dejan de agruparse.
 *
 * Plantilla en línea, como el diálogo de confirmación: son cuatro campos y un
 * archivo aparte solo agregaría dónde buscarlos.
 */
@Component({
  selector: 'app-talla-formulario',
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
      {{ esEdicion ? 'Editar talla' : 'Nueva talla' }}
    </h2>

    <mat-dialog-content>
      @if (error(); as e) {
        <div class="aviso" role="alert">
          <mat-icon>error_outline</mat-icon>
          <span>{{ e }}</span>
        </div>
      }

      <form [formGroup]="formulario" (ngSubmit)="guardar()" novalidate id="formulario-talla">
        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Tipo de prenda</mat-label>
          <input matInput formControlName="tipo_prenda" list="tipos-de-prenda" />
          <datalist id="tipos-de-prenda">
            @for (t of datos.tipos; track t) {
              <option [value]="t"></option>
            }
          </datalist>
          <mat-hint>Agrupa las tallas: SUPERIOR, INFERIOR, CALZADO…</mat-hint>
          @if (formulario.controls.tipo_prenda.hasError('required')) {
            <mat-error>Indicá el tipo de prenda.</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Código</mat-label>
          <input matInput formControlName="codigo" />
          <mat-hint>XS, S, M, L, XL, 38, 40…</mat-hint>
          @if (formulario.controls.codigo.hasError('required')) {
            <mat-error>Ingresá el código.</mat-error>
          } @else if (formulario.controls.codigo.hasError('duplicado')) {
            <!-- Excepción E1. -->
            <mat-error>Ese código ya existe para ese tipo de prenda.</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Orden</mat-label>
          <input matInput type="number" formControlName="orden" min="0" />
          <mat-hint>
            Sin orden, XL aparece antes que S: la lista sale alfabética.
          </mat-hint>
          @if (formulario.controls.orden.hasError('min')) {
            <mat-error>No puede ser negativo.</mat-error>
          }
        </mat-form-field>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(false)">Cancelar</button>
      <button
        matButton="filled"
        type="submit"
        form="formulario-talla"
        class="vb-boton-marca"
        [disabled]="guardando()"
      >
        {{ esEdicion ? 'Guardar cambios' : 'Crear talla' }}
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
export class TallaFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(MaestrosService);

  protected readonly ref = inject(MatDialogRef<TallaFormulario, boolean>);
  protected readonly datos = inject<DatosTalla>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.datos.talla !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    tipo_prenda: [
      this.datos.talla?.tipo_prenda ?? '',
      [Validators.required, Validators.maxLength(30)],
    ],
    codigo: [
      this.datos.talla?.codigo ?? '',
      [Validators.required, Validators.maxLength(10)],
    ],
    orden: [this.datos.talla?.orden ?? 0, [Validators.required, Validators.min(0)]],
  });

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
          this.formulario.controls.codigo.setErrors({ duplicado: true });
        }
      },
    };

    // La normalización a mayúsculas la hace el servidor; acá solo se recorta.
    const datos = {
      tipo_prenda: v.tipo_prenda.trim(),
      codigo: v.codigo.trim(),
      orden: v.orden,
    };

    if (this.esEdicion) {
      this.api.editarTalla(this.datos.talla!.id, datos).subscribe(alTerminar);
    } else {
      this.api.crearTalla({ ...datos, activa: true }).subscribe(alTerminar);
    }
  }
}
