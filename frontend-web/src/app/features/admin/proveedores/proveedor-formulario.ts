import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  ProveedoresService,
  type ErrorProveedores,
} from '../../../core/services/proveedores.service';
import type { Proveedor } from '../../../core/models/proveedores.models';

/** null = alta (pasos 4 a 7); con valor = edición (flujo alternativo 3a). */
export type DatosProveedor = Proveedor | null;

/**
 * Alta y edición de un proveedor.
 *
 * Las dos excepciones del caso de uso se resuelven acá además de en el
 * servidor: E1, identificación tributaria duplicada, marcando el campo con lo
 * que responde el 409 —solo el servidor puede saberlo—, y E2, correo con
 * formato inválido, con el validador `email`.
 */
@Component({
  selector: 'app-proveedor-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSlideToggleModule,
  ],
  templateUrl: './proveedor-formulario.html',
  styleUrl: './proveedor-formulario.scss',
})
export class ProveedorFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ProveedoresService);

  protected readonly ref = inject(MatDialogRef<ProveedorFormulario, boolean>);
  protected readonly proveedor = inject<DatosProveedor>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.proveedor !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    razon_social: [
      this.proveedor?.razon_social ?? '',
      [Validators.required, Validators.maxLength(120)],
    ],
    identificacion_tributaria: [
      this.proveedor?.identificacion_tributaria ?? '',
      [Validators.required, Validators.maxLength(30)],
    ],
    contacto: [this.proveedor?.contacto ?? '', [Validators.maxLength(80)]],
    telefono: [this.proveedor?.telefono ?? '', [Validators.maxLength(20)]],
    // Excepción E2: el formato del correo se rechaza antes de enviarlo.
    correo: [this.proveedor?.correo ?? '', [Validators.email, Validators.maxLength(120)]],
    direccion: [this.proveedor?.direccion ?? '', [Validators.maxLength(200)]],
    activo: [this.proveedor?.activo ?? true],
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
      error: (e: ErrorProveedores) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Excepción E1: el caso de uso pide señalar el campo.
        if (e.tipo === 'identificacion-duplicada') {
          this.formulario.controls.identificacion_tributaria.setErrors({ duplicado: true });
        }
      },
    };

    // El texto vacío viaja como null: significa borrar el dato, no dejarlo en
    // cadena vacía. El backend hace la misma conversión.
    const comunes = {
      razon_social: v.razon_social.trim(),
      identificacion_tributaria: v.identificacion_tributaria.trim(),
      contacto: v.contacto.trim() || null,
      telefono: v.telefono.trim() || null,
      correo: v.correo.trim().toLowerCase() || null,
      direccion: v.direccion.trim() || null,
    };

    if (this.esEdicion) {
      // El estado no viaja acá: se cambia desde el listado, que es donde el
      // caso de uso pone la baja (flujo 3b) y pide confirmarla.
      this.api.editar(this.proveedor!.id, comunes).subscribe(alTerminar);
    } else {
      this.api.crear({ ...comunes, activo: v.activo }).subscribe(alTerminar);
    }
  }
}
