import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import type {
  Anomalia,
  GrupoAnomalia,
  ResultadoAnomalias,
} from '../../../../core/models/analitica.models';
import {
  AnaliticaService,
  type ErrorAnalitica,
} from '../../../../core/services/analitica.service';

/**
 * Aporte propio · Anomalías en caja y devoluciones — «boundary» PanelAnomalias.
 *
 * Va dentro del dashboard analítico (CU-30). Un botón busca las anomalías con
 * Isolation Forest sobre los turnos cerrados y las devoluciones del último año;
 * cada fila marcada trae su puntaje y POR QUÉ es rara, y el administrador la
 * puede dar por revisada.
 */
@Component({
  selector: 'app-anomalias-panel',
  imports: [
    DatePipe,
    DecimalPipe,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './anomalias-panel.html',
  styleUrl: './anomalias-panel.scss',
})
export class AnomaliasPanel implements OnInit {
  private readonly api = inject(AnaliticaService);

  protected readonly datos = signal<ResultadoAnomalias | null>(null);
  protected readonly buscando = signal(false);
  protected readonly revisando = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  protected readonly grupos: { clave: GrupoAnomalia; titulo: string }[] = [
    { clave: 'turnos', titulo: 'Turnos de caja' },
    { clave: 'devoluciones', titulo: 'Devoluciones' },
  ];

  ngOnInit(): void {
    this.api.anomalias().subscribe({
      next: (r) => this.datos.set(r),
      error: (e: ErrorAnalitica) => this.error.set(e.tipo === 'plan' ? null : e.mensaje),
    });
  }

  protected buscar(): void {
    if (this.buscando()) return;
    this.buscando.set(true);
    this.error.set(null);
    this.api.buscarAnomalias().subscribe({
      next: (r) => {
        this.datos.set(r);
        this.buscando.set(false);
      },
      error: (e: ErrorAnalitica) => {
        this.error.set(e.mensaje);
        this.buscando.set(false);
      },
    });
  }

  protected revisar(grupo: GrupoAnomalia, a: Anomalia): void {
    const clave = `${grupo}:${a.id}`;
    if (this.revisando()) return;
    this.revisando.set(clave);
    this.api.marcarRevisada(grupo, a.id).subscribe({
      next: (r) => {
        this.datos.set(r);
        this.revisando.set(null);
      },
      error: (e: ErrorAnalitica) => {
        this.error.set(e.mensaje);
        this.revisando.set(null);
      },
    });
  }

  /** Puntaje alto (≥ 0,65) en rojo, medio en ámbar. */
  protected nivel(puntaje: number): 'alto' | 'medio' {
    return puntaje >= 0.65 ? 'alto' : 'medio';
  }
}
