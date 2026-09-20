import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';

import { CajaService } from '../../../core/services/caja.service';
import {
  DevolucionesService,
  type ErrorDevolucion,
} from '../../../core/services/devoluciones.service';
import type {
  ComprobanteDevolucion,
  LineaEnDevolucion,
  VentaDevolvible,
} from '../../../core/models/devoluciones.models';

/**
 * CU-32 · Registrar devolución — «boundary» PantallaDevolucion.
 *
 * LO QUE ESTA PANTALLA TIENE QUE DECIR BIEN
 * ------------------------------------------
 * **Cuánto vale lo devuelto y si sale del cajón son dos cosas distintas.** Una
 * venta cobrada con tarjeta se devuelve igual —la prenda vuelve al local— pero
 * el dinero **no sale del cajón**: nunca entró. Mostrar «Bs 250» sin más
 * llevaría al cajero a abrir el cajón y entregarlos, y esa noche el arqueo
 * cerraría con un faltante de 250 Bs que se le anotaría a él.
 *
 * **Lo que ya se devolvió no se puede volver a devolver.** El tope de cada
 * línea es `devolvibles`, no `vendidas`. El servidor lo rechaza igual, pero el
 * cajero no tiene por qué descubrirlo pulsando.
 *
 * El motivo es obligatorio acá y en el servidor. Una devolución sin motivo es
 * mercadería y plata que nadie puede auditar después.
 */
@Component({
  selector: 'app-devolucion',
  imports: [
    CurrencyPipe,
    DatePipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './devolucion.html',
  styleUrl: './devolucion.scss',
})
export class Devolucion implements OnInit {
  private readonly api = inject(DevolucionesService);
  private readonly caja = inject(CajaService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly buscando = signal(false);
  protected readonly guardando = signal(false);
  protected readonly hayTurno = signal<boolean | null>(null);

  protected readonly venta = signal<VentaDevolvible | null>(null);
  protected readonly lineas = signal<LineaEnDevolucion[]>([]);
  protected readonly comprobante = signal<ComprobanteDevolucion | null>(null);

  protected readonly codigo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(3)],
  });
  protected readonly motivo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(3), Validators.maxLength(200)],
  });

  /** El valor de lo que se está devolviendo, en centavos enteros. */
  protected readonly valorCentavos = computed(() =>
    this.lineas().reduce(
      (suma, l) => suma + this.aCentavos(l.linea.precio_unitario) * l.cantidad,
      0,
    ),
  );

  protected readonly hayQueDevolver = computed(() =>
    this.lineas().some((l) => l.cantidad > 0),
  );

  /**
   * Si hay algo devolvible en esta venta.
   *
   * Una venta devuelta entera se busca igual y se encuentra igual: decir «ya se
   * devolvió toda» es una respuesta, y no encontrarla sería mentir.
   */
  protected readonly algoDevolvible = computed(() =>
    (this.venta()?.lineas ?? []).some((l) => l.devolvibles > 0),
  );

  ngOnInit(): void {
    this.caja.miTurno().subscribe({
      next: (t) => {
        this.hayTurno.set(t !== null);
        this.cargando.set(false);
      },
      error: () => {
        this.hayTurno.set(false);
        this.cargando.set(false);
      },
    });
  }

  protected buscar(): void {
    if (this.codigo.invalid || this.buscando()) return;

    this.buscando.set(true);
    this.comprobante.set(null);
    this.api.buscarVenta(this.codigo.value.trim()).subscribe({
      next: (venta) => {
        this.buscando.set(false);
        this.venta.set(venta);
        // Se arranca en cero y no en «todo»: devolver la venta entera es una
        // decisión, no el valor por omisión. Con todo marcado, un descuido
        // reingresa mercadería que el cliente no trajo.
        this.lineas.set(venta.lineas.map((linea) => ({ linea, cantidad: 0 })));
      },
      error: (e: ErrorDevolucion) => {
        this.buscando.set(false);
        this.venta.set(null);
        this.lineas.set([]);
        this.manejar(e);
      },
    });
  }

  protected cambiar(fila: LineaEnDevolucion, cantidad: number): void {
    const tope = fila.linea.devolvibles;
    const nueva = Math.max(0, Math.min(cantidad, tope));
    this.lineas.set(
      this.lineas().map((l) =>
        l.linea.variante_id === fila.linea.variante_id ? { ...l, cantidad: nueva } : l,
      ),
    );
  }

  protected todo(): void {
    this.lineas.set(
      this.lineas().map((l) => ({ ...l, cantidad: l.linea.devolvibles })),
    );
  }

  protected registrar(): void {
    const venta = this.venta();
    if (!venta || !this.hayQueDevolver() || this.motivo.invalid || this.guardando()) {
      this.motivo.markAsTouched();
      return;
    }

    this.guardando.set(true);
    this.api
      .registrar({
        venta_codigo: venta.codigo,
        motivo: this.motivo.value.trim(),
        lineas: this.lineas()
          .filter((l) => l.cantidad > 0)
          .map((l) => ({ variante_id: l.linea.variante_id, cantidad: l.cantidad })),
      })
      .subscribe({
        next: (comprobante) => {
          this.guardando.set(false);
          this.comprobante.set(comprobante);
          this.venta.set(null);
          this.lineas.set([]);
          this.motivo.setValue('');
          this.motivo.markAsUntouched();
          // El arqueo del turno acaba de cambiar si salió plata del cajón.
          this.caja.miTurno().subscribe({ error: () => undefined });
        },
        error: (e: ErrorDevolucion) => {
          this.guardando.set(false);
          this.manejar(e);
          // Si alguien devolvió lo mismo en el medio, la ficha quedó vieja.
          if (e.tipo === 'se-pasa') this.buscar();
        },
      });
  }

  protected otra(): void {
    this.comprobante.set(null);
    this.codigo.setValue('');
  }

  protected subtotalDe(fila: LineaEnDevolucion): number {
    return this.enBs(this.aCentavos(fila.linea.precio_unitario) * fila.cantidad);
  }

  protected enBs(centavos: number): number {
    return centavos / 100;
  }

  private manejar(e: ErrorDevolucion): void {
    if (e.tipo === 'sin-turno') {
      this.hayTurno.set(false);
      return;
    }
    this.aviso.open(e.mensaje, 'Entendido', { duration: 7000 });
  }

  /** El dinero se suma en centavos enteros, nunca en coma flotante. */
  private aCentavos(texto: string): number {
    return Math.round(Number(texto.replace(',', '.')) * 100);
  }
}
