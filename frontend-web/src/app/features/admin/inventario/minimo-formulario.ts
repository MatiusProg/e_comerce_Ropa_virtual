import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { toSignal } from '@angular/core/rxjs-interop';

import {
  InventarioService,
  type ErrorInventario,
} from '../../../core/services/inventario.service';
import type { Existencia } from '../../../core/models/inventario.models';

export interface DatosMinimoFormulario {
  existencia: Existencia;
}

/**
 * CU-16 · Fijar el punto de reposición de una prenda.
 *
 * **Es la única escritura del inventario que no pide motivo**, y la única que
 * no genera movimiento. No es una excepción a la regla del paquete: lo que no
 * se toca sin dejar rastro es una *cantidad de mercadería*, y el umbral no lo
 * es — es una preferencia de quien administra el local. No hay nada que
 * auditar porque no cambió el stock, solo cuándo avisar sobre él.
 *
 * **Se muestra el efecto antes de guardar.** Escribir «20» sin ver que eso deja
 * la prenda en alerta desde ya es la forma de llenar la pantalla de alertas sin
 * querer; con el aviso en vivo, quien lo fija entiende lo que acaba de pedir.
 */
@Component({
  selector: 'app-minimo-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './minimo-formulario.html',
  styleUrl: './minimo-formulario.scss',
})
export class MinimoFormulario {
  private readonly api = inject(InventarioService);
  protected readonly datos = inject<DatosMinimoFormulario>(MAT_DIALOG_DATA);
  private readonly dialogo = inject(MatDialogRef<MinimoFormulario>);

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly minimo = new FormControl<number | null>(
    this.datos.existencia.stock_minimo,
    [Validators.required, Validators.min(0)],
  );

  private readonly minimoAhora = toSignal(this.minimo.valueChanges, {
    initialValue: this.minimo.value,
  });

  /** Cero apaga la alerta. Se dice en pantalla porque no es evidente. */
  protected readonly apagado = computed(() => this.minimoAhora() === 0);

  /** Si con ese umbral la prenda queda avisando desde ya. */
  protected readonly quedaEnAlerta = computed(() => {
    const valor = this.minimoAhora();
    if (valor === null || valor === undefined || valor === 0) return false;
    return this.datos.existencia.cantidad_disponible <= valor;
  });

  protected confirmar(): void {
    if (this.minimo.invalid) {
      this.minimo.markAsTouched();
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.api
      .fijarStockMinimo(this.datos.existencia.existencia_id, {
        stock_minimo: this.minimo.value!,
      })
      .subscribe({
        next: (existencia) => this.dialogo.close(existencia),
        error: (e: ErrorInventario) => {
          this.guardando.set(false);
          this.error.set(e.mensaje);
        },
      });
  }

  protected cancelar(): void {
    this.dialogo.close(null);
  }
}
