import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import { OrganizacionService } from '../../../core/services/organizacion.service';
import { PerfilService, type ErrorPerfil } from '../../../core/services/perfil.service';
import type { Ciudad } from '../../../core/models/organizacion.models';
import type { Direccion } from '../../../core/models/perfil.models';

export interface DatosDireccion {
  /**
   * Si el cliente ya tiene direcciones, la casilla de predeterminada se ofrece
   * como opción. Si es la primera, el servidor la marca igual, así que la
   * casilla se muestra fija y explicada en vez de dar a elegir algo que no se
   * puede elegir.
   */
  hayDirecciones: boolean;
}

/**
 * Alta de una dirección de entrega — flujo alternativo 3a del CU-04.
 *
 * Devuelve la lista completa de direcciones ya reordenada por el servidor, no
 * solo la nueva: marcarla como predeterminada desmarca otra, y la pantalla
 * tiene que reflejar ambos cambios.
 */
@Component({
  selector: 'app-direccion-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './direccion-formulario.html',
  styleUrl: './direccion-formulario.scss',
})
export class DireccionFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(PerfilService);
  private readonly organizacion = inject(OrganizacionService);

  protected readonly ref = inject(MatDialogRef<DireccionFormulario, Direccion[]>);
  protected readonly datos = inject<DatosDireccion>(MAT_DIALOG_DATA);

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly ciudades = signal<Ciudad[]>([]);

  protected readonly formulario = this.fb.nonNullable.group({
    alias: ['', [Validators.required, Validators.maxLength(40)]],
    ciudad_id: [null as number | null, [Validators.required]],
    direccion: ['', [Validators.required, Validators.maxLength(200)]],
    referencia: ['', [Validators.maxLength(200)]],
    predeterminada: [!this.datos.hayDirecciones],
  });

  constructor() {
    this.organizacion.listarCiudades().subscribe({
      next: (c) => this.ciudades.set(c),
      error: () =>
        this.error.set('No se pudieron cargar las ciudades. Intentá de nuevo.'),
    });
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    this.api
      .agregarDireccion({
        ciudad_id: v.ciudad_id!,
        alias: v.alias.trim(),
        direccion: v.direccion.trim(),
        referencia: v.referencia.trim() || null,
        predeterminada: v.predeterminada,
      })
      .subscribe({
        next: (lista) => {
          this.guardando.set(false);
          this.ref.close(lista);
        },
        error: (e: ErrorPerfil) => {
          this.guardando.set(false);
          this.error.set(e.mensaje);
        },
      });
  }
}
