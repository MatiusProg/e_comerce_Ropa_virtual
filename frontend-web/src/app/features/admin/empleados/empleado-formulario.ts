import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import { EmpleadosService, type ErrorEmpleados } from '../../../core/services/empleados.service';
import {
  CONTRASENA_LONGITUD_MINIMA,
  CONTRASENA_PATRON,
} from '../../../core/models/auth.models';
import {
  ETIQUETA_CARGO,
  type Cargo,
  type Empleado,
  type UsuarioVinculable,
} from '../../../core/models/empleados.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';

export interface DatosFormularioEmpleado {
  sucursales: SucursalBreve[];
  /** null = alta; con valor = edición (flujo alternativo 3a). */
  empleado: Empleado | null;
}

/** Los dos caminos del alta, que la ficha trata como excluyentes. */
type CaminoDeAlta = 'nueva' | 'existente';

/**
 * Alta y edición de un empleado (pasos 4 a 7 y flujos 3a y 3c).
 *
 * En el alta, el administrador elige entre crear una cuenta nueva o vincular
 * una existente sin empleado asociado (flujo 3c). Son excluyentes, y el
 * selector lo hace explícito: aceptar los dos a la vez obligaría a decidir cuál
 * gana, y esa ambigüedad no la resuelve bien nadie.
 *
 * Al editar, la cuenta ya está: solo se muestran los datos del empleado y de la
 * persona, nunca la contraseña. Cambiarla es CU-03 o CU-04, no esto.
 */
