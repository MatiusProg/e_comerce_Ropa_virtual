import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import { OrganizacionService } from '../../../core/services/organizacion.service';
import { UsuariosService, type ErrorUsuarios } from '../../../core/services/usuarios.service';
import {
  CONTRASENA_LONGITUD_MINIMA,
  CONTRASENA_PATRON,
  type Rol,
} from '../../../core/models/auth.models';
import {
  ETIQUETA_ROL,
  type RolAsignable,
  type UsuarioResumen,
} from '../../../core/models/usuarios.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';

export interface DatosFormulario {
  roles: RolAsignable[];
  /** null = alta; con valor = edición (flujo alternativo 3a). */
  usuario: UsuarioResumen | null;
}

/**
 * Alta y edición de un usuario (pasos 4 a 7 y flujo alternativo 3a).
 *
 * El campo de sucursal aparece solo cuando el rol elegido lo exige, y el mismo
 * criterio decide si es obligatorio: es la excepción E2 resuelta en la
 * interfaz, además de en el servidor.
 */
@Component({
  selector: 'app-usuario-formulario',
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
  templateUrl: './usuario-formulario.html',
  styleUrl: './usuario-formulario.scss',
})
export class UsuarioFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(UsuariosService);
  private readonly organizacion = inject(OrganizacionService);

  protected readonly ref = inject(MatDialogRef<UsuarioFormulario, boolean>);
  protected readonly datos = inject<DatosFormulario>(MAT_DIALOG_DATA);

  protected readonly etiquetaRol = ETIQUETA_ROL;
  protected readonly longitudMinima = CONTRASENA_LONGITUD_MINIMA;
  protected readonly esEdicion = this.datos.usuario !== null;

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly verContrasena = signal(false);
  protected readonly sucursales = signal<SucursalBreve[]>([]);

  protected readonly rolElegido = signal<Rol | ''>(
    (this.datos.usuario?.rol as Rol) ?? '',
  );

  /** Excepción E2: estos roles no tienen ámbito sin sucursal. */
  protected readonly exigeSucursal = computed(() => {
    const rol = this.rolElegido();
    return this.datos.roles.find((r) => r.nombre === rol)?.exige_sucursal ?? false;
  });

  /** El documento solo se pide al crear un empleado; al editar ya existe su ficha. */
  protected readonly pideDatosEmpleado = computed(
    () => this.exigeSucursal() && !this.esEdicion,
  );

  protected readonly formulario = this.fb.nonNullable.group({
    nombres: [this.datos.usuario?.nombres ?? '', [Validators.required, Validators.maxLength(80)]],
    apellidos: [
      this.datos.usuario?.apellidos ?? '',
      [Validators.required, Validators.maxLength(80)],
    ],
    correo: [
      this.datos.usuario?.correo ?? '',
      [Validators.required, Validators.email, Validators.maxLength(120)],
    ],
    // Al editar, la contraseña queda vacía y solo viaja si se escribe algo
    // (flujo alternativo 3a).
    contrasena: [
      '',
      this.esEdicion
        ? [Validators.minLength(CONTRASENA_LONGITUD_MINIMA), Validators.pattern(CONTRASENA_PATRON)]
        : [
            Validators.required,
            Validators.minLength(CONTRASENA_LONGITUD_MINIMA),
            Validators.pattern(CONTRASENA_PATRON),
          ],
    ],
    rol: [(this.datos.usuario?.rol ?? '') as Rol | '', [Validators.required]],
    sucursal_id: [this.datos.usuario?.sucursal_id ?? (null as number | null)],
    documento: ['', [Validators.maxLength(20)]],
  });

  constructor() {
    this.organizacion.sucursales().subscribe({
      next: (s) => this.sucursales.set(s),
      error: () => this.sucursales.set([]),
    });

    this.formulario.controls.rol.valueChanges.subscribe((rol) => {
      this.rolElegido.set(rol);
      this.ajustarCamposDeAmbito();
    });
    this.ajustarCamposDeAmbito();
  }

  /** Activa o desactiva las validaciones de sucursal y documento según el rol. */
  private ajustarCamposDeAmbito(): void {
    const { sucursal_id, documento } = this.formulario.controls;

    if (this.exigeSucursal()) {
      sucursal_id.addValidators(Validators.required);
    } else {
      sucursal_id.removeValidators(Validators.required);
      sucursal_id.setValue(null, { emitEvent: false });
    }

    if (this.pideDatosEmpleado()) {
      documento.addValidators(Validators.required);
    } else {
      documento.removeValidators(Validators.required);
    }

    sucursal_id.updateValueAndValidity({ emitEvent: false });
    documento.updateValueAndValidity({ emitEvent: false });
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
      error: (e: ErrorUsuarios) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        if (e.tipo === 'correo-duplicado') {
          this.formulario.controls.correo.setErrors({ duplicado: true });
        } else if (e.tipo === 'documento-duplicado') {
          this.formulario.controls.documento.setErrors({ duplicado: true });
        }
      },
    };

    if (this.esEdicion) {
      this.api
        .editar(this.datos.usuario!.id, {
          nombres: v.nombres.trim(),
          apellidos: v.apellidos.trim(),
          correo: v.correo.trim().toLowerCase(),
          // Solo se envía si se escribió una nueva.
          ...(v.contrasena ? { contrasena: v.contrasena } : {}),
          rol: v.rol as Rol,
          sucursal_id: this.exigeSucursal() ? v.sucursal_id : null,
        })
        .subscribe(alTerminar);
    } else {
      this.api
        .crear({
          nombres: v.nombres.trim(),
          apellidos: v.apellidos.trim(),
          correo: v.correo.trim().toLowerCase(),
          contrasena: v.contrasena,
          rol: v.rol as Rol,
          sucursal_id: this.exigeSucursal() ? v.sucursal_id : null,
          documento: this.pideDatosEmpleado() ? v.documento.trim() : null,
        })
        .subscribe(alTerminar);
    }
  }
}
