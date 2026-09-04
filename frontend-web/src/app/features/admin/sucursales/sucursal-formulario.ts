import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  OrganizacionService,
  type ErrorOrganizacion,
} from '../../../core/services/organizacion.service';
import {
  CAPACIDAD_VESTIDORES_MINIMA,
  type Ciudad,
  type Sucursal,
} from '../../../core/models/organizacion.models';

export interface DatosSucursal {
  ciudades: Ciudad[];
  /** null = alta (pasos 4 a 7); con valor = edición (flujo alternativo 3b). */
  sucursal: Sucursal | null;
}

/** `HH:MM:SS` del servidor a `HH:MM`, que es lo que acepta `<input type="time">`. */
function aHoraCorta(valor: string | undefined): string {
  return valor ? valor.slice(0, 5) : '';
}

/**
 * Alta y edición de una sucursal (pasos 4 a 7 y flujo alternativo 3b).
 *
 * Las tres excepciones del caso de uso se resuelven también acá, además de en
 * el servidor:
 *
 *   E1  nombre repetido en la misma ciudad — se marca el campo con lo que
 *       responde el 409, porque solo el servidor puede saberlo.
 *   E3  capacidad de vestidores no positiva — validador `min`.
 *   y la coherencia del horario, que la base exige con un check.
 */
@Component({
  selector: 'app-sucursal-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
  templateUrl: './sucursal-formulario.html',
  styleUrl: './sucursal-formulario.scss',
})
export class SucursalFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(OrganizacionService);

  protected readonly ref = inject(MatDialogRef<SucursalFormulario, boolean>);
  protected readonly datos = inject<DatosSucursal>(MAT_DIALOG_DATA);

  protected readonly capacidadMinima = CAPACIDAD_VESTIDORES_MINIMA;
  protected readonly esEdicion = this.datos.sucursal !== null;

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    ciudad_id: [
      this.datos.sucursal?.ciudad_id ?? (null as number | null),
      [Validators.required],
    ],
    nombre: [
      this.datos.sucursal?.nombre ?? '',
      [Validators.required, Validators.maxLength(80)],
    ],
    direccion: [
      this.datos.sucursal?.direccion ?? '',
      [Validators.required, Validators.maxLength(200)],
    ],
    telefono: [this.datos.sucursal?.telefono ?? '', [Validators.maxLength(20)]],
    horario_apertura: [
      aHoraCorta(this.datos.sucursal?.horario_apertura) || '09:00',
      [Validators.required],
    ],
    horario_cierre: [
      aHoraCorta(this.datos.sucursal?.horario_cierre) || '20:00',
      [Validators.required],
    ],
    // Excepción E3: la capacidad tiene que ser positiva.
    capacidad_vestidores: [
      this.datos.sucursal?.capacidad_vestidores ?? CAPACIDAD_VESTIDORES_MINIMA,
      [Validators.required, Validators.min(CAPACIDAD_VESTIDORES_MINIMA)],
    ],
    activa: [this.datos.sucursal?.activa ?? true],
  });

  /**
   * El cierre tiene que ser posterior a la apertura.
   *
   * Es un getter y no un validador de grupo porque el mensaje se muestra
   * debajo del campo de cierre, y un error de grupo no lo alcanza.
   */
  protected get horarioInvertido(): boolean {
    const { horario_apertura, horario_cierre } = this.formulario.getRawValue();
    return !!horario_apertura && !!horario_cierre && horario_cierre <= horario_apertura;
  }

  protected guardar(): void {
    if (this.formulario.invalid || this.horarioInvertido) {
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
      error: (e: ErrorOrganizacion) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Excepción E1: el caso de uso pide señalar el campo.
        if (e.tipo === 'nombre-duplicado') {
          this.formulario.controls.nombre.setErrors({ duplicado: true });
        }
      },
    };

    const comunes = {
      ciudad_id: v.ciudad_id!,
      nombre: v.nombre.trim(),
      direccion: v.direccion.trim(),
      telefono: v.telefono.trim() || null,
      horario_apertura: v.horario_apertura,
      horario_cierre: v.horario_cierre,
      capacidad_vestidores: Number(v.capacidad_vestidores),
    };

    if (this.esEdicion) {
      // El estado no viaja acá: se cambia desde el listado, que es donde el
      // caso de uso pone la baja (flujo alternativo 3c) y pide confirmarla.
      this.api.editarSucursal(this.datos.sucursal!.id, comunes).subscribe(alTerminar);
    } else {
      this.api.crearSucursal({ ...comunes, activa: v.activa }).subscribe(alTerminar);
    }
  }
}
