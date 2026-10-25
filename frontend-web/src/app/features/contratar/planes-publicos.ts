import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import {
  ContratacionService,
  type ErrorContratacion,
} from '../../core/services/contratacion.service';
import type { PlanPublico } from '../../core/models/contratacion.models';
import { BsPipe } from '../../shared/bs.pipe';

/**
 * CU-11 · Contratar un plan desde la web — «boundary» PaginaPlanes (2do parcial).
 *
 * Pasos 1 a 3: los planes que se ofrecen, con su precio, sus límites y sus
 * funciones, y el botón para elegir uno. Pública: la ve cualquiera.
 */
@Component({
  selector: 'app-planes-publicos',
  imports: [BsPipe, RouterLink, MatButtonModule, MatIconModule, MatProgressBarModule],
  templateUrl: './planes-publicos.html',
  styleUrl: './planes-publicos.scss',
})
export class PlanesPublicos implements OnInit {
  private readonly api = inject(ContratacionService);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly planes = signal<PlanPublico[]>([]);

  ngOnInit(): void {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.planes().subscribe({
      next: (p) => {
        this.planes.set(p);
        this.cargando.set(false);
      },
      error: (e: ErrorContratacion) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  /** Con tres planes se destaca el del medio, el que equilibra precio y funciones. */
  protected destacado(indice: number): boolean {
    return this.planes().length === 3 && indice === 1;
  }

  protected limite(valor: number | null, singular: string, plural: string, sinLimite: string): string {
    if (valor === null) return sinLimite;
    return `Hasta ${valor} ${valor === 1 ? singular : plural}`;
  }

  protected cupo(valor: number | null, nombre: string): string | null {
    if (valor === 0) return null;
    if (valor === null) return `${nombre[0].toUpperCase()}${nombre.slice(1)} ilimitados`;
    return `${valor} ${nombre} al mes`;
  }
}