@Component({
  selector: 'app-empleado-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './empleado-formulario.html',
  styleUrl: './empleado-formulario.scss',
})
export class EmpleadoFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(EmpleadosService);

  protected readonly ref = inject(MatDialogRef<EmpleadoFormulario, boolean>);
  protected readonly datos = inject<DatosFormularioEmpleado>(MAT_DIALOG_DATA);

  protected readonly etiquetaCargo = ETIQUETA_CARGO;
  protected readonly cargos: Cargo[] = ['ENCARGADO', 'CAJERO'];
  protected readonly longitudMinima = CONTRASENA_LONGITUD_MINIMA;
  protected readonly esEdicion = this.datos.empleado !== null;

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly verContrasena = signal(false);
  protected readonly vinculables = signal<UsuarioVinculable[]>([]);
  protected readonly camino = signal<CaminoDeAlta>('nueva');

  /** Los datos de la cuenta solo se piden al crear una nueva. */
  protected readonly pideCuentaNueva = computed(
    () => !this.esEdicion && this.camino() === 'nueva',
  );
  protected readonly pideCuentaExistente = computed(
    () => !this.esEdicion && this.camino() === 'existente',
  );

  protected readonly formulario = this.fb.nonNullable.group({
    // --- Datos de la persona ---
    nombres: [this.datos.empleado?.nombres ?? '', [Validators.maxLength(80)]],
    apellidos: [this.datos.empleado?.apellidos ?? '', [Validators.maxLength(80)]],
    correo: ['', [Validators.email, Validators.maxLength(120)]],
    contrasena: ['', []],
    usuario_id: [null as number | null],

    // --- Datos del empleado ---
    documento: [
      this.datos.empleado?.documento ?? '',
      [Validators.required, Validators.maxLength(20)],
    ],
    telefono: [this.datos.empleado?.telefono ?? '', [Validators.maxLength(20)]],
    cargo: [(this.datos.empleado?.cargo ?? '') as Cargo | '', [Validators.required]],
    sucursal_id: [
      this.datos.empleado?.sucursal_id ?? (null as number | null),
      [Validators.required],
    ],
    fecha_ingreso: [
      this.datos.empleado?.fecha_ingreso ?? new Date().toISOString().slice(0, 10),
      [Validators.required],
    ],
  });

  constructor() {
    if (!this.esEdicion) {
      this.api.usuariosVinculables().subscribe({
        next: (u) => this.vinculables.set(u),
        error: () => this.vinculables.set([]),
      });
    }
    this.ajustarValidaciones();
  }

  protected elegirCamino(camino: CaminoDeAlta): void {
    this.camino.set(camino);
    this.error.set(null);
    this.ajustarValidaciones();
  }

  /**
   * Activa las validaciones del camino elegido y desactiva las del otro.
   *
   * Sin esto, el formulario quedaría inválido por campos que ni siquiera se
   * están mostrando, y el botón de guardar no reaccionaría sin explicación.
   */
  private ajustarValidaciones(): void {
    const { nombres, apellidos, correo, contrasena, usuario_id } = this.formulario.controls;

    const obligatoriosDeCuenta = [nombres, apellidos];
    if (this.pideCuentaNueva()) {
      for (const control of obligatoriosDeCuenta) control.addValidators(Validators.required);
      correo.addValidators(Validators.required);
      contrasena.addValidators([
        Validators.required,
        Validators.minLength(CONTRASENA_LONGITUD_MINIMA),
        Validators.pattern(CONTRASENA_PATRON),
      ]);
      usuario_id.removeValidators(Validators.required);
      usuario_id.setValue(null, { emitEvent: false });
    } else if (this.pideCuentaExistente()) {
      for (const control of obligatoriosDeCuenta) control.removeValidators(Validators.required);
      correo.removeValidators(Validators.required);
      contrasena.clearValidators();
      usuario_id.addValidators(Validators.required);
      correo.setValue('', { emitEvent: false });
      contrasena.setValue('', { emitEvent: false });
    } else {
      // Edición: la cuenta ya existe. Nombres y apellidos se pueden corregir,
      // el correo y la contraseña no se tocan desde acá.
      for (const control of obligatoriosDeCuenta) control.addValidators(Validators.required);
      correo.clearValidators();
      contrasena.clearValidators();
      usuario_id.removeValidators(Validators.required);
    }

    for (const control of [nombres, apellidos, correo, contrasena, usuario_id]) {
      control.updateValueAndValidity({ emitEvent: false });
    }
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
      error: (e: ErrorEmpleados) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // Las excepciones E1 y E2 devuelven el control al formulario: se
        // señala el campo y el diálogo NO se cierra.
        if (e.tipo === 'documento-duplicado') {
          this.formulario.controls.documento.setErrors({ duplicado: true });
        } else if (e.tipo === 'correo-duplicado') {
          this.formulario.controls.correo.setErrors({ duplicado: true });
        } else if (e.tipo === 'sucursal-inactiva') {
          this.formulario.controls.sucursal_id.setErrors({ inactiva: true });
        } else if (e.tipo === 'no-vinculable') {
          this.formulario.controls.usuario_id.setErrors({ noVinculable: true });
        }
      },
    };

    if (this.esEdicion) {
      this.api
        .editar(this.datos.empleado!.id, {
          nombres: v.nombres.trim(),
          apellidos: v.apellidos.trim(),
          documento: v.documento.trim(),
          telefono: v.telefono.trim() || null,
          cargo: v.cargo as Cargo,
          sucursal_id: v.sucursal_id!,
          fecha_ingreso: v.fecha_ingreso,
        })
        .subscribe(alTerminar);
      return;
    }

    const comun = {
      documento: v.documento.trim(),
      telefono: v.telefono.trim() || null,
      cargo: v.cargo as Cargo,
      sucursal_id: v.sucursal_id!,
      fecha_ingreso: v.fecha_ingreso,
    };

    this.api
      .crear(
        this.camino() === 'existente'
          ? { ...comun, usuario_id: v.usuario_id! }
          : {
              ...comun,
              nombres: v.nombres.trim(),
              apellidos: v.apellidos.trim(),
              correo: v.correo.trim().toLowerCase(),
              contrasena: v.contrasena,
            },
      )
      .subscribe(alTerminar);
  }
}
