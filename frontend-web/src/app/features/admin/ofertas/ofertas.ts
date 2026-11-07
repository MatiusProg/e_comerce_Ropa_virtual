import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { RouterLink } from '@angular/router';
import {
  EMPTY,
  catchError,
  debounceTime,
  distinctUntilChanged,
  expand,
  map,
  of,
  reduce,
  startWith,
  switchMap,
} from 'rxjs';

import type { Aplicacion, Candidata, Mayorista } from '../../../core/models/ofertas.models';
import type { ProductoResumen } from '../../../core/models/productos.models';
import { OfertasService } from '../../../core/services/ofertas.service';
import { ProductosService } from '../../../core/services/productos.service';
import { BsPipe } from '../../../shared/bs.pipe';

/**
 * 3ra presentación · CU-31 Gestionar ofertas y precios mayoristas y CU-32
 * Aplicar ofertas de fuera de temporada. «boundary» PantallaOfertas.
 *
 * - **Mayoristas** (RF-56): escalones «desde N prendas del producto, a Bs X».
 * - **Fuera de temporada** (RF-57): el factor medible guardado en la base y la
 *   aplicación, que crea las ofertas automáticas.
 * - Las **ofertas manuales** (RF-58) son las promociones de siempre: se
 *   enlazan, no se duplican.
 */
@Component({
  selector: 'app-ofertas',
  imports: [
    BsPipe,
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSlideToggleModule,
    MatTabsModule,
  ],
  templateUrl: './ofertas.html',
  styleUrl: './ofertas.scss',
})
export class Ofertas implements OnInit {
  private readonly api = inject(OfertasService);
  private readonly productosApi = inject(ProductosService);
  private readonly aviso = inject(MatSnackBar);
  private readonly destruir = inject(DestroyRef);

  // --- CU-31 · Mayoristas ----------------------------------------------
  protected readonly cargando = signal(true);
  protected readonly mayoristas = signal<Mayorista[]>([]);
  protected readonly guardando = signal(false);
  /** El escalón que se está editando, o nulo si el formulario es de alta. */
  protected readonly editando = signal<Mayorista | null>(null);

  protected readonly busquedaProducto = new FormControl('', { nonNullable: true });
  protected readonly productos = signal<ProductoResumen[]>([]);
  protected readonly producto = signal<ProductoResumen | null>(null);
  protected readonly formulario = new FormGroup({
    cantidad_minima: new FormControl<number | null>(6, [Validators.required, Validators.min(2)]),
    precio_unitario: new FormControl<number | null>(null, [
      Validators.required,
      Validators.min(0.01),
    ]),
  });

  // --- CU-32 · Fuera de temporada --------------------------------------
  protected readonly regla = new FormGroup({
    activa: new FormControl(false, { nonNullable: true }),
    dias_desde_fin: new FormControl<number | null>(30, [Validators.required, Validators.min(0)]),
    existencia_minima: new FormControl<number | null>(10, [Validators.required, Validators.min(1)]),
    porcentaje: new FormControl<number | null>(30, [
      Validators.required,
      Validators.min(0.01),
      Validators.max(90),
    ]),
  });
  protected readonly reglaPorOmision = signal(false);
  protected readonly guardandoRegla = signal(false);
  protected readonly candidatas = signal<Candidata[]>([]);
  protected readonly cargandoCandidatas = signal(false);
  protected readonly aplicando = signal(false);
  protected readonly ultima = signal<Aplicacion | null>(null);

  protected readonly etiquetaSituacion: Record<string, string> = {
    NUEVA: 'Entraría en oferta',
    VIGENTE: 'Ya en oferta',
    APAGADA: 'Apagada a mano',
    CREADA: 'Oferta creada',
  };

  ngOnInit(): void {
    this.cargarMayoristas();
    this.cargarRegla();

    this.busquedaProducto.valueChanges
      .pipe(
        startWith(''),
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((texto) =>
          this.productosApi
            .listar({ busqueda: texto.trim() || undefined, activo: true, tamano: 8 })
            .pipe(
              map((p) => p.items),
              catchError(() => of([] as ProductoResumen[])),
            ),
        ),
        takeUntilDestroyed(this.destruir),
      )
      .subscribe((p) => this.productos.set(p));
  }

  // --- Mayoristas -------------------------------------------------------
  private cargarMayoristas(): void {
    this.cargando.set(true);
    // Se traen TODAS las páginas (de a 100, el tope del backend): antes se
    // pedía una sola de 50 y los escalones que sobraban no se veían nunca.
    const POR_PAGINA = 100;
    this.api
      .listarMayoristas('', 1, POR_PAGINA)
      .pipe(
        expand((p) =>
          p.pagina * p.tamano < p.total
            ? this.api.listarMayoristas('', p.pagina + 1, POR_PAGINA)
            : EMPTY,
        ),
        reduce((todos, p) => todos.concat(p.items), [] as Mayorista[]),
      )
      .subscribe({
        next: (items) => {
          this.mayoristas.set(items);
          this.cargando.set(false);
        },
        error: (e: HttpErrorResponse) => {
          this.cargando.set(false);
          this.mostrar(e, 'No se pudieron leer los precios mayoristas.');
        },
      });
  }

