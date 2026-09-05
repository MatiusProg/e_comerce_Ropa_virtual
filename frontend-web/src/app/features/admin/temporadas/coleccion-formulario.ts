import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import {
  TemporadasService,
  type ErrorTemporadas,
} from '../../../core/services/temporadas.service';
import type { Coleccion, Temporada } from '../../../core/models/temporadas.models';

export interface DatosColeccion {
  temporadas: Temporada[];
  /** null = alta (flujo alternativo 1a); con valor = edición (3a). */
  coleccion: Coleccion | null;
  /** Temporada preseleccionada cuando se crea desde una ya filtrada. */
  temporadaId?: number | null;
}

/**
 * Alta y edición de una colección (flujos alternativos 1a y 3a de CU-09).
 *
 * El nombre es único dentro de la temporada, no en todo el sistema: dos
 * temporadas distintas pueden tener cada una su colección «Playa». Por eso
 * mover una colección a otra temporada puede chocar, y el servidor lo
 * comprueba contra la temporada resultante.
 */
@Component({
  selector: 'app-coleccion-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  template: `
    @if (guardando()) {
      <mat-progress-bar mode="indeterminate" />
    }

    <h2 mat-dialog-title class="vb-titulo">
      {{ esEdicion ? 'Editar colección' : 'Nueva colección' }}
    </h2>

    <mat-dialog-content>
      @if (error(); as e) {
        <div class="aviso" role="alert">
          <mat-icon>error_outline</mat-icon>
          <span>{{ e }}</span>
        </div>
      }

      <form [formGroup]="formulario" (ngSubmit)="guardar()" novalidate id="formulario-coleccion">
        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Temporada</mat-label>
          <mat-select formControlName="temporada_id">
            @for (t of datos.temporadas; track t.id) {
              <mat-option [value]="t.id">
                {{ t.nombre }}
                @if (!t.activa) {
                  <span class="cerrada">· cerrada</span>
                }
              </mat-option>
            }
          </mat-select>
          @if (formulario.controls.temporada_id.hasError('required')) {
            <mat-error>Elija la temporada a la que pertenece.</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Nombre</mat-label>
          <input matInput formControlName="nombre" />
          <mat-hint>Único dentro de su temporada.</mat-hint>
          @if (formulario.controls.nombre.hasError('required')) {
            <mat-error>Ingrese el nombre de la colección.</mat-error>
          } @else if (formulario.controls.nombre.hasError('duplicado')) {
            <mat-error>Esa temporada ya tiene una colección con ese nombre.</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="ancho-completo">
          <mat-label>Descripción</mat-label>
          <textarea matInput rows="2" formControlName="descripcion"></textarea>
          <mat-hint>Opcional.</mat-hint>
        </mat-form-field>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button matButton type="button" (click)="ref.close(false)">Cancelar</button>
      <button
        matButton="filled"
        type="submit"
        form="formulario-coleccion"
        class="vb-boton-marca"
        [disabled]="guardando()"
      >
        {{ esEdicion ? 'Guardar cambios' : 'Registrar colección' }}
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
    .cerrada {
      color: var(--mat-sys-on-surface-variant);
      font-size: 0.85em;
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
export class ColeccionFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(TemporadasService);

  protected readonly ref = inject(MatDialogRef<ColeccionFormulario, boolean>);
  protected readonly datos = inject<DatosColeccion>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.datos.coleccion !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    temporada_id: [
      this.datos.coleccion?.temporada_id ?? this.datos.temporadaId ?? (null as number | null),
      [Validators.required],
    ],
    nombre: [
      this.datos.coleccion?.nombre ?? '',
      [Validators.required, Validators.maxLength(60)],
    ],
    descripcion: [this.datos.coleccion?.descripcion ?? '', [Validators.maxLength(200)]],
  });

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    const comunes = {
      temporada_id: v.temporada_id!,
      nombre: v.nombre.trim(),
      descripcion: v.descripcion.trim() || null,
    };

    const alTerminar = {
      next: () => {
        this.guardando.set(false);
        this.ref.close(true);
      },
      error: (e: ErrorTemporadas) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        if (e.tipo === 'nombre-duplicado') {
          this.formulario.controls.nombre.setErrors({ duplicado: true });
        }
      },
    };

    if (this.esEdicion) {
      this.api.editarColeccion(this.datos.coleccion!.id, comunes).subscribe(alTerminar);
    } else {
      this.api.crearColeccion(comunes).subscribe(alTerminar);
    }
  }
}
