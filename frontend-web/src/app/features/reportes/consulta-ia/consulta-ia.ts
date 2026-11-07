import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import type { ChartConfiguration, ChartType } from 'chart.js';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';

import { DictadoService } from '../../../core/services/dictado.service';
import {
  ReportesService,
  type ErrorReportes,
  type ResultadoReporteIa,
} from '../../../core/services/reportes.service';

/**
 * CU-27 · Generar reporte con IA por texto o voz.
 *
 * El usuario escribe o dicta lo que quiere ver; el servidor lo traduce a una
 * especificación (medida, agrupación, filtros, período), la valida contra una
 * lista blanca y la ejecuta sobre los datos de SU empresa. Acá se muestra qué
 * se entendió, la tabla, el gráfico y una lectura en castellano, y se puede
 * exportar a PDF o Excel.
 *
 * Chart.js se registra en el componente, igual que en el tablero, para que el
 * motor de gráficos viaje solo en este trozo diferido.
 */
@Component({
  selector: 'app-consulta-ia',
  imports: [
    ReactiveFormsModule,
    BaseChartDirective,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './consulta-ia.html',
  styleUrl: './consulta-ia.scss',
})
export class ConsultaIa {
  private readonly api = inject(ReportesService);
  private readonly aviso = inject(MatSnackBar);
  protected readonly dictado = inject(DictadoService);

  protected readonly pedido = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(3), Validators.maxLength(500)],
  });

  protected readonly consultando = signal(false);
  protected readonly bajando = signal<'pdf' | 'xlsx' | null>(null);
  protected readonly resultado = signal<ResultadoReporteIa | null>(null);

  protected readonly ejemplos = [
    'Mostrame las ventas de septiembre agrupadas por sucursal',
    '¿Cuáles fueron los diez productos más vendidos este mes?',
    'Generá un gráfico de ventas por semana',
    'Compará las ventas de las sucursales durante los últimos tres meses',
    'Mostrame los productos con menor existencia',
    '¿Qué categorías generaron mayores ingresos este mes?',
    'Devoluciones del mes pasado por producto',
  ];

  private readonly paleta = [
    '#7B4BA8', '#E07A5F', '#3D9970', '#F2A541', '#4A90D9', '#C2416B', '#6C757D', '#2A9D8F', '#999999',
  ];

  protected readonly hayGrafico = computed(() => {
    const g = this.resultado()?.grafico;
    return !!g && g.tipo !== 'tabla' && g.etiquetas.length > 0;
  });

  protected readonly tipoGrafico = computed<ChartType>(() => {
    switch (this.resultado()?.grafico?.tipo) {
      case 'lineas':
        return 'line';
      case 'torta':
        return 'pie';
      default:
        return 'bar';
    }
  });

  protected readonly datosGrafico = computed<ChartConfiguration['data']>(() => {
    const g = this.resultado()?.grafico;
    if (!g) return { labels: [], datasets: [] };
    const torta = g.tipo === 'torta';
    return {
      labels: g.etiquetas,
      datasets: g.series.map((s, i) => ({
        label: s.nombre,
        data: s.datos,
        backgroundColor: torta ? g.etiquetas.map((_, j) => this.color(j)) : this.color(i),
        borderColor: torta ? '#ffffff' : this.color(i),
        tension: 0.25,
        fill: false,
      })),
    };
  });

  protected readonly opcionesGrafico: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
  };

  private color(i: number): string {
    return this.paleta[i % this.paleta.length];
  }

  protected usarEjemplo(frase: string): void {
    this.pedido.setValue(frase);
    this.consultar();
  }

  protected hablar(): void {
    if (this.dictado.escuchando()) {
      this.dictado.detener();
      return;
    }
    this.dictado.escuchar((frase) => {
      this.pedido.setValue(frase);
      this.consultar();
    });
  }

  protected consultar(): void {
    const texto = this.pedido.value.trim();
    if (texto.length < 3 || this.consultando()) {
      this.pedido.markAsTouched();
      return;
    }
    this.consultando.set(true);
    this.api.consultarIa(texto).subscribe({
      next: (r) => {
        this.consultando.set(false);
        this.resultado.set(r);
      },
      error: (e: ErrorReportes) => {
        this.consultando.set(false);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 });
      },
    });
  }

  protected exportar(formato: 'pdf' | 'xlsx'): void {
    const espec = this.resultado()?.especificacion;
    if (!espec || this.bajando()) return;
    this.bajando.set(formato);
    this.api.exportarIa(espec, formato).subscribe({
      next: ({ archivo, nombre }) => {
        this.bajando.set(null);
        const url = URL.createObjectURL(archivo);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombre;
        enlace.click();
        // Se suelta después: revocarlo en el mismo tick puede cortar la descarga.
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      },
      error: (e: ErrorReportes) => {
        this.bajando.set(null);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 });
      },
    });
  }

  protected formatear(valor: string | number, columna: number): string {
    if (typeof valor !== 'number') return String(valor);
    const encabezado = this.resultado()?.encabezados[columna] ?? '';
    const dinero = encabezado.includes('(Bs)');
    return valor.toLocaleString('es-BO', {
      minimumFractionDigits: dinero ? 2 : 0,
      maximumFractionDigits: 2,
    });
  }
}
