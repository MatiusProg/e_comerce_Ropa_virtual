import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  TemporadasService,
  type ErrorTemporadas,
} from '../../../core/services/temporadas.service';
import type { Temporada } from '../../../core/models/temporadas.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';

/** null = alta (pasos 4 a 7); con valor = edición (flujo alternativo 3a). */
export type DatosTemporada = Temporada | null;

/**
 * Alta y edición de una temporada.
 *
 * Las dos excepciones que llegan hasta acá se resuelven de forma distinta:
 *
 *   E1  fechas incoherentes — se rechaza en el formulario, sin ir al servidor.
 *       Unas fechas invertidas no tienen ninguna lectura válida.
 *   E2  solapamiento — NO se rechaza. El caso de uso pide advertir y pedir
 *       confirmación explícita, así que el 409 abre un diálogo y, si se
 *       confirma, se reenvía con `confirmar_solapamiento`.
 */
@Component({
  selector: 'app-temporada-formulario',
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
  templateUrl: './temporada-formulario.html',
  styleUrl: './temporada-formulario.scss',
})
export class TemporadaFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(TemporadasService);
  private readonly dialogo = inject(MatDialog);

  protected readonly ref = inject(MatDialogRef<TemporadaFormulario, boolean>);
  protected readonly temporada = inject<DatosTemporada>(MAT_DIALOG_DATA);

  protected readonly esEdicion = this.temporada !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly formulario = this.fb.nonNullable.group({
    nombre: [this.temporada?.nombre ?? '', [Validators.required, Validators.maxLength(60)]],
    descripcion: [this.temporada?.descripcion ?? '', [Validators.maxLength(200)]],
    fecha_inicio: [this.temporada?.fecha_inicio ?? '', [Validators.required]],
    fecha_fin: [this.temporada?.fecha_fin ?? '', [Validators.required]],
    activa: [this.temporada?.activa ?? true],
  });

  /**
   * Excepción E1. Es un getter y no un validador de grupo porque el mensaje se
   * muestra debajo del campo de fin, y un error de grupo no lo alcanza.
   */
  protected get rangoInvalido(): boolean {
    const { fecha_inicio, fecha_fin } = this.formulario.getRawValue();
    return !!fecha_inicio && !!fecha_fin && fecha_fin <= fecha_inicio;
  }

  protected guardar(): void {
    if (this.formulario.invalid || this.rangoInvalido) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.enviar(false);
  }

  /** `confirmado` solo llega en true tras aceptar la advertencia de E2. */
  private enviar(confirmado: boolean): void {
    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    this.error.set(null);

    const comunes = {
      nombre: v.nombre.trim(),
      descripcion: v.descripcion.trim() || null,
      fecha_inicio: v.fecha_inicio,
      fecha_fin: v.fecha_fin,
      confirmar_solapamiento: confirmado,
    };

    const alTerminar = {
      next: () => {
        this.guardando.set(false);
        this.ref.close(true);
      },
      error: (e: ErrorTemporadas) => {
        this.guardando.set(false);
        if (e.tipo === 'solapamiento') {
          // Excepción E2: advertir y preguntar, no rechazar.
          this.preguntarPorSolapamiento(e.mensaje);
          return;
        }
        this.error.set(e.mensaje);
        if (e.tipo === 'nombre-duplicado') {
          this.formulario.controls.nombre.setErrors({ duplicado: true });
        }
      },
    };

    if (this.esEdicion) {
      // El estado no viaja acá: cerrar o reabrir es el flujo 3b, que se hace
      // desde el listado y pide su propia confirmación.
      this.api.editarTemporada(this.temporada!.id, comunes).subscribe(alTerminar);
    } else {
      this.api.crearTemporada({ ...comunes, activa: v.activa }).subscribe(alTerminar);
    }
  }

  private preguntarPorSolapamiento(motivo: string): void {
    const datos: DatosConfirmacion = {
      titulo: 'Las fechas se superponen',
      mensaje: `El rango ${motivo}. Dos temporadas abiertas a la vez hacen ambigua cuál es la vigente. ¿Desea guardarla de todos modos?`,
      confirmar: 'Guardar igual',
      peligrosa: true,
    };

    this.dialogo
      .open(Confirmacion, { data: datos, width: '480px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => {
        if (si) this.enviar(true);
      });
  }
}
