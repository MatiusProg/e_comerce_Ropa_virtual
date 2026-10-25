import { DatePipe, LowerCasePipe, NgTemplateOutlet } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import type { LimitePlan, MiPlan as DatosMiPlan, Plan } from '../../../core/models/mi-plan.models';
import { MiPlanService, type ErrorMiPlan } from '../../../core/services/mi-plan.service';
import { BsPipe } from '../../../shared/bs.pipe';

const ESTADOS: Record<string, string> = {
  VIGENTE: 'Vigente',
  SUSPENDIDA: 'Suspendida',
  VENCIDA: 'Vencida',
  REEMPLAZADA: 'Reemplazada',
};

type CodigoLimite = 'sucursales' | 'empleados' | 'reportes_ia' | 'fotos_ia';

/**
 * CU-04 · Consultar plan y consumo — «boundary» PantallaMiPlan.
 *
 * El administrador de la empresa ve su plan, el estado de la suscripción, cuánto
 * usó de cada límite y qué funciones trae. No modifica nada: cambiar de plan es
 * del administrador de la plataforma (CU-03) o de la contratación (CU-11).
 *
 * **Un cupo con `usado` null no se dibuja como 0.** Los reportes y las fotos con
 * IA se cuentan desde los casos de uso que los gastan; mientras no midan, la
 * pantalla dice «sin medir aún» en vez de una barra vacía que parecería real.
 */
@Component({
  selector: 'app-mi-plan',
  imports: [
    BsPipe,
    DatePipe,
    LowerCasePipe,
    NgTemplateOutlet,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
  ],
  templateUrl: './mi-plan.html',
  styleUrl: './mi-plan.scss',
})
export class MiPlan implements OnInit {
  private readonly servicio = inject(MiPlanService);

  protected readonly datos = signal<DatosMiPlan | null>(null);
  protected readonly cargando = signal(true);
  protected readonly error = signal<ErrorMiPlan | null>(null);
  /** Paso 4: la comparación se abre a pedido, para no tapar el consumo. */
  protected readonly comparando = signal(false);

  /** El plan actual primero y después los demás, por precio. */
  protected readonly planesComparados = computed<Plan[]>(() => {
    const d = this.datos();
    if (!d) return [];
    const otros = [...d.otros_planes].sort((a, b) => +a.precio_mensual - +b.precio_mensual);
    return d.plan ? [d.plan, ...otros] : otros;
  });

  /** Las filas de la comparación: la unión de las funciones de todos los planes. */
  protected readonly filasComparacion = computed(() => {
    const vistas = new Map<string, string>();
    for (const p of this.planesComparados()) {
      for (const f of p.funciones) if (!vistas.has(f.codigo)) vistas.set(f.codigo, f.etiqueta);
    }
    return [...vistas].map(([codigo, etiqueta]) => ({ codigo, etiqueta }));
  });

  protected readonly filasLimites: { codigo: CodigoLimite; etiqueta: string }[] = [
    { codigo: 'sucursales', etiqueta: 'Sucursales activas' },
    { codigo: 'empleados', etiqueta: 'Empleados activos' },
    { codigo: 'reportes_ia', etiqueta: 'Reportes con IA por mes' },
    { codigo: 'fotos_ia', etiqueta: 'Fotos con IA por mes' },
  ];

  ngOnInit(): void {
    this.consultar();
  }

  protected consultar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.servicio.consultar().subscribe({
      next: (d) => {
        this.datos.set(d);
        this.cargando.set(false);
      },
      error: (e: ErrorMiPlan) => {
        this.error.set(e);
        this.cargando.set(false);
      },
    });
  }

  protected estado(codigo: string): string {
    return ESTADOS[codigo] ?? codigo;
  }

  protected porcentaje(l: LimitePlan): number {
    if (l.usado === null || l.limite === null || l.limite === 0) return 0;
    return Math.min(100, Math.round((l.usado / l.limite) * 100));
  }

  /** El texto de un límite en la barra: «2 de 10», «Ilimitado», «sin medir aún». */
  protected textoLimite(l: LimitePlan): string {
    if (l.limite === 0) return 'No incluido';
    if (l.usado === null) {
      return `${l.limite === null ? 'Ilimitado' : 'Hasta ' + l.limite} · sin medir aún`;
    }
    if (l.limite === null) return `${l.usado} · ilimitado`;
    return `${l.usado} de ${l.limite}`;
  }

  protected limiteDe(p: Plan, codigo: CodigoLimite): string {
    const valor = {
      sucursales: p.max_sucursales,
      empleados: p.max_empleados,
      reportes_ia: p.cupo_reportes_ia,
      fotos_ia: p.cupo_fotos_ia,
    }[codigo];
    if (valor === null) return 'Ilimitado';
    if (valor === 0) return 'No incluye';
    return `Hasta ${valor}`;
  }

  protected funcionDe(p: Plan, codigo: string): string {
    const f = p.funciones.find((x) => x.codigo === codigo);
    if (!f || !f.incluida) return '—';
    return f.detalle ?? 'Sí';
  }
}
