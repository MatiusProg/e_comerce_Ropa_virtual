import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import type { ChartConfiguration } from 'chart.js';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';

import type { ClienteSegmento, ResumenAnalitica } from '../../../core/models/analitica.models';
import { AnaliticaService, type ErrorAnalitica } from '../../../core/services/analitica.service';
import { BsPipe } from '../../../shared/bs.pipe';
import { AnomaliasPanel } from './anomalias/anomalias-panel';

/** Los mismos colores de marca que el tablero (ver `tablero.ts`). */
const COLORES = {
  malva: '#8e4a67',
  malvaClaro: '#b57f9a',
  rosaPalido: '#e7bfa8',
  oro: '#c9a227',
  humo: '#cbbcc4',
} as const;
const PALETA = [COLORES.malva, COLORES.oro, COLORES.malvaClaro, COLORES.rosaPalido, COLORES.humo, '#6b3a50'];

/** Cómo se lee cada variable del modelo de demanda. */
const VARIABLES: Record<string, string> = {
  semana_seno: 'Época del año (seno)',
  semana_coseno: 'Época del año (coseno)',
  mes: 'Mes',
  rezago_1: 'Ventas de la semana anterior',
  rezago_2: 'Ventas de hace 2 semanas',
  rezago_4: 'Ventas de hace 4 semanas',
  media_4: 'Media de las últimas 4 semanas',
  precio: 'Precio',
  categoria: 'Categoría',
  de_temporada: 'Es de temporada',
};

/**
 * CU-29 Entrenar los modelos de analítica y CU-30 Consultar el dashboard
 * analítico — «boundary» PantallaAnalitica.
 *
 * Arriba, el botón que entrena (CU-29) y las métricas de la validación; abajo,
 * los resultados: la demanda prevista de la semana que viene (supervisado) y
 * los segmentos de clientes (no supervisado), con su gráfico cada uno.
 *
 * Chart.js se provee en el componente, como en el tablero: así viaja en el
 * trozo diferido de esta pantalla y no en el arranque de todas.
 */
