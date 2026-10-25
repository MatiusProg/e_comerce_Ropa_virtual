import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import {
  MAT_DIALOG_DATA,
  MatDialog,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  PlataformaService,
  type ErrorPlataforma,
} from '../../../core/services/plataforma.service';
import type { FuncionDePlan, Plan, PlanGuardado } from '../../../core/models/plataforma.models';
import { BsPipe } from '../../../shared/bs.pipe';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { PlanFormulario, type DatosPlan } from './plan-formulario';

/**
 * Alternativo 5a: el plan quedó guardado, pero estas empresas ya tienen más de
 * lo que permite. No se les borra nada; solo no pueden crear más (RN-04).
 */
@Component({
  selector: 'app-plan-excedidas',
  imports: [MatButtonModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title class="vb-titulo">Plan guardado</h2>
    <mat-dialog-content>
      <p>
        Estas empresas del plan <strong>{{ plan.nombre }}</strong> ya tienen más de lo que el
        nuevo límite permite. Conservan todo lo que tienen, pero no podrán crear más hasta
        quedar por debajo del límite o cambiar de plan.
      </p>
      <ul>
        @for (e of plan.excedidas; track e.empresa + e.recurso) {
          <li>
            <strong>{{ e.empresa }}</strong>: {{ e.uso }} {{ e.recurso }}, el límite es
            {{ e.limite }}.
          </li>
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
export class PlanExcedidasDialogo {
  protected readonly ref = inject(MatDialogRef<PlanExcedidasDialogo>);
  protected readonly plan = inject<PlanGuardado>(MAT_DIALOG_DATA);
}

/**
 * CU-02 · Gestionar planes — «boundary» PantallaPlanes (2do parcial).
 *
 * Paso 2: cada plan con su precio, sus límites, sus funciones y cuántas
 * empresas lo usan. Desde acá se crea, se edita y se desactiva (3a). Solo la
 * ve el administrador de la plataforma.
 */
@Component({
  selector: 'app-planes',
  imports: [
    BsPipe,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatMenuModule,
    MatProgressBarModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './planes.html',
  styleUrls: ['../empresas/empresas.scss', './planes.scss'],
})
export class Planes implements OnInit {
  private readonly api = inject(PlataformaService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = ['plan', 'precio', 'limites', 'ia', 'funciones', 'empresas', 'estado', 'acciones'];

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly planes = signal<Plan[]>([]);
  private readonly funciones = signal<FuncionDePlan[]>([]);

  /** Clave → nombre, para el detalle de las funciones de cada fila. */
  private readonly nombres = computed(
    () => new Map(this.funciones().map((f) => [f.clave, f.nombre])),
  );

  ngOnInit(): void {
    this.api.funcionesDePlan().subscribe({ next: (f) => this.funciones.set(f) });
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.listarPlanes().subscribe({
      next: (p) => {
        this.planes.set(p);
        this.cargando.set(false);
      },
      error: (e: ErrorPlataforma) => {
        this.cargando.set(false);
        this.error.set(e.mensaje);
      },
    });
  }

  /** «3 sucursales», «Sin límite»: vacío es ilimitado. */
  protected limite(valor: number | null, singular: string, plural: string): string {
    if (valor === null) return `${plural[0].toUpperCase()}${plural.slice(1)} sin límite`;
    return `${valor} ${valor === 1 ? singular : plural}`;
  }

  protected cupo(valor: number | null): string {
    if (valor === null) return 'sin límite';
    return valor === 0 ? 'no incluye' : `${valor} por mes`;
  }

  protected detalleFunciones(plan: Plan): string {
    return plan.funciones.map((f) => this.nombres().get(f) ?? f).join('\n');
  }

  protected nuevo(): void {
    this.abrir({ funciones: this.funciones(), plan: null });
  }

  protected editar(plan: Plan): void {
    this.abrir({ funciones: this.funciones(), plan });
  }

  private abrir(datos: DatosPlan): void {
    if (!datos.funciones.length) {
      this.mostrar('Todavía se están cargando las funciones. Intente de nuevo.');
      return;
    }
    this.dialogo
      .open(PlanFormulario, { data: datos, width: '640px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado: PlanGuardado | null) => {
        if (!guardado) return;
        if (guardado.excedidas.length) {
          this.dialogo.open(PlanExcedidasDialogo, { data: guardado, width: '520px', maxWidth: '95vw' });
        } else {
          this.mostrar(datos.plan ? 'Plan actualizado.' : 'Plan creado.');
        }
        this.cargar();
      });
  }

  /** Alternativo 3a: desactivar no le quita el plan a quien ya lo tiene. */
  protected cambiarEstado(plan: Plan): void {
    const desactivando = plan.activo;
    const quienes =
      plan.empresas === 1 ? 'La empresa que lo tiene lo conserva' : `Las ${plan.empresas} empresas que lo tienen lo conservan`;
    const datos: DatosConfirmacion = {
      titulo: desactivando ? 'Dejar de ofrecer el plan' : 'Volver a ofrecer el plan',
      mensaje: desactivando
        ? `${plan.nombre} ya no se podrá elegir en las altas ni en la página de planes. ${
            plan.empresas ? `${quienes} hasta su vencimiento.` : 'Ninguna empresa lo usa hoy.'
          }`
        : `${plan.nombre} vuelve a ofrecerse en las altas y en la página de planes.`,
      confirmar: desactivando ? 'Dejar de ofrecer' : 'Volver a ofrecer',
      peligrosa: desactivando,
    };
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => {
        if (!si) return;
        this.api.cambiarEstadoPlan(plan.id, !desactivando).subscribe({
          next: () => {
            this.mostrar(desactivando ? 'El plan ya no se ofrece.' : 'El plan vuelve a ofrecerse.');
            this.cargar();
          },
          error: (e: ErrorPlataforma) => this.mostrar(e.mensaje),
        });
      });
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 5000 });
  }
}
