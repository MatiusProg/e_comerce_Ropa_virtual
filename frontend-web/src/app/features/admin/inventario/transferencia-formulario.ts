import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { toSignal } from '@angular/core/rxjs-interop';

import {
  InventarioService,
  type ErrorInventario,
} from '../../../core/services/inventario.service';
import type { Existencia } from '../../../core/models/inventario.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';

export interface DatosTransferenciaFormulario {
  /** El saldo desde el que se abrió, o null si se abrió desde el botón general. */
  existencia: Existencia | null;
  /** Saldos disponibles, para elegir origen cuando no vino uno fijado. */
  existencias: Existencia[];
  sucursales: SucursalBreve[];
}

const MOTIVO_MINIMO = 5;

/**
 * CU-15 · Transferencia entre sucursales — flujo alternativo 3a.
 *
 * **El origen es una existencia, no una sucursal.** Se transfiere una prenda
 * concreta que está en un local concreto, y esa combinación ya tiene un saldo
 * conocido: eligiendo la existencia, la cantidad máxima se sabe sin preguntar
 * nada más. Pedir «prenda» y «sucursal origen» por separado permitiría armar
 * una combinación que no existe y descubrirlo recién al enviar.
 *
 * **El destino no puede ser el origen** (excepción E5) y se filtra del
 * desplegable, de modo que la combinación inválida no se pueda armar con el
 * ratón. El servidor la rechaza igual: el formulario no es la única puerta.
 *
 * **El tope de la cantidad es lo disponible, no lo físico.** Lo reservado sigue
 * en la percha pero ya está comprometido con un cliente de esa sucursal;
 * mandarlo a otra dejaría la reserva sin prenda que entregar.
 */
@Component({
  selector: 'app-transferencia-formulario',
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
  templateUrl: './transferencia-formulario.html',
  styleUrl: './transferencia-formulario.scss',
})
export class TransferenciaFormulario {
  private readonly api = inject(InventarioService);
  protected readonly datos = inject<DatosTransferenciaFormulario>(MAT_DIALOG_DATA);
  private readonly dialogo = inject(MatDialogRef<TransferenciaFormulario>);

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Solo se puede transferir lo que tiene saldo disponible. */
  protected readonly origenes = this.datos.existencias.filter(
    (e) => e.cantidad_disponible > 0,
  );

  protected readonly origen = new FormControl<number | null>(
    this.datos.existencia?.existencia_id ?? null,
    Validators.required,
  );
  protected readonly destino = new FormControl<number | null>(null, Validators.required);
  protected readonly cantidad = new FormControl<number | null>(null, [
    Validators.required,
    Validators.min(1),
  ]);
  protected readonly motivo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(MOTIVO_MINIMO)],
  });

  private readonly origenAhora = toSignal(this.origen.valueChanges, {
    initialValue: this.origen.value,
  });

  protected readonly existenciaOrigen = computed(() => {
    const id = this.origenAhora();
    if (id === null || id === undefined) return this.datos.existencia;
    return (
      this.datos.existencias.find((e) => e.existencia_id === id) ??
      this.datos.existencia
    );
  });

  protected readonly maximo = computed(
    () => this.existenciaOrigen()?.cantidad_disponible ?? 0,
  );

  /** E5: el destino nunca es el origen. */
  protected readonly destinos = computed(() => {
    const actual = this.existenciaOrigen();
    return this.datos.sucursales.filter((s) => s.id !== actual?.sucursal_id);
  });

  protected etiquetaDeOrigen(existencia: Existencia): string {
    return (
      `${existencia.sku} · ${existencia.producto} ${existencia.talla}/${existencia.color}` +
      ` — ${existencia.sucursal} (${existencia.cantidad_disponible} disp.)`
    );
  }

  protected confirmar(): void {
    const actual = this.existenciaOrigen();
    if (!actual || this.destino.invalid || this.cantidad.invalid || this.motivo.invalid) {
      this.destino.markAsTouched();
      this.cantidad.markAsTouched();
      this.motivo.markAsTouched();
      return;
    }

    const cuantas = this.cantidad.value!;
    if (cuantas > this.maximo()) {
      this.error.set(
        `Solo hay ${this.maximo()} unidades disponibles en ${actual.sucursal}.`,
      );
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.api
      .registrarTransferencia({
        variante_id: actual.variante_id,
        sucursal_origen_id: actual.sucursal_id,
        sucursal_destino_id: this.destino.value!,
        cantidad: cuantas,
        motivo: this.motivo.value.trim(),
      })
      .subscribe({
        next: (hecha) => this.dialogo.close(hecha),
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
