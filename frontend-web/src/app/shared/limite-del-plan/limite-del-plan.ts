import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

import type { LimitePlan } from '../../core/models/mi-plan.models';
import { MiPlanService } from '../../core/services/mi-plan.service';

/**
 * 2do parcial · CU-09 y CU-10 — cuánto del límite del plan ya se usó.
 *
 * «2 de 3 sucursales activas», con el enlace a «Mi plan» (CU-04). Lo lee del
 * mismo endpoint del CU-04 para no duplicar el conteo. Es solo información:
 * quien rechaza por encima del límite es el backend (CU-05), y la pantalla
 * muestra ese rechazo si llega.
 *
 * Si el plan no limita el recurso o la consulta falla, no se muestra nada: el
 * aviso no puede trabar la pantalla de la que forma parte.
 */
@Component({
  selector: 'app-limite-del-plan',
  imports: [RouterLink, MatIconModule],
  template: `
    @if (limite(); as l) {
      @if (l.limite !== null) {
        <a
          class="limite"
          [class.alcanzado]="l.alcanzado"
          routerLink="/admin/mi-plan"
          [attr.aria-label]="'Ver mi plan: ' + texto()"
        >
          <mat-icon>{{ l.alcanzado ? 'block' : 'workspace_premium' }}</mat-icon>
          <span>{{ texto() }}</span>
          @if (l.alcanzado) {
            <span class="ver">Ver planes</span>
          }
        </a>
      }
    }
  `,
  styles: `
    .limite {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.3rem 0.75rem;
      border-radius: 999px;
      background: var(--vb-rosa-palido);
      color: var(--vb-malva-oscuro);
      font-size: 0.85rem;
      text-decoration: none;
      white-space: nowrap;

      mat-icon {
        width: 1.1rem;
        height: 1.1rem;
        font-size: 1.1rem;
      }

      &:hover,
      &:focus-visible {
        text-decoration: underline;
      }

      &.alcanzado {
        background: var(--mat-sys-error-container);
        color: var(--mat-sys-on-error-container);
      }

      .ver {
        font-weight: 600;
      }
    }
  `,
})
export class LimiteDelPlan implements OnInit {
  private readonly miPlan = inject(MiPlanService);

  /** El código del límite en el CU-04: `sucursales` o `empleados`. */
  readonly recurso = input.required<'sucursales' | 'empleados'>();

  protected readonly limite = signal<LimitePlan | null>(null);

  /** Si ya se llegó al límite. La pantalla lo usa para avisar antes de abrir el formulario. */
  readonly alcanzado = computed(() => this.limite()?.alcanzado ?? false);

  protected readonly texto = computed(() => {
    const l = this.limite();
    if (!l || l.limite === null) return '';
    const nombre = l.etiqueta.toLowerCase();
    return `${l.usado ?? 0} de ${l.limite} ${nombre}`;
  });

  ngOnInit(): void {
    this.recargar();
  }

  /** Se llama después de un alta, una baja o una reactivación. */
  recargar(): void {
    this.miPlan.consultar().subscribe({
      next: (plan) =>
        this.limite.set(plan.limites.find((l) => l.codigo === this.recurso()) ?? null),
      error: () => this.limite.set(null),
    });
  }

  /** El mensaje para avisar que no se puede crear más, el mismo que daría el backend. */
  mensajeAlcanzado(): string {
    const l = this.limite();
    return l
      ? `Su plan permite hasta ${l.limite} ${l.etiqueta.toLowerCase()} y ya tiene ${l.usado}.`
      : '';
  }
}
