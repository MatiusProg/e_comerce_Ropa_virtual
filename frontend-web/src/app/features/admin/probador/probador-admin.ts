import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import {
  ProbadorService,
  type ErrorProbador,
  type ImagenParaPreparar,
  type MedidaDeTalla,
  type PrendaParaPreparar,
  type ProductoDelProbador,
  type Punto,
} from '../../../core/services/probador.service';
import { UrlMediaPipe } from '../../../shared/url-media.pipe';

type Paso = 'hombro_izq' | 'hombro_der' | 'ruedo';

const PASOS: { clave: Paso; etiqueta: string }[] = [
  { clave: 'hombro_izq', etiqueta: 'Hombro izquierdo' },
  { clave: 'hombro_der', etiqueta: 'Hombro derecho' },
  { clave: 'ruedo', etiqueta: 'Ruedo (donde termina la prenda)' },
];

interface FilaMedida {
  talla_id: number;
  codigo: string;
  busto_cm: number | null;
  cintura_cm: number | null;
  cadera_cm: number | null;
  largo_cm: number | null;
}

/**
 * CU-36 · Preparar prenda para el probador — «boundary» PantallaPrepararPrenda.
 *
 * El Administrador deja una prenda lista para que el cliente se la pruebe con
 * su talla real. Son dos cosas, y la pantalla dice cuál falta:
 *
 * 1. **Los puntos de la imagen.** Sobre el PNG sin fondo de cada variante marca
 *    los dos hombros y el ruedo. Con eso el probador sabe dónde va la línea de
 *    hombros y cuántos píxeles mide la prenda de largo.
 * 2. **Los centímetros por talla.** Lo que mide la PRENDA (con su holgura) en
 *    cada talla. Es lo que hace que una L se vea más grande que una S.
 *
 * Las imágenes se suben en la galería del producto (CU-11), como siempre:
 * acá solo se calibran. Ofrecer otra subida acá duplicaría ese caso de uso.
 */
