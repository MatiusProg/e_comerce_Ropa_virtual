import { Component, inject, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  ProductosService,
  type ErrorProductos,
} from '../../../core/services/productos.service';
import type { Producto, Variante } from '../../../core/models/productos.models';
import type { Color, Talla } from '../../../core/models/maestros.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';

export interface DatosVariantes {
  producto: Producto;
  tallas: Talla[];
  colores: Color[];
}

/**
 * CU-10 · Paso 7 y sus flujos alternativos — las variantes de un producto.
 *
 * El paso 7 del caso de uso no es «agregar una variante»: es elegir las tallas
 * y los colores y que el sistema **genere la combinación completa**. Cargar
 * doce variantes de a una es el trabajo que esta pantalla existe para evitar.
 *
 * Volver a generar no rompe nada: las combinaciones que ya existen se omiten,
 * y el resultado dice cuántas creó y cuántas omitió. Sin ese conteo, agregar
 * una talla a un producto de veinte variantes dejaría al Administrador
 * comparando la tabla antes y después para saber si funcionó.
 *
 * El SKU no se edita: lo arma el servidor a partir del código del producto, la
 * talla y el color, y tiene que seguir siendo el mismo si se regenera.
 */
@Component({
  selector: 'app-variantes',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './variantes.html',
  styleUrl: './variantes.scss',
})
export class Variantes {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ProductosService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly ref = inject(MatDialogRef<Variantes, boolean>);
  protected readonly datos = inject<DatosVariantes>(MAT_DIALOG_DATA);

  protected readonly columnas = ['sku', 'talla', 'color', 'precio', 'estado', 'acciones'];

  protected readonly producto = signal<Producto>(this.datos.producto);
  protected readonly variantes = signal<Variante[]>(this.datos.producto.variantes);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  /** Se marca en cuanto algo cambia, para que la pantalla de fondo recargue. */
  private readonly hubocambios = signal(false);

  /** Fila cuyo precio se está editando, o null. */
  protected readonly editandoPrecio = signal<number | null>(null);
  protected readonly precioEnEdicion = new FormControl('', { nonNullable: true });

  protected readonly generacion = this.fb.nonNullable.group({
    tallas: [[] as number[], [Validators.required]],
    colores: [[] as number[], [Validators.required]],
    precio: ['', [Validators.pattern(/^\d{1,8}([.,]\d{1,2})?$/)]],
  });

  protected get combinacionesAGenerar(): number {
    const v = this.generacion.getRawValue();
    return v.tallas.length * v.colores.length;
  }

  /** Paso 7. */
  protected generar(): void {
    if (this.generacion.invalid) {
      this.generacion.markAllAsTouched();
      return;
    }
    this.cargando.set(true);
    this.error.set(null);
    const v = this.generacion.getRawValue();

    this.api
      .generarVariantes(this.producto().id, {
        tallas: v.tallas,
        colores: v.colores,
        precio: v.precio ? String(v.precio).replace(',', '.') : null,
      })
      .subscribe({
        next: (resultado) => {
          this.hubocambios.set(true);
          // El mensaje nombra las dos cifras. «Omitidas» no es un fallo: son
          // las que ya existian, y decirlo evita que parezca que no hizo nada.
          const partes = [`${resultado.creadas} variante(s) creada(s)`];
          if (resultado.omitidas > 0) {
            partes.push(`${resultado.omitidas} ya existía(n)`);
          }
          this.mostrar(partes.join(' · '));
          this.generacion.reset({ tallas: [], colores: [], precio: '' });
          this.recargar();
        },
        error: (e: ErrorProductos) => {
          this.cargando.set(false);
          this.error.set(e.mensaje);
        },
      });
  }

  /** Flujo alternativo 7b: el precio, en la propia fila. */
  protected empezarAEditarPrecio(variante: Variante): void {
    this.editandoPrecio.set(variante.id);
    this.precioEnEdicion.setValue(variante.precio);
  }

  protected cancelarEdicionPrecio(): void {
    this.editandoPrecio.set(null);
  }

  protected guardarPrecio(variante: Variante): void {
    const valor = String(this.precioEnEdicion.value).replace(',', '.');
    if (!/^\d{1,8}(\.\d{1,2})?$/.test(valor)) {
      this.mostrar('Escriba un importe con hasta dos decimales.');
      return;
    }
    this.cargando.set(true);
    this.api.editarVariante(variante.id, { precio: valor }).subscribe({
      next: () => {
        this.hubocambios.set(true);
        this.editandoPrecio.set(null);
        this.mostrar('Precio actualizado.');
        this.recargar();
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  /** Flujo alternativo 7c. */
  protected cambiarEstado(variante: Variante): void {
    this.fijarEstado(variante, !variante.activa);
  }

  private fijarEstado(variante: Variante, activa: boolean): void {
    this.cargando.set(true);
    this.api.editarVariante(variante.id, { activa }).subscribe({
      next: () => {
        this.hubocambios.set(true);
        this.mostrar(activa ? 'Variante activada.' : 'Variante desactivada.');
        this.recargar();
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  protected eliminar(variante: Variante): void {
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'Eliminar variante',
          mensaje: `Se eliminará la variante ${variante.sku}. Si ya tiene existencias o reservas, no se podrá y convendrá desactivarla.`,
          confirmar: 'Eliminar',
          peligrosa: true,
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.cargando.set(true);
        this.api.eliminarVariante(variante.id).subscribe({
          next: () => {
            this.hubocambios.set(true);
            this.mostrar('Variante eliminada.');
            this.recargar();
          },
          error: (e: ErrorProductos) => {
            this.cargando.set(false);
            // Excepcion E3: no es un fallo del sistema, es una regla. Se ofrece
            // la salida que el caso de uso indica.
            if (e.tipo === 'con-dependencias') {
              this.ofrecerDesactivar(variante, e.mensaje);
              return;
            }
            this.mostrar(e.mensaje);
          },
        });
      });
  }

  private ofrecerDesactivar(variante: Variante, mensaje: string): void {
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'No se puede eliminar',
          mensaje: `${mensaje} ¿Desea desactivarla?`,
          confirmar: 'Desactivar',
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (confirmado) this.fijarEstado(variante, false);
      });
  }

  protected cerrar(): void {
    this.ref.close(this.hubocambios());
  }

  private recargar(): void {
    this.api.obtener(this.producto().id).subscribe({
      next: (p) => {
        this.producto.set(p);
        this.variantes.set(p.variantes);
        this.cargando.set(false);
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.error.set(e.mensaje);
      },
    });
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 4000 });
  }
}
