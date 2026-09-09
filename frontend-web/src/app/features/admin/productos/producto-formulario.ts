import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  ProductosService,
  type ErrorProductos,
} from '../../../core/services/productos.service';
import type { Producto, ProductoCrear, ProductoEditar } from '../../../core/models/productos.models';
import { aplanarCategorias, type Categoria, type CategoriaPlana } from '../../../core/models/maestros.models';
import type { Coleccion, Temporada } from '../../../core/models/temporadas.models';
import type { Proveedor } from '../../../core/models/proveedores.models';

/**
 * Lo que la pantalla de productos le pasa al diálogo.
 *
 * Los maestros llegan ya cargados y no se piden acá: la pantalla los necesita
 * igual para sus filtros, y volver a pedirlos al abrir el formulario sería
 * cuatro consultas más por cada alta.
 */
export interface DatosProductoFormulario {
  /** null = alta (pasos 4 a 6); con valor = edición (flujo alternativo 3a). */
  producto: Producto | null;
  arbolCategorias: Categoria[];
  temporadas: Temporada[];
  colecciones: Coleccion[];
  proveedores: Proveedor[];
}

/**
 * CU-10 · Alta y edición de un producto.
 *
 * La regla que se resuelve acá es la excepción **E2**: la colección elegida
 * tiene que pertenecer a la temporada indicada. Se ataca de dos maneras y las
 * dos hacen falta:
 *
 *   - **En la interfaz**, el selector de colecciones solo ofrece las de la
 *     temporada elegida, de modo que la combinación inválida no se puede armar
 *     con el ratón.
 *   - **En el servidor**, igual se valida: el formulario no es la única puerta
 *     —está la API, el *seed*— y la coherencia entre las dos columnas es lo que
 *     paga la redundancia que el esquema aceptó a propósito (§6.4, decisión 2).
 *
 * Elegir una colección **sin** temporada es válido y no se bloquea: el servidor
 * completa la temporada a partir de ella.
 */
@Component({
  selector: 'app-producto-formulario',
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
  ],
  templateUrl: './producto-formulario.html',
  styleUrl: './producto-formulario.scss',
})
export class ProductoFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ProductosService);

  protected readonly ref = inject(MatDialogRef<ProductoFormulario, boolean>);
  protected readonly datos = inject<DatosProductoFormulario>(MAT_DIALOG_DATA);

  protected readonly producto = this.datos.producto;
  protected readonly esEdicion = this.producto !== null;
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly categorias: CategoriaPlana[] = aplanarCategorias(this.datos.arbolCategorias);
  protected readonly temporadas = this.datos.temporadas;
  protected readonly proveedores = this.datos.proveedores;

  /** La temporada elegida, como señal, para poder filtrar las colecciones. */
  private readonly temporadaElegida = signal<number | null>(this.producto?.temporada_id ?? null);

  /**
   * Las colecciones que se pueden elegir.
   *
   * Sin temporada elegida se ofrecen todas: elegir primero la colección es un
   * camino legítimo, y el servidor completa la temporada a partir de ella.
   */
  protected readonly coleccionesDisponibles = computed<Coleccion[]>(() => {
    const temporada = this.temporadaElegida();
    if (temporada === null) return this.datos.colecciones;
    return this.datos.colecciones.filter((c) => c.temporada_id === temporada);
  });

  protected readonly formulario = this.fb.nonNullable.group({
    codigo: [
      this.producto?.codigo ?? '',
      [Validators.required, Validators.maxLength(30)],
    ],
    nombre: [
      this.producto?.nombre ?? '',
      [Validators.required, Validators.maxLength(120)],
    ],
    descripcion: [this.producto?.descripcion ?? '', [Validators.maxLength(500)]],
    categoria_id: [this.producto?.categoria_id ?? (null as number | null), [Validators.required]],
    proveedor_id: [this.producto?.proveedor_id ?? (null as number | null)],
    temporada_id: [this.producto?.temporada_id ?? (null as number | null)],
    coleccion_id: [this.producto?.coleccion_id ?? (null as number | null)],
    // Se valida como texto y no como número: el importe viaja en decimal y
    // pasar por coma flotante introduce el redondeo binario en el precio.
    precio_base: [
      this.producto?.precio_base ?? '',
      [Validators.required, Validators.pattern(/^\d{1,8}([.,]\d{1,2})?$/)],
    ],
    activo: [this.producto?.activo ?? true],
  });

  /**
   * Al cambiar de temporada, una colección de la anterior dejaría de ser
   * válida. Se limpia en vez de dejarla puesta: mantenerla es exactamente la
   * combinación que el servidor rechaza con E2.
   */
  protected alCambiarTemporada(valor: number | null): void {
    this.temporadaElegida.set(valor);
    const coleccion = this.formulario.controls.coleccion_id.value;
    if (coleccion === null) return;
    const sigueSiendoValida = this.coleccionesDisponibles().some((c) => c.id === coleccion);
    if (!sigueSiendoValida) this.formulario.controls.coleccion_id.setValue(null);
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.guardando.set(true);
    this.error.set(null);

    const v = this.formulario.getRawValue();
    // La coma decimal se escribe mucho en Bolivia; el backend espera punto.
    const precio = String(v.precio_base).replace(',', '.');

    const peticion = this.esEdicion
      ? this.api.editar(this.producto!.id, {
          codigo: v.codigo.trim(),
          nombre: v.nombre.trim(),
          descripcion: v.descripcion.trim() || null,
          categoria_id: v.categoria_id!,
          proveedor_id: v.proveedor_id,
          temporada_id: v.temporada_id,
          coleccion_id: v.coleccion_id,
          precio_base: precio,
        } satisfies ProductoEditar)
      : this.api.crear({
          codigo: v.codigo.trim(),
          nombre: v.nombre.trim(),
          descripcion: v.descripcion.trim() || null,
          categoria_id: v.categoria_id!,
          proveedor_id: v.proveedor_id,
          temporada_id: v.temporada_id,
          coleccion_id: v.coleccion_id,
          precio_base: precio,
          activo: v.activo,
        } satisfies ProductoCrear);

    peticion.subscribe({
      next: () => this.ref.close(true),
      error: (e: ErrorProductos) => {
        this.guardando.set(false);
        this.error.set(e.mensaje);
        // E1 y E2 señalan el campo, sin cerrar el diálogo: el caso de uso pide
        // que el Administrador pueda corregir sin volver a escribir todo.
        if (e.tipo === 'codigo-duplicado') {
          this.formulario.controls.codigo.setErrors({ duplicado: true });
        }
        if (e.tipo === 'coleccion-ajena') {
          this.formulario.controls.coleccion_id.setErrors({ ajena: true });
        }
      },
    });
  }
}