@Component({
  selector: 'app-probador-admin',
  imports: [
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
    RouterLink,
    UrlMediaPipe,
  ],
  templateUrl: './probador-admin.html',
  styleUrl: './probador-admin.scss',
})
export class ProbadorAdmin implements OnInit {
  private readonly api = inject(ProbadorService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly pasos = PASOS;

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly productos = signal<ProductoDelProbador[]>([]);

  protected readonly cargandoPrenda = signal(false);
  protected readonly prenda = signal<PrendaParaPreparar | null>(null);
  protected readonly imagenElegida = signal<ImagenParaPreparar | null>(null);
  protected readonly puntos = signal<Partial<Record<Paso, Punto>>>({});
  protected readonly paso = signal<Paso>('hombro_izq');
  protected readonly filas = signal<FilaMedida[]>([]);

  protected readonly guardandoPuntos = signal(false);
  protected readonly guardandoMedidas = signal(false);
  protected readonly errorPuntos = signal<string | null>(null);
  protected readonly errorMedidas = signal<string | null>(null);

  protected readonly puntosCompletos = computed(() => {
    const p = this.puntos();
    return !!(p.hombro_izq && p.hombro_der && p.ruedo);
  });

  protected readonly etiquetaDelPaso = computed(
    () => PASOS.find((p) => p.clave === this.paso())?.etiqueta ?? '',
  );

  ngOnInit(): void {
    this.cargarProductos();
  }

  private cargarProductos(): void {
    this.cargando.set(true);
    this.api.productos().subscribe({
      next: (lista) => {
        this.productos.set(lista);
        this.cargando.set(false);
      },
      error: (e: ErrorProbador) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  protected elegirProducto(id: number): void {
    if (this.cargandoPrenda()) return;
    this.cargandoPrenda.set(true);
    this.errorPuntos.set(null);
    this.errorMedidas.set(null);
    this.api.preparacion(id).subscribe({
      next: (prenda) => {
        this.mostrar(prenda);
        this.cargandoPrenda.set(false);
      },
      error: (e: ErrorProbador) => {
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 });
        this.cargandoPrenda.set(false);
      },
    });
  }

  private mostrar(prenda: PrendaParaPreparar, conservarImagen = false): void {
    this.prenda.set(prenda);
    this.filas.set(
      prenda.tallas.map((t) => ({
        talla_id: t.talla_id,
        codigo: t.codigo,
        busto_cm: t.medidas ? Number(t.medidas.busto_cm) : null,
        cintura_cm: t.medidas ? Number(t.medidas.cintura_cm) : null,
        cadera_cm: t.medidas ? Number(t.medidas.cadera_cm) : null,
        largo_cm: t.medidas ? Number(t.medidas.largo_cm) : null,
      })),
    );
    const actual = this.imagenElegida();
    const imagen =
      (conservarImagen && actual
        ? prenda.imagenes.find((i) => i.imagen_id === actual.imagen_id)
        : null) ?? prenda.imagenes[0] ?? null;
    this.elegirImagen(imagen);
  }

  protected elegirImagen(imagen: ImagenParaPreparar | null): void {
    this.imagenElegida.set(imagen);
    this.errorPuntos.set(null);
    this.puntos.set(imagen?.puntos ? { ...imagen.puntos } : {});
    this.paso.set(imagen?.puntos ? 'hombro_izq' : 'hombro_izq');
  }

  /** Un clic sobre la imagen marca el punto del paso actual y pasa al siguiente. */
  protected marcar(evento: MouseEvent): void {
    const img = evento.currentTarget as HTMLElement;
    const caja = img.getBoundingClientRect();
    const punto: Punto = {
      x: redondear((evento.clientX - caja.left) / caja.width),
      y: redondear((evento.clientY - caja.top) / caja.height),
    };
    this.puntos.update((p) => ({ ...p, [this.paso()]: punto }));
    const i = PASOS.findIndex((p) => p.clave === this.paso());
    this.paso.set(PASOS[(i + 1) % PASOS.length].clave);
  }

  protected elegirPaso(paso: Paso): void {
    this.paso.set(paso);
  }

  protected guardarPuntos(): void {
    const imagen = this.imagenElegida();
    const p = this.puntos();
    if (!imagen || !p.hombro_izq || !p.hombro_der || !p.ruedo || this.guardandoPuntos()) return;
    this.guardandoPuntos.set(true);
    this.errorPuntos.set(null);
    this.api
      .guardarPuntos(imagen.imagen_id, {
        hombro_izq: p.hombro_izq,
        hombro_der: p.hombro_der,
        ruedo: p.ruedo,
      })
      .subscribe({
        next: () => {
          this.guardandoPuntos.set(false);
          this.aviso.open('Puntos guardados.', 'Cerrar', { duration: 3000 });
          this.refrescar();
        },
        error: (e: ErrorProbador) => {
          this.guardandoPuntos.set(false);
          this.errorPuntos.set(e.mensaje);
        },
      });
  }

  protected guardarMedidas(): void {
    const prenda = this.prenda();
    if (!prenda || this.guardandoMedidas()) return;
    const completas = this.filas().filter(
      (f) => f.busto_cm && f.cintura_cm && f.cadera_cm && f.largo_cm,
    );
    if (completas.length === 0) {
      this.errorMedidas.set('Cargá las cuatro medidas de al menos una talla.');
      return;
    }
    const incompletas = this.filas().filter(
      (f) =>
        !completas.includes(f) && (f.busto_cm || f.cintura_cm || f.cadera_cm || f.largo_cm),
    );
    if (incompletas.length) {
      this.errorMedidas.set(
        `A la talla ${incompletas.map((f) => f.codigo).join(', ')} le faltan medidas.`,
      );
      return;
    }
    this.guardandoMedidas.set(true);
    this.errorMedidas.set(null);
    const tallas: MedidaDeTalla[] = completas.map((f) => ({
      talla_id: f.talla_id,
      busto_cm: f.busto_cm!,
      cintura_cm: f.cintura_cm!,
      cadera_cm: f.cadera_cm!,
      largo_cm: f.largo_cm!,
    }));
    this.api.guardarMedidas(prenda.producto_id, tallas).subscribe({
      next: (actualizada) => {
        this.guardandoMedidas.set(false);
        this.aviso.open('Medidas guardadas.', 'Cerrar', { duration: 3000 });
        this.mostrar(actualizada, true);
        this.cargarProductos();
      },
      error: (e: ErrorProbador) => {
        this.guardandoMedidas.set(false);
        this.errorMedidas.set(e.mensaje);
      },
    });
  }

  private refrescar(): void {
    const prenda = this.prenda();
    if (!prenda) return;
    this.api.preparacion(prenda.producto_id).subscribe({
      next: (p) => this.mostrar(p, true),
      error: () => undefined,
    });
    this.cargarProductos();
  }

  protected pct(valor: number | undefined): string {
    return `${(valor ?? 0) * 100}%`;
  }
}

function redondear(v: number): number {
  return Math.round(Math.min(1, Math.max(0, v)) * 10000) / 10000;
}
