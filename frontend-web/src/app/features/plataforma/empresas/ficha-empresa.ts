import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import {
  MAT_DIALOG_DATA,
  MatDialog,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { forkJoin } from 'rxjs';

import {
  PlataformaService,
  type ErrorPlataforma,
} from '../../../core/services/plataforma.service';
import type {
  Empresa,
  EstadoSuscripcion,
  Plan,
  SuscripcionGuardada,
  SuscripcionesEmpresa,
} from '../../../core/models/plataforma.models';
import { BsPipe, formatoBs } from '../../../shared/bs.pipe';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { CambiarPlan, type DatosCambiarPlan } from './cambiar-plan';

/**
 * Alternativo 5a: el plan nuevo es menor que lo que la empresa ya tiene. Se
 * cambió igual; no se borra nada, solo no puede crear más (RN-04).
 */
@Component({
  selector: 'app-suscripcion-excedida',
  imports: [MatButtonModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title class="vb-titulo">Plan cambiado</h2>
    <mat-dialog-content>
      <p>
        {{ datos.empresa }} ya tiene más de lo que permite el plan
        <strong>{{ datos.actual?.plan_nombre }}</strong>. Conserva todo lo que tiene, pero no
        podrá crear más hasta quedar por debajo del límite.
      </p>
      <ul>
        @for (e of datos.excedidas; track e.recurso) {
          <li>{{ e.uso }} {{ e.recurso }}; el límite es {{ e.limite }}.</li>
        }
      </ul>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button matButton="filled" class="vb-boton-marca" type="button" (click)="ref.close()">
        Entendido
      </button>
    </mat-dialog-actions>
  `,
  styles: `ul { line-height: 1.8; }`,
})
export class SuscripcionExcedidaDialogo {
  protected readonly ref = inject(MatDialogRef<SuscripcionExcedidaDialogo>);
  protected readonly datos = inject<SuscripcionGuardada>(MAT_DIALOG_DATA);
}

const ETIQUETAS: Record<EstadoSuscripcion, string> = {
  VIGENTE: 'Vigente',
  SUSPENDIDA: 'Suspendida',
  VENCIDA: 'Vencida',
  REEMPLAZADA: 'Reemplazada',
};

const CONCEPTOS: Record<string, string> = {
  ALTA: 'Alta',
  CAMBIO: 'Cambio de plan',
  RENOVACION: 'Renovación',
};

/**
 * CU-03 · Gestionar suscripciones — «boundary» PantallaSuscripcion (2do parcial).
 *
 * La ficha de la empresa (paso 1): la suscripción actual y el historial
 * (paso 2). Desde acá se asigna o cambia el plan (pasos 3 a 6), se renueva
 * (3a) y se suspende o reactiva (3b). Solo la ve el administrador de la
 * plataforma.
 */
@Component({
  selector: 'app-ficha-empresa',
  imports: [
    BsPipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatProgressBarModule,
    MatTableModule,
  ],
  templateUrl: './ficha-empresa.html',
  styleUrls: ['./empresas.scss', './ficha-empresa.scss'],
})
export class FichaEmpresa implements OnInit {
  private readonly api = inject(PlataformaService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  /** El `:id` de la ruta. */
  readonly id = input.required<string>();
  private readonly empresaId = computed(() => Number(this.id()));

  protected readonly columnasHistorial = ['plan', 'inicio', 'vencimiento', 'estado'];
  protected readonly columnasPagos = ['fecha', 'concepto', 'plan', 'monto', 'comprobante'];

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly empresa = signal<Empresa | null>(null);
  protected readonly datos = signal<SuscripcionesEmpresa | null>(null);
  /** Los que se ofrecen, para cambiar de plan. */
  private planes: Plan[] = [];
  /** Todos: el plan actual de la empresa puede estar desactivado (CU-02, 3a). */
  private todos: Plan[] = [];

  protected readonly actual = computed(() => this.datos()?.actual ?? null);
  /** Hay una suscripción que se puede suspender o reactivar (no vencida ni reemplazada). */
  protected readonly enCurso = computed(() => {
    const a = this.actual();
    return a !== null && (a.estado === 'VIGENTE' || a.estado === 'SUSPENDIDA');
  });
  protected readonly deBaja = computed(() => this.empresa()?.estado === 'BAJA');

  ngOnInit(): void {
    this.api.listarPlanes().subscribe({
      next: (p) => {
        this.todos = p;
        this.planes = p.filter((x) => x.activo);
      },
    });
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    forkJoin({
      empresa: this.api.obtenerEmpresa(this.empresaId()),
      datos: this.api.suscripciones(this.empresaId()),
    }).subscribe({
      next: ({ empresa, datos }) => {
        this.empresa.set(empresa);
        this.datos.set(datos);
        this.cargando.set(false);
      },
      error: (e: ErrorPlataforma) => {
        this.cargando.set(false);
        this.error.set(e.mensaje);
      },
    });
  }

  protected etiqueta(estado: EstadoSuscripcion): string {
    return ETIQUETAS[estado];
  }

  protected concepto(concepto: string): string {
    return CONCEPTOS[concepto] ?? concepto;
  }

  /** Flujo principal, pasos 3 a 6. */
  protected cambiarPlan(): void {
    const datos = this.datos();
    if (!datos) return;
    if (!this.planes.length) {
      this.mostrar('Todavía se están cargando los planes. Intente de nuevo.');
      return;
    }
    const entrada: DatosCambiarPlan = {
      empresaId: datos.empresa_id,
      empresa: datos.empresa,
      planes: this.planes,
      actual: this.enCurso() ? datos.actual : null,
    };
    this.dialogo
      .open(CambiarPlan, { data: entrada, width: '520px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((r: SuscripcionGuardada | null) => {
        if (!r) return;
        this.aplicar(r, `Plan ${r.actual?.plan_nombre} asignado. Pago ${r.pago?.comprobante}.`);
        if (r.excedidas.length) {
          this.dialogo.open(SuscripcionExcedidaDialogo, {
            data: r,
            width: '480px',
            maxWidth: '95vw',
          });
        }
      });
  }

  /** 3a: extiende desde el vencimiento actual (o desde hoy, si ya venció). */
  protected renovar(): void {
    const a = this.actual();
    const plan = this.todos.find((p) => p.id === a?.plan_id);
    const monto = plan ? formatoBs((plan.precio_mensual * plan.duracion_dias) / 30) : null;
    this.confirmar(
      {
        titulo: 'Renovar la suscripción',
        mensaje:
          `Se extiende el plan ${a?.plan_nombre} por ${plan?.duracion_dias ?? 'su'} días más` +
          (a && a.dias_restantes >= 0 ? ', a partir del vencimiento actual' : ', desde hoy') +
          (monto ? `, y se registra un pago simulado de ${monto}.` : '.'),
        confirmar: 'Renovar',
      },
      () => this.ejecutar('renovar', 'Suscripción renovada.'),
    );
  }

  /** 3b: suspendida, la empresa solo consulta (RN-03). */
  protected suspenderOReactivar(): void {
    const suspender = this.actual()?.estado === 'VIGENTE';
    const nombre = this.datos()?.empresa;
    this.confirmar(
      suspender
        ? {
            titulo: 'Suspender la suscripción',
            mensaje: `${nombre} queda en modo solo consulta: sus usuarios entran y ven sus datos, pero no pueden registrar nada nuevo hasta que la reactive.`,
            confirmar: 'Suspender',
            peligrosa: true,
          }
        : {
            titulo: 'Reactivar la suscripción',
            mensaje: `${nombre} vuelve a operar con normalidad. El vencimiento no cambia.`,
            confirmar: 'Reactivar',
          },
      () =>
        this.ejecutar(
          suspender ? 'suspender' : 'reactivar',
          suspender ? 'Suscripción suspendida.' : 'Suscripción reactivada.',
        ),
    );
  }

  private confirmar(datos: DatosConfirmacion, accion: () => void): void {
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => si && accion());
  }

  private ejecutar(accion: 'renovar' | 'suspender' | 'reactivar', exito: string): void {
    this.cargando.set(true);
    this.api.accionSuscripcion(this.empresaId(), accion).subscribe({
      next: (r) => this.aplicar(r, exito),
      error: (e: ErrorPlataforma) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  private aplicar(r: SuscripcionGuardada, mensaje: string): void {
    this.datos.set(r);
    this.cargando.set(false);
    this.mostrar(mensaje);
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 5000 });
  }
}
