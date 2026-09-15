import { Component, computed, inject, signal } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  type FormControl,
} from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import {
  ProveedorService,
  type ErrorMisProductos,
} from '../../../core/services/proveedor.service';
import type { ListasDelFormulario } from '../../../core/models/proveedor.models';
import type { Producto } from '../../../core/models/productos.models';
import { aplanarCategorias, type CategoriaPlana } from '../../../core/models/maestros.models';

export interface DatosProductoFormulario {
  listas: ListasDelFormulario;
  /** Presente sólo al corregir; ausente al registrar. */
  producto?: Producto;
}

/**
 * CU-38 · «boundary» FormularioMiProducto — pasos 4 a 6 y flujo alternativo 3a.
 *
 * Diálogo propio y no el de CU-10 aunque el formulario se parezca. El del
 * Administrador llama a `ProductosService`, que pega en los endpoints de
 * `/catalogo/productos`: reusarlo acá haría que la pantalla del Proveedor
 * pidiera rutas que su rol no puede abrir, y devolverían 403.
 *
 * **Le faltan dos campos respecto del de CU-10, y son justamente el caso de
 * uso:** no hay selector de proveedor —el ámbito sale del token— ni casilla de
 * «activo» —lo que registra el Proveedor nace inactivo, y publicarlo es del
 * Administrador—.
 *
 * El aviso de que nace inactivo se muestra en el alta, no se deja implícito:
 * un proveedor que registra una prenda y no la ve en la tienda tiene que saber
 * por qué antes de que pase, no después.
 */
@Component({
  selector: 'app-mi-producto-formulario',
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
  templateUrl: './producto-formulario.html',
  styleUrl: './producto-formulario.scss',
})
export class MiProductoFormulario {
  private readonly fb = inject(FormBuilder);
  private readonly proveedor = inject(ProveedorService);

  protected readonly ref =
    inject<MatDialogRef<MiProductoFormulario, Producto | undefined>>(MatDialogRef);
  protected readonly datos = inject<DatosProductoFormulario>(MAT_DIALOG_DATA);

  protected readonly editando = this.datos.producto !== undefined;
  protected readonly enviando = signal(false);
  protected readonly error = signal<ErrorMisProductos | null>(null);

  /** El árbol de categorías aplanado, con sangría por nivel. */
  protected readonly categorias: CategoriaPlana[] = aplanarCategorias(
    this.datos.listas.categorias,
  );

  protected readonly formulario = this.fb.nonNullable.group({
    codigo: ['', [Validators.required, Validators.maxLength(30)]],
    nombre: ['', [Validators.required, Validators.maxLength(120)]],
    descripcion: ['', [Validators.maxLength(500)]],
    categoria_id: [null as number | null, [Validators.required]],
    temporada_id: [null as number | null],
    coleccion_id: [null as number | null],
    precio_base: ['', [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)]],
  });

  /**
   * Las colecciones que se pueden elegir con la temporada actual.
   *
   * El servidor exige que la colección pertenezca a la temporada (excepción
   * E2). Filtrarlo acá no reemplaza esa validación —el servidor sigue siendo
   * el que manda— pero evita que alguien componga a mano una combinación que
   * va a rebotar.
   *
   * Sin temporada elegida se ofrecen todas: mandar sólo la colección es
   * legítimo y el servidor completa la temporada a partir de ella.
   */
  protected readonly coleccionesElegibles = computed(() => {
    const temporada = this.temporadaElegida();
    if (temporada === null) return this.datos.listas.colecciones;
    return this.datos.listas.colecciones.filter((c) => c.temporada_id === temporada);
  });

  private readonly temporadaElegida = signal<number | null>(null);

  constructor() {
    const p = this.datos.producto;
    if (p) {
      this.formulario.patchValue({
        codigo: p.codigo,
        nombre: p.nombre,
        descripcion: p.descripcion ?? '',
        categoria_id: p.categoria_id,
        temporada_id: p.temporada_id,
        coleccion_id: p.coleccion_id,
        precio_base: String(p.precio_base),
      });
      this.temporadaElegida.set(p.temporada_id);
    }

    this.formulario.controls.temporada_id.valueChanges.subscribe((valor) => {
      this.temporadaElegida.set(valor);
      // Si la colección elegida ya no pertenece a la temporada nueva, se
      // limpia: dejarla puesta mandaría al servidor una combinación que él
      // rechaza, y el error señalaría un campo que el usuario no tocó.
      const coleccion = this.formulario.controls.coleccion_id.value;
      if (coleccion !== null && !this.coleccionesElegibles().some((c) => c.id === coleccion)) {
        this.formulario.controls.coleccion_id.setValue(null);
      }
    });
  }

  protected control(nombre: keyof typeof this.formulario.controls): FormControl<never> {
    return this.formulario.controls[nombre] as FormControl<never>;
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const v = this.formulario.getRawValue();
    const cuerpo = {
      codigo: v.codigo.trim().toUpperCase(),
      nombre: v.nombre.trim(),
      descripcion: v.descripcion.trim() || null,
      categoria_id: v.categoria_id as number,
      temporada_id: v.temporada_id,
      coleccion_id: v.coleccion_id,
      // La coma decimal es lo que escribe cualquiera acá; el servidor espera punto.
      precio_base: v.precio_base.replace(',', '.'),
    };

    this.enviando.set(true);
    this.error.set(null);

    const peticion = this.datos.producto
      ? this.proveedor.editar(this.datos.producto.id, cuerpo)
      : this.proveedor.registrar(cuerpo);

    peticion.subscribe({
      next: (producto) => {
        this.enviando.set(false);
        this.ref.close(producto);
      },
      error: (e: ErrorMisProductos) => {
        this.enviando.set(false);
        this.error.set(e);
        // El diálogo NO se cierra: el código duplicado (E1) y la colección
        // ajena (E2) se corrigen acá mismo. Cerrarlo perdería lo escrito.
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
