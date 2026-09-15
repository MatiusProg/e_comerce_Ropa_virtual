import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import {
  ProveedorService,
  type ErrorMisProductos,
} from '../../../core/services/proveedor.service';
import type { ListasDelFormulario } from '../../../core/models/proveedor.models';
import type { Producto } from '../../../core/models/productos.models';

export interface DatosVariantes {
  producto: Producto;
  listas: ListasDelFormulario;
}

/**
 * CU-38 · «boundary» PanelMisVariantes — paso 7.
 *
 * Es la mitad que vuelve útil al registro. Un producto sin variantes no tiene
 * SKU, y sin SKU no hay existencia, ni reserva, ni venta: la decisión D1 dice
 * que la unidad del negocio es la **variante**, no el producto. Registrar una
 * prenda y no declarar en qué tallas y colores se abastece deja algo que la
 * tienda no puede pedir.
 *
 * **Sólo genera; no edita ni borra.** Cambiar el precio de una variante suelta
 * o desactivarla es del Administrador (CU-10, flujos 7b y 7c): son decisiones
 * de venta, no de abastecimiento. El Proveedor declara qué puede traer.
 *
 * Las combinaciones que ya existen se omiten en vez de fallar, así que volver a
 * generar tras agregar un color es seguro y no duplica nada.
 */
@Component({
  selector: 'app-mis-variantes',
  imports: [
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './variantes.html',
  styleUrl: './variantes.scss',
})
export class MisVariantes {
  private readonly proveedor = inject(ProveedorService);

  protected readonly ref = inject<MatDialogRef<MisVariantes, boolean>>(MatDialogRef);
  protected readonly datos = inject<DatosVariantes>(MAT_DIALOG_DATA);

  protected readonly enviando = signal(false);
  protected readonly error = signal<ErrorMisProductos | null>(null);
  protected readonly resultado = signal<{ creadas: number; omitidas: number } | null>(null);

  /** Las variantes que el producto ya tiene, para no pedirlas de nuevo a ciegas. */
  protected readonly existentes = signal(this.datos.producto.variantes ?? []);

  protected readonly tallas = signal<number[]>([]);
  protected readonly colores = signal<number[]>([]);

  /** Cuántas combinaciones saldrían de lo elegido. */
  protected readonly combinaciones = computed(
    () => this.tallas().length * this.colores().length,
  );

  protected readonly puedeGenerar = computed(
    () => this.combinaciones() > 0 && !this.enviando(),
  );

  protected generar(): void {
    if (!this.puedeGenerar()) return;

    this.enviando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.proveedor
      .generarVariantes(this.datos.producto.id, {
        tallas: this.tallas(),
        colores: this.colores(),
      })
      .subscribe({
        next: (r) => {
          this.enviando.set(false);
          this.resultado.set({ creadas: r.creadas, omitidas: r.omitidas });
          this.existentes.set(r.variantes);
          // Se limpia la selección: dejarla puesta invita a pulsar otra vez y
          // ver «0 creadas», que parece un fallo y no lo es.
          this.tallas.set([]);
          this.colores.set([]);
        },
        error: (e: ErrorMisProductos) => {
          this.enviando.set(false);
          this.error.set(e);
        },
      });
  }

  /** `true` si algo cambió: la pantalla de atrás tiene que recargar. */
  protected cerrar(): void {
    this.ref.close(this.resultado() !== null);
  }
}
