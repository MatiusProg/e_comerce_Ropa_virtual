import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  OrganizacionService,
  type ErrorOrganizacion,
} from '../../../core/services/organizacion.service';
import type { Ciudad } from '../../../core/models/organizacion.models';

/** null = alta; con valor = edición. */
export type DatosCiudad = Ciudad | null;

/**
 * Alta y edición de una ciudad (flujo alternativo 3a de CU-05).
 *
 * Son dos campos, nombre y departamento, así que la plantilla va en línea:
 * separarla en tres archivos para esto sería más ceremonia que ayuda. El
 * formulario de sucursal, que tiene ocho campos, sí los usa.
 */
@Component({
  selector: 'app-ciudad-formulario',
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
      {{ esEdicion ? 'Editar ciudad' : 'Nueva ciudad' }}
    </h2>

    <mat-dialog-content>
      @if (error(); as e) {
        <div class="aviso" role="alert">
          <mat-icon>error_outline</mat-icon>
          <span>{{ e }}</span>
        </div>
      }

      <form [formGroup]="formulario" (ngSubmit)="guardar()" novalidate id="formulario-ciudad">
        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Nombre</mat-label>
          <input matInput formControlName="nombre" />
          @if (formulario.controls.nombre.hasError('required')) {
            <mat-error>Ingrese el nombre de la ciudad.</mat-error>
          } @else if (formulario.controls.nombre.hasError('duplicado')) {
            <mat-error>Ya existe una ciudad con ese nombre.</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Departamento</mat-label>
          <input matInput formControlName="departamento" />
          @if (formulario.controls.departamento.hasError('required')) {
            <mat-error>Ingrese el departamento.</mat-error>
          }
        </mat-form-field>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(false)">Cancelar</button>
      <button
        matButton="filled"
        type="submit"
        form="formulario-ciudad"
        class="vb-boton-marca"
        [disabled]="guardando()"
      >
        {{ esEdicion ? 'Guardar cambios' : 'Registrar ciudad' }}
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

      mat-icon {
        flex: none;
      }
    }
  `,
})
export class CiudadFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(OrganizacionService);

  protected readonly ref = inject(MatDialogRef<CiudadFormulario, boolean>);
  protected readonly ciudad = inject<DatosCiudad>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.ciudad !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    nombre: [this.ciudad?.nombre ?? '', [Validators.required, Validators.maxLength(60)]],
    departamento: [
      this.ciudad?.departamento ?? '',
      [Validators.required, Validators.maxLength(60)],
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

    const datos = {
      nombre: v.nombre.trim(),
      departamento: v.departamento.trim(),
    };

    const alTerminar = {
      next: () => {
        this.guardando.set(false);
        this.ref.close(true);
      },
      error: (e: ErrorOrganizacion) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        if (e.tipo === 'nombre-duplicado') {
          this.formulario.controls.nombre.setErrors({ duplicado: true });
        }
      },
    };

    if (this.esEdicion) {
      this.api.editarCiudad(this.ciudad!.id, datos).subscribe(alTerminar);
    } else {
      this.api.crearCiudad(datos).subscribe(alTerminar);
    }
  }
}
