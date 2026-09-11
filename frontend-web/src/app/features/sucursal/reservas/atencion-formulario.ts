import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  ReservasService,
  type ErrorReservas,
} from '../../../core/services/reservas.service';
import type {
  Reserva,
  ResultadoPrueba,
} from '../../../core/models/reservas.models';

export interface DatosAtencionFormulario {
  reserva: Reserva;
}

/**
 * CU-24 · Cerrar la reserva con el resultado de la prueba — pasos 5 a 7.
 *
 * **Ninguna prenda viene marcada por defecto**, y es deliberado. Poner
 * «NO_LLEVA» de entrada haría que cerrar sin mirar fuera un clic, y el
 * resultado de la prueba es justamente lo que este caso de uso existe para
 * registrar: cada prenda mueve stock según lo que se marque. El botón de
 * confirmar queda deshabilitado hasta que las dos preguntas estén respondidas.
 *
 * Es la interfaz de la excepción **E11**: el servidor rechaza un cierre con
 * resultados incompletos porque esas unidades quedarían apartadas en una
 * reserva ya cerrada, y no las libera nadie. Acá se evita antes de enviarlo.
 */
@Component({
  selector: 'app-atencion-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './atencion-formulario.html',
  styleUrl: './atencion-formulario.scss',
})
export class AtencionFormulario {
  private readonly api = inject(ReservasService);
  protected readonly datos = inject<DatosAtencionFormulario>(MAT_DIALOG_DATA);
  private readonly dialogo = inject(MatDialogRef<AtencionFormulario>);

  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Qué se marcó para cada línea. Vacío = sin responder. */
  protected readonly marcas = signal<Record<number, ResultadoPrueba>>({});

  protected readonly observacion = new FormControl('', { nonNullable: true });

  protected readonly completo = computed(
    () =>
      this.datos.reserva.lineas.every(
        (linea) => this.marcas()[linea.id] !== undefined,
      ),
  );

  protected readonly seLleva = computed(
    () =>
      this.datos.reserva.lineas
        .filter((l) => this.marcas()[l.id] === 'LLEVA')
        .reduce((suma, l) => suma + l.cantidad, 0),
  );

  protected readonly devuelve = computed(
    () =>
      this.datos.reserva.lineas
        .filter((l) => this.marcas()[l.id] === 'NO_LLEVA')
        .reduce((suma, l) => suma + l.cantidad, 0),
  );

  protected marcar(detalleId: number, resultado: ResultadoPrueba): void {
    this.marcas.update((actuales) => ({ ...actuales, [detalleId]: resultado }));
    this.error.set(null);
  }

  protected marcaDe(detalleId: number): ResultadoPrueba | null {
    return this.marcas()[detalleId] ?? null;
  }

  /** Atajo para el caso más común: el cliente no se llevó nada. */
  protected marcarTodas(resultado: ResultadoPrueba): void {
    const todas: Record<number, ResultadoPrueba> = {};
    for (const linea of this.datos.reserva.lineas) todas[linea.id] = resultado;
    this.marcas.set(todas);
    this.error.set(null);
  }

  protected confirmar(): void {
    if (!this.completo()) {
      this.error.set('Marcá qué pasó con cada prenda antes de cerrar.');
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.api
      .atender(this.datos.reserva.id, {
        resultados: this.datos.reserva.lineas.map((linea) => ({
          detalle_id: linea.id,
          resultado: this.marcas()[linea.id],
        })),
        observacion: this.observacion.value.trim() || null,
      })
      .subscribe({
        next: (reserva) => this.dialogo.close(reserva),
        error: (e: ErrorReservas) => {
          this.guardando.set(false);
          this.error.set(e.mensaje);
        },
      });
  }

  protected cancelar(): void {
    this.dialogo.close(null);
  }
}
