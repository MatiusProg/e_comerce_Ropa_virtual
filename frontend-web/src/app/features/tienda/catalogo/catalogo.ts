import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { AbstractControl, FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { AuthService } from '../../../core/services/auth.service';
import { TiendaService, type ErrorTienda } from '../../../core/services/tienda.service';
import type {
  FiltrosDisponibles,
  OrdenVitrina,
  PaginaVitrina,
  ProductoVitrina,
} from '../../../core/models/tienda.models';

/**
 * CU-17 · Consultar catálogo — «boundary» PantallaCatalogo.
 *
 * Realiza el flujo principal completo: la vitrina con búsqueda, filtros, orden
 * y paginación (RF07), y la navegación a la ficha (CU-18).
 *
 * **Es pública: no lleva guarda.** El flujo principal del caso de uso no tiene
 * precondición de sesión, y el enunciado pide que el cliente consulte el
 * catálogo desde la web y el móvil. Exigir token obligaría a registrarse para
 * mirar una prenda.
 *
 * Las opciones de los filtros se piden **una vez** al entrar, a `/tienda/filtros`
 * y no a los maestros de CU-08: aquellos exigen rol Administrador, y además
 * devolverían tallas y colores que ningún producto usa —opciones que al
 * elegirlas vacían la vitrina sin que el cliente sepa por qué—.
 *
 * **Falta el filtro por sucursal** que el caso de uso también enuncia: depende
 * de `existencia`, que es tabla de Mateo, y llega con la costura C1 junto con
 * CU-19.
 */
@Component({
  selector: 'app-catalogo',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './catalogo.html',
  styleUrl: './catalogo.scss',
})
export class Catalogo implements OnInit {
  private readonly api = inject(TiendaService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  // --- CU-20 · Favoritos -------------------------------------------------
  //
  // Los corazones se pintan del lado del navegador, con la lista de
  // identificadores que devuelve `/tienda/favoritos/ids`. La vitrina es pública
  // y no sabe quién la mira: agregarle un campo `es_favorito` a la tarjeta
  // obligaría a que el catálogo tuviera sesión, y no la tiene.

  /** Solo el Cliente tiene favoritos. Un Administrador mirando la tienda no ve
   *  corazones, y así el endpoint no se llama para recibir un 403. */
  protected readonly puedeMarcar = computed(() => this.auth.rol() === 'CLIENTE');
  protected readonly favoritos = signal<Set<number>>(new Set());

  protected readonly cargando = signal(false);
  /** Mensaje del último fallo, o null. Distingue «no se pudo consultar» de
   *  «no hay resultados», que en pantalla se confundían. */
  protected readonly error = signal<string | null>(null);
  protected readonly pagina = signal<PaginaVitrina | null>(null);
  protected readonly filtros = signal<FiltrosDisponibles | null>(null);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroCategoria = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroTalla = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroColor = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroTemporada = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly orden = new FormControl<OrdenVitrina>('novedades', { nonNullable: true });

  private indice = 0;
  private tamano = 12;

  /** Si hay algún filtro puesto. Decide si se ofrece «Limpiar filtros», y
   *  también qué dice el cartel de vacío: no es lo mismo un catálogo sin
   *  prendas que una combinación de filtros sin resultados. */
  protected readonly hayFiltros = computed(() => {
    void this.version();
    return Boolean(
      this.busqueda.value ||
        this.filtroCategoria.value ||
        this.filtroTalla.value ||
        this.filtroColor.value ||
        this.filtroTemporada.value,
    );
  });

  /** Contador que se incrementa con cada consulta. Existe solo para que
   *  `hayFiltros` se recalcule: los `FormControl` no son señales, así que un
   *  `computed` que los lee no se enteraría de que cambiaron. */
  private readonly version = signal(0);

  ngOnInit(): void {
    this.api.obtenerFiltros().subscribe({
      next: (filtros) => this.filtros.set(filtros),
      // Que fallen los filtros no puede dejar la vitrina en blanco: se pierde
      // el panel lateral, no el catálogo.
      error: () => this.filtros.set(null),
    });

    // La búsqueda no consulta en cada tecla. Sin el retardo, escribir «blusa»
    // dispara cinco consultas y la última en llegar puede no ser la última
    // escrita.
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.reiniciar());

    // El arreglo se declara como `AbstractControl[]` a propósito: los cinco
    // controles tienen tipos de valor distintos, y sin la anotación TypeScript
    // infiere una unión de firmas de `subscribe` que no son compatibles entre
    // sí, y el `build` falla.
    const controlesDeFiltro: AbstractControl[] = [
      this.filtroCategoria,
      this.filtroTalla,
      this.filtroColor,
      this.filtroTemporada,
      this.orden,
    ];
    for (const control of controlesDeFiltro) {
      control.valueChanges.subscribe(() => this.reiniciar());
    }

    if (this.puedeMarcar()) this.cargarFavoritos();

    this.consultar();
  }

  protected esFavorito(producto: ProductoVitrina): boolean {
    return this.favoritos().has(producto.id);
  }

  /**
   * Marca o desmarca, y actualiza la pantalla antes de que responda el servidor.
   *
   * El corazón tiene que contestar en el acto; esperar la respuesta para
   * pintarlo hace que parezca que no funcionó. Si el servidor falla, se
   * revierte y se avisa — que es el único caso en que el cliente ve un salto.
   */
  protected alternarFavorito(producto: ProductoVitrina, evento: Event): void {
    // La tarjeta entera navega a la ficha: sin esto, tocar el corazón abre la
    // prenda además de marcarla.
    evento.stopPropagation();

    const marcado = this.esFavorito(producto);
    this.pintarFavorito(producto.id, !marcado);

    const peticion = marcado
      ? this.api.desmarcarFavorito(producto.id)
      : this.api.marcarFavorito(producto.id);

    peticion.subscribe({
      error: () => {
        this.pintarFavorito(producto.id, marcado);
        this.error.set('No se pudo actualizar tus favoritos.');
      },
    });
  }

  private pintarFavorito(productoId: number, marcado: boolean): void {
    // Se reemplaza el `Set` en vez de mutarlo: una señal compara por
    // referencia, y mutar el conjunto no redibuja nada.
    const copia = new Set(this.favoritos());
    if (marcado) copia.add(productoId);
    else copia.delete(productoId);
    this.favoritos.set(copia);
  }

  private cargarFavoritos(): void {
    this.api.idsDeFavoritos().subscribe({
      next: (ids) => this.favoritos.set(new Set(ids)),
      // Quedarse sin los corazones no puede vaciar la vitrina.
      error: () => this.favoritos.set(new Set()),
    });
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.tamano = evento.pageSize;
    this.consultar();
  }

  protected limpiar(): void {
    // `emitEvent: false` en los cuatro primeros y una sola consulta al final:
    // sin eso, limpiar cinco controles dispara cinco consultas.
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroCategoria.setValue('', { emitEvent: false });
    this.filtroTalla.setValue('', { emitEvent: false });
    this.filtroColor.setValue('', { emitEvent: false });
    this.filtroTemporada.setValue('', { emitEvent: false });
    this.reiniciar();
  }

  protected abrir(producto: ProductoVitrina): void {
    this.router.navigate(['/tienda/producto', producto.id]);
  }

  /** La URL absoluta de la foto de la tarjeta, o null si no tiene. */
  protected foto(producto: ProductoVitrina): string | null {
    return this.api.urlDeImagen(producto.imagen_url);
  }

  /**
   * El precio que se muestra en la tarjeta.
   *
   * Cuando las variantes valen distinto se anuncia «desde», que es lo que la
   * tarjeta puede prometer sin saber qué talla y color va a elegir el cliente.
   */
  protected precio(producto: ProductoVitrina): string {
    if (!producto.precio_desde) return 'Sin precio';
    if (producto.precio_hasta && producto.precio_hasta !== producto.precio_desde) {
      return `desde Bs ${producto.precio_desde}`;
    }
    return `Bs ${producto.precio_desde}`;
  }

  private reiniciar(): void {
    // Cambiar un filtro vuelve a la primera página. Sin esto, filtrar estando
    // en la página 4 deja una vitrina vacía que parece un error.
    this.indice = 0;
    this.consultar();
  }

  private consultar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.version.update((n) => n + 1);

    this.api
      .listar({
        busqueda: this.busqueda.value || undefined,
        categoria_id: this.filtroCategoria.value || undefined,
        talla_id: this.filtroTalla.value || undefined,
        color_id: this.filtroColor.value || undefined,
        temporada_id: this.filtroTemporada.value || undefined,
        orden: this.orden.value,
        pagina: this.indice + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (pagina) => {
          this.pagina.set(pagina);
          this.cargando.set(false);
        },
        error: (fallo: ErrorTienda) => {
          this.error.set(fallo.mensaje);
          this.pagina.set(null);
          this.cargando.set(false);
        },
      });
  }
}
