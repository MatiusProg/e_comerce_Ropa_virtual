import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TiendaService, type ErrorTienda } from '../../../core/services/tienda.service';
import type {
  ColorTienda,
  FichaProducto,
  TallaTienda,
  VarianteVitrina,
} from '../../../core/models/tienda.models';

/**
 * CU-18 · Consultar ficha de producto — «boundary» PantallaFichaProducto.
 *
 * Realiza el paso 3: la galería, la descripción y la selección de talla y
 * color, que es lo que fija la **variante** —la unidad de negocio (D1)— y con
 * ella el precio y el SKU.
 *
 * **La selección se resuelve en dos pasos y no en uno.** El cliente elige una
 * talla y un color por separado, pero no toda combinación existe: puede haber
 * una blusa en S negra y en M roja, y ninguna en S roja. Elegir la talla, por
 * lo tanto, tiene que restringir los colores ofrecidos —y al revés—; si no, la
 * pantalla deja armar una combinación que no se puede comprar y el error
 * aparece recién al reservar.
 *
 * **El botón del vestidor virtual está en la ficha pero no funciona acá.** La
 * cámara y la detección de pose son del teléfono (RF13: «la aplicación móvil
 * deberá permitir utilizar el vestidor virtual»), así que en la web el botón
 * anuncia la funcionalidad y manda a la app. La ficha ya entrega el activo que
 * hace falta —`imagen_vestidor_url` por variante, costura C5—, de modo que la
 * pantalla móvil no tiene que volver a consultar nada.
 */
@Component({
  selector: 'app-ficha',
  imports: [
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDividerModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './ficha.html',
  styleUrl: './ficha.scss',
})
export class Ficha implements OnInit {
  private readonly api = inject(TiendaService);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly ficha = signal<FichaProducto | null>(null);

  protected readonly tallaElegida = signal<number | null>(null);
  protected readonly colorElegido = signal<number | null>(null);
  /** Índice de la foto grande dentro de la galería. */
  protected readonly fotoActiva = signal(0);

  /** Los colores en los que existe la talla elegida. Sin talla, todos. */
  protected readonly coloresOfrecidos = computed<ColorTienda[]>(() => {
    const ficha = this.ficha();
    if (!ficha) return [];
    const talla = this.tallaElegida();
    if (talla == null) return ficha.colores;
    const ids = new Set(
      ficha.variantes.filter((v) => v.talla_id === talla).map((v) => v.color_id),
    );
    return ficha.colores.filter((c) => ids.has(c.id));
  });

  /** Las tallas en las que existe el color elegido. Sin color, todas. */
  protected readonly tallasOfrecidas = computed<TallaTienda[]>(() => {
    const ficha = this.ficha();
    if (!ficha) return [];
    const color = this.colorElegido();
    if (color == null) return ficha.tallas;
    const ids = new Set(
      ficha.variantes.filter((v) => v.color_id === color).map((v) => v.talla_id),
    );
    return ficha.tallas.filter((t) => ids.has(t.id));
  });

  /** La variante que resulta de la talla y el color elegidos, si ya hay ambos. */
  protected readonly variante = computed<VarianteVitrina | null>(() => {
    const ficha = this.ficha();
    const talla = this.tallaElegida();
    const color = this.colorElegido();
    if (!ficha || talla == null || color == null) return null;
    return (
      ficha.variantes.find((v) => v.talla_id === talla && v.color_id === color) ?? null
    );
  });

  /** El precio que se muestra: el de la variante si ya está elegida, y si no,
   *  el rango del producto. */
  protected readonly precio = computed<string>(() => {
    const variante = this.variante();
    if (variante) return `Bs ${variante.precio}`;

    const ficha = this.ficha();
    if (!ficha?.precio_desde) return 'Sin precio';
    if (ficha.precio_hasta && ficha.precio_hasta !== ficha.precio_desde) {
      return `Bs ${ficha.precio_desde} — ${ficha.precio_hasta}`;
    }
    return `Bs ${ficha.precio_desde}`;
  });

  ngOnInit(): void {
    // `paramMap` y no una lectura suelta: navegar de una prenda a otra sin
    // salir de la ficha reutiliza el componente, y con una lectura única se
    // quedaría mostrando la anterior.
    this.ruta.paramMap.subscribe((parametros) => {
      const id = Number(parametros.get('id'));
      if (!Number.isInteger(id) || id < 1) {
        this.error.set('La prenda que busca ya no está disponible.');
        this.cargando.set(false);
        return;
      }
      this.consultar(id);
    });
  }

  protected elegirTalla(tallaId: number): void {
    this.tallaElegida.set(this.tallaElegida() === tallaId ? null : tallaId);
    // Si el color que estaba elegido no existe en la talla nueva, se suelta:
    // dejarlo mostraría una combinación inexistente como si fuera válida.
    const color = this.colorElegido();
    if (color != null && !this.coloresOfrecidos().some((c) => c.id === color)) {
      this.colorElegido.set(null);
    }
    this.mostrarFotoDeLaVariante();
  }

  protected elegirColor(colorId: number): void {
    this.colorElegido.set(this.colorElegido() === colorId ? null : colorId);
    const talla = this.tallaElegida();
    if (talla != null && !this.tallasOfrecidas().some((t) => t.id === talla)) {
      this.tallaElegida.set(null);
    }
    this.mostrarFotoDeLaVariante();
  }

  protected verFoto(indice: number): void {
    this.fotoActiva.set(indice);
  }

  protected urlDe(url: string | null): string | null {
    return this.api.urlDeImagen(url);
  }

  private consultar(id: number): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.obtenerFicha(id).subscribe({
      next: (ficha) => {
        this.ficha.set(ficha);
        this.tallaElegida.set(null);
        this.colorElegido.set(null);
        this.fotoActiva.set(0);
        this.cargando.set(false);
      },
      error: (fallo: ErrorTienda) => {
        this.error.set(fallo.mensaje);
        this.ficha.set(null);
        this.cargando.set(false);
      },
    });
  }

  /** Si la variante elegida tiene foto propia, la galería salta a ella. */
  private mostrarFotoDeLaVariante(): void {
    const variante = this.variante();
    const ficha = this.ficha();
    if (!variante || !ficha) return;
    const indice = ficha.imagenes.findIndex((i) => i.variante_id === variante.id);
    if (indice >= 0) this.fotoActiva.set(indice);
  }
}