@Component({
  selector: 'app-analitica',
  imports: [
    AnomaliasPanel,
    BsPipe,
    DatePipe,
    DecimalPipe,
    RouterLink,
    BaseChartDirective,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './analitica.html',
  styleUrl: './analitica.scss',
})
export class Analitica implements OnInit {
  private readonly api = inject(AnaliticaService);

  protected readonly cargando = signal(true);
  protected readonly entrenando = signal(false);
  protected readonly descargando = signal<'pdf' | 'xlsx' | null>(null);
  protected readonly error = signal<ErrorAnalitica | null>(null);
  protected readonly datos = signal<ResumenAnalitica | null>(null);
  protected readonly clientes = signal<ClienteSegmento[]>([]);

  protected readonly demanda = computed(() => this.datos()?.demanda ?? null);
  protected readonly segmentos = computed(() => this.datos()?.segmentos ?? null);
  protected readonly prediccion = computed(() => this.datos()?.predicciones ?? null);
  protected readonly top = computed(() => this.prediccion()?.predicciones.slice(0, 15) ?? []);

  protected readonly graficoValidacion = computed<ChartConfiguration<'line'>['data'] | null>(() => {
    const p = this.prediccion();
    if (!p) return null;
    return {
      labels: p.serie_validacion.map((s) => this.fechaCorta(s.semana)),
      datasets: [
        {
          label: 'Real',
          data: p.serie_validacion.map((s) => s.real),
          borderColor: COLORES.malva,
          backgroundColor: COLORES.malva,
          tension: 0.25,
        },
        {
          label: 'Prevista por el modelo',
          data: p.serie_validacion.map((s) => s.prevista),
          borderColor: COLORES.oro,
          backgroundColor: COLORES.oro,
          borderDash: [6, 4],
          tension: 0.25,
        },
      ],
    };
  });

  protected readonly graficoImportancia = computed<ChartConfiguration<'bar'>['data'] | null>(() => {
    const p = this.prediccion();
    if (!p) return null;
    const filas = p.importancia.slice(0, 6);
    return {
      labels: filas.map((f) => VARIABLES[f.variable] ?? f.variable),
      datasets: [
        {
          label: 'Peso en la predicción',
          data: filas.map((f) => Math.round(f.peso * 1000) / 10),
          backgroundColor: COLORES.malvaClaro,
        },
      ],
    };
  });

  protected readonly graficoSegmentos = computed<ChartConfiguration<'doughnut'>['data'] | null>(() => {
    const grupos = this.datos()?.grupos ?? [];
    if (!grupos.length) return null;
    return {
      labels: grupos.map((g) => g.nombre),
      datasets: [{ data: grupos.map((g) => g.clientes), backgroundColor: PALETA }],
    };
  });

  protected readonly graficoSiluetas = computed<ChartConfiguration<'bar'>['data'] | null>(() => {
    const s = this.segmentos();
    if (!s) return null;
    return {
      labels: s.metricas.siluetas.map((x) => `k = ${x.k}`),
      datasets: [
        {
          label: 'Coeficiente de silueta',
          data: s.metricas.siluetas.map((x) => x.silueta),
          backgroundColor: s.metricas.siluetas.map((x) =>
            x.k === s.metricas.k ? COLORES.malva : COLORES.humo,
          ),
        },
      ],
    };
  });

  protected readonly opcionesLinea: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
    scales: { y: { beginAtZero: true, title: { display: true, text: 'Unidades por semana' } } },
  };
  protected readonly opcionesBarraH: ChartConfiguration<'bar'>['options'] = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true, title: { display: true, text: '% del peso' } } },
  };
  protected readonly opcionesBarra: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, max: 1 } },
  };
  protected readonly opcionesDona: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
  };

  ngOnInit(): void {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.resumen().subscribe({
      next: (r) => {
        this.datos.set(r);
        this.cargando.set(false);
        if (r.entrenado) this.cargarClientes();
      },
      error: (e: ErrorAnalitica) => {
        this.error.set(e);
        this.cargando.set(false);
      },
    });
  }

  /** CU-29: entrena los dos modelos. Tarda unos segundos. */
  protected entrenar(): void {
    if (this.entrenando()) return;
    this.entrenando.set(true);
    this.error.set(null);
    this.api.entrenar().subscribe({
      next: (r) => {
        this.datos.set(r);
        this.entrenando.set(false);
        this.cargarClientes();
      },
      error: (e: ErrorAnalitica) => {
        this.error.set(e);
        this.entrenando.set(false);
      },
    });
  }

  protected descargar(formato: 'pdf' | 'xlsx'): void {
    if (this.descargando()) return;
    this.descargando.set(formato);
    this.api.reporte(formato).subscribe({
      next: (archivo) => {
        const url = URL.createObjectURL(archivo);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `analitica.${formato}`;
        enlace.click();
        // Se libera después: revocarla en el acto puede cortar la descarga.
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        this.descargando.set(null);
      },
      error: (e: ErrorAnalitica) => {
        this.error.set(e);
        this.descargando.set(null);
      },
    });
  }

  private cargarClientes(): void {
    this.api.clientes().subscribe({
      next: (c) => this.clientes.set(c.slice(0, 20)),
      error: () => this.clientes.set([]),
    });
  }

  protected tendencia(t: string): { icono: string; texto: string } {
    if (t === 'SUBE') return { icono: 'trending_up', texto: 'Sube' };
    if (t === 'BAJA') return { icono: 'trending_down', texto: 'Baja' };
    return { icono: 'trending_flat', texto: 'Estable' };
  }

  /** `2026-11-02` → `02/11`, sin pasar por `Date` (que corre el día por UTC). */
  protected fechaCorta(iso: string): string {
    const [, mes, dia] = iso.split('-');
    return `${dia}/${mes}`;
  }

  /** «1 semana», «3 semanas»: el número decide el plural. */
  protected semanas(n: number | null | undefined): string {
    const cantidad = n ?? 0;
    return `${cantidad.toLocaleString('es-BO')} ${cantidad === 1 ? 'semana' : 'semanas'}`;
  }

  /**
   * La predicción es de la semana siguiente AL ENTRENAMIENTO. Si se entrenó
   * hace rato, esa semana ya pudo empezar o pasar: se avisa en vez de
   * mostrarla como si fuera futura.
   */
  protected semanaVencida(iso: string): boolean {
    const hoy = new Date();
    const lunes = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - ((hoy.getDay() + 6) % 7));
    const [anio, mes, dia] = iso.split('-').map(Number);
    return new Date(anio, mes - 1, dia) < lunes;
  }

  protected fechaLarga(iso: string): string {
    const [anio, mes, dia] = iso.split('-');
    return `${dia}/${mes}/${anio}`;
  }
}
