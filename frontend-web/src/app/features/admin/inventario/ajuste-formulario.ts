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

export interface DatosAjusteFormulario {
  existencia: Existencia;
}

/** Mismo mínimo que `MOTIVO_LONGITUD_MINIMA` del backend. */
const MOTIVO_MINIMO = 5;

/**
 * CU-15 · Ajuste por conteo físico — flujo principal.
 *
 * **Se escribe lo que se contó, no la diferencia.** Nadie cuenta «menos tres
 * camisas»: cuenta «hay diecisiete». La diferencia la calcula el servidor, que
 * es quien sabe cuál era el saldo en ese instante; acá se muestra en vivo solo
 * para que la persona vea lo que va a pasar antes de confirmarlo.
 *
 * **Lo que se cuenta es el total físico, reservadas incluidas.** Una prenda
 * apartada para una reserva sigue estando en la percha. El formulario lo dice
 * explícitamente porque es la confusión que arruina un conteo: si alguien
 * contara solo lo «libre», cada reserva viva parecería un faltante.
 *
 * **El motivo es obligatorio.** Es la trazabilidad que pide el RF28, y es lo
 * único que va a explicar dentro de seis meses por qué el saldo cambió.
 */
@Component({
  selector: 'app-ajuste-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './ajuste-formulario.html',
  styleUrl: './ajuste-formulario.scss',
})
export class AjusteFormulario {
  private readonly api = inject(InventarioService);
  protected readonly datos = inject<DatosAjusteFormulario>(MAT_DIALOG_DATA);
  private readonly dialogo = inject(MatDialogRef<AjusteFormulario>);

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly contada = new FormControl<number | null>(
    this.datos.existencia.cantidad_fisica,
    [Validators.required, Validators.min(0)],
  );
  protected readonly motivo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(MOTIVO_MINIMO)],
  });

  private readonly contadaAhora = toSignal(this.contada.valueChanges, {
    initialValue: this.contada.value,
  });

  /** Lo que el ajuste va a escribir, mostrado antes de confirmarlo. */
  protected readonly diferencia = computed(() => {
    const valor = this.contadaAhora();
    if (valor === null || valor === undefined) return null;
    return valor - this.datos.existencia.cantidad_fisica;
  });

  /**
   * Excepción E8, anticipada en pantalla.
   *
   * Con 4 unidades comprometidas en reservas, un conteo de 3 dejaría una
   * reserva sin respaldo físico. El servidor lo rechaza igual; avisarlo acá
   * evita que la persona escriba el motivo para nada.
   */
  protected readonly menorQueLoReservado = computed(() => {
    const valor = this.contadaAhora();
    if (valor === null || valor === undefined) return false;
    return valor < this.datos.existencia.cantidad_reservada;
  });

  protected readonly sinDiferencia = computed(() => this.diferencia() === 0);

  protected confirmar(): void {
    if (this.contada.invalid || this.motivo.invalid) {
      this.contada.markAsTouched();
      this.motivo.markAsTouched();
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.api
      .registrarAjuste({
        variante_id: this.datos.existencia.variante_id,
        sucursal_id: this.datos.existencia.sucursal_id,
        cantidad_contada: this.contada.value!,
        motivo: this.motivo.value.trim(),
      })
      .subscribe({
        next: (ajuste) => this.dialogo.close(ajuste),
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