  protected elegirProducto(p: ProductoResumen): void {
    this.producto.set(p);
  }

  protected editar(m: Mayorista): void {
    this.editando.set(m);
    this.producto.set(null);
    this.formulario.setValue({
      cantidad_minima: m.cantidad_minima,
      precio_unitario: Number(m.precio_unitario),
    });
  }

  protected cancelar(): void {
    this.editando.set(null);
    this.producto.set(null);
    this.formulario.reset({ cantidad_minima: 6, precio_unitario: null });
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const cantidad = this.formulario.value.cantidad_minima!;
    const precio = Number(this.formulario.value.precio_unitario).toFixed(2);
    const editando = this.editando();
    const producto = this.producto();
    if (!editando && !producto) {
      this.aviso.open('Elija el producto.', 'Entendido', { duration: 4000 });
      return;
    }
    this.guardando.set(true);
    const peticion = editando
      ? this.api.editarMayorista(editando.id, {
          cantidad_minima: cantidad,
          precio_unitario: precio,
        })
      : this.api.crearMayorista({
          producto_id: producto!.id,
          cantidad_minima: cantidad,
          precio_unitario: precio,
        });
    peticion.subscribe({
      next: (m) => {
        this.guardando.set(false);
        this.aviso.open(
          `${m.producto}: desde ${m.cantidad_minima} u. a Bs ${m.precio_unitario} c/u.`,
          'Entendido',
          { duration: 5000 },
        );
        this.cancelar();
        this.cargarMayoristas();
      },
      error: (e: HttpErrorResponse) => {
        this.guardando.set(false);
        this.mostrar(e, 'No se pudo guardar el precio mayorista.');
      },
    });
  }

  /** Si falla, el interruptor vuelve a como estaba (recargar no lo reescribe). */
  protected cambiarEstado(m: Mayorista, activo: boolean, control?: { checked: boolean }): void {
    this.api.estadoMayorista(m.id, activo).subscribe({
      next: (nuevo) =>
        this.mayoristas.set(this.mayoristas().map((x) => (x.id === nuevo.id ? nuevo : x))),
      error: (e: HttpErrorResponse) => {
        this.mostrar(e, 'No se pudo cambiar el estado.');
        if (control) control.checked = !activo;
        this.cargarMayoristas();
      },
    });
  }

  // --- Fuera de temporada -------------------------------------------------
  private cargarRegla(): void {
    this.api.regla().subscribe({
      next: (r) => {
        this.regla.setValue({
          activa: r.activa,
          dias_desde_fin: r.dias_desde_fin,
          existencia_minima: r.existencia_minima,
          porcentaje: Number(r.porcentaje),
        });
        this.reglaPorOmision.set(!!r.por_omision);
        this.cargarCandidatas();
      },
      error: (e: HttpErrorResponse) => this.mostrar(e, 'No se pudo leer la regla.'),
    });
  }

  protected cargarCandidatas(): void {
    this.cargandoCandidatas.set(true);
    this.api.candidatas().subscribe({
      next: (c) => {
        this.candidatas.set(c);
        this.cargandoCandidatas.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.cargandoCandidatas.set(false);
        this.mostrar(e, 'No se pudieron calcular las prendas que califican.');
      },
    });
  }

  protected guardarRegla(): void {
    if (this.regla.invalid) {
      this.regla.markAllAsTouched();
      return;
    }
    const v = this.regla.getRawValue();
    this.guardandoRegla.set(true);
    this.api
      .guardarRegla({
        activa: v.activa,
        dias_desde_fin: v.dias_desde_fin!,
        existencia_minima: v.existencia_minima!,
        porcentaje: Number(v.porcentaje).toFixed(2),
      })
      .subscribe({
        next: () => {
          this.guardandoRegla.set(false);
          this.reglaPorOmision.set(false);
          this.aviso.open('Regla guardada.', 'Entendido', { duration: 4000 });
          this.cargarCandidatas();
        },
        error: (e: HttpErrorResponse) => {
          this.guardandoRegla.set(false);
          this.mostrar(e, 'No se pudo guardar la regla.');
        },
      });
  }

  protected aplicar(): void {
    this.aplicando.set(true);
    this.api.aplicar().subscribe({
      next: (a) => {
        this.aplicando.set(false);
        this.ultima.set(a);
        this.candidatas.set(a.candidatas);
        const partes = [`${a.creadas} creada${a.creadas === 1 ? '' : 's'}`];
        if (a.cerradas) partes.push(`${a.cerradas} cerrada${a.cerradas === 1 ? '' : 's'}`);
        this.aviso.open(
          a.regla_activa
            ? `Ofertas de fuera de temporada: ${partes.join(', ')}.`
            : `La regla está apagada: no se creó ninguna oferta${a.cerradas ? `; ${partes[1]}` : ''}.`,
          'Entendido',
          { duration: 6000 },
        );
      },
      error: (e: HttpErrorResponse) => {
        this.aplicando.set(false);
        this.mostrar(e, 'No se pudieron aplicar las ofertas.');
      },
    });
  }

  private mostrar(e: HttpErrorResponse, porOmision: string): void {
    const texto = typeof e.error?.detail === 'string' ? e.error.detail : porOmision;
    this.aviso.open(texto, 'Entendido', { duration: 7000 });
  }
}
