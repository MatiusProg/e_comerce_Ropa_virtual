import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../../core/services/auth.service';
import {
  ReservasService,
  type ErrorReservas,
} from '../../../core/services/reservas.service';
import type {
  EstadoReserva,
  PaginaReservas,
  Reserva,
  ReservaResumen,
} from '../../../core/models/reservas.models';
import {
  AtencionFormulario,
  type DatosAtencionFormulario,
} from './atencion-formulario';

/**
 * CU-24 · Reservas de la sucursal — «boundary» PantallaReservasSucursal.
 *
 * **Es una agenda, no un historial**, y por eso la franja más próxima va
 * arriba: el Encargado necesita ver primero lo que tiene que atender antes. Es
 * el orden inverso al de «mis reservas» del Cliente, y el servidor ya devuelve
 * cada listado con el suyo.
 *
 * **Las de hoy se destacan.** En un listado plano, una reserva de dentro de
 * tres días y una de dentro de veinte minutos se leen igual, y solo una de las
 * dos es urgente.
 *
 * El Administrador entra a la misma pantalla con alcance a toda la red, y solo
 * para él aparece el disparador de la expiración (CU-25): es mantenimiento del
 * sistema, no una tarea de sucursal.
 */
@Component({
  selector: 'app-reservas-sucursal',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './reservas-sucursal.html',
  styleUrl: './reservas-sucursal.scss',
})
export class ReservasSucursal implements OnInit {
  private readonly api = inject(ReservasService);
  private readonly auth = inject(AuthService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly esAdministrador = computed(
    () => this.auth.rol() === 'ADMINISTRADOR',
  );

  protected readonly columnas = [
    'franja',
    'cliente',
    'sucursal',
    'prendas',
    'estado',
    'acciones',
  ];

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly pagina = signal<PaginaReservas | null>(null);

  /** Detalle desplegado. Se pide al abrir, no con el listado. */
  protected readonly abierta = signal<Reserva | null>(null);

  protected readonly filtroEstado = new FormControl<EstadoReserva | ''>('', {
    nonNullable: true,
  });
  protected readonly soloVivas = new FormControl(true, { nonNullable: true });

  private indice = 0;
  private readonly tamano = 20;

  ngOnInit(): void {
    this.cargar();
    this.filtroEstado.valueChanges.subscribe(() => {
      this.indice = 0;
      this.cargar();
    });
    this.soloVivas.valueChanges.subscribe(() => {
      this.indice = 0;
      this.cargar();
    });
  }

  protected cargar(): void {
    this.cargando.set(true);
    const estado = this.filtroEstado.value;
    this.api
      .deMiSucursal({
        // El estado concreto manda sobre el interruptor de «solo vivas»: pedir
        // las CANCELADAS y a la vez solo las vivas no devolvería nada, y eso se
        // vería como una pantalla rota.
        ...(estado ? { estado } : { vivas: this.soloVivas.value }),
        pagina: this.indice + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => {
          this.pagina.set(p);
          this.error.set(null);
          this.cargando.set(false);
        },
        error: (e: ErrorReservas) => {
          this.pagina.set(null);
          this.error.set(e.mensaje);
          this.cargando.set(false);
        },
      });
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.cargar();
  }

  // --- Presentación ---------------------------------------------------------

  /** Si la franja empieza hoy. Es lo que hay que atender sin falta. */
  protected esDeHoy(reserva: ReservaResumen): boolean {
    const inicio = new Date(reserva.franja_inicio);
    const hoy = new Date();
    return (
      inicio.getFullYear() === hoy.getFullYear() &&
      inicio.getMonth() === hoy.getMonth() &&
      inicio.getDate() === hoy.getDate()
    );
  }

  protected claseDeEstado(estado: EstadoReserva): string {
    return `estado-${estado.toLowerCase()}`;
  }

  protected estaViva(reserva: ReservaResumen): boolean {
    return reserva.estado === 'PENDIENTE' || reserva.estado === 'PREPARADA';
  }

  // --- Detalle --------------------------------------------------------------

  protected alternarDetalle(reserva: ReservaResumen): void {
    if (this.abierta()?.id === reserva.id) {
      this.abierta.set(null);
      return;
    }
    this.abierta.set(null);
    this.api.obtenerDeSucursal(reserva.id).subscribe({
      next: (r) => this.abierta.set(r),
      error: (e: ErrorReservas) =>
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 }),
    });
  }

  protected estaAbierta(reserva: ReservaResumen): boolean {
    return this.abierta()?.id === reserva.id;
  }

  // --- Acciones -------------------------------------------------------------

  protected preparar(reserva: ReservaResumen): void {
    this.api.preparar(reserva.id).subscribe({
      next: () => {
        this.aviso.open(
          `Reserva #${reserva.id} marcada como preparada.`,
          'Cerrar',
          { duration: 5000 },
        );
        this.cargar();
      },
      error: (e: ErrorReservas) => {
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 });
        // Si el estado ya no admite la operación, la pantalla está vieja: se
        // refresca en vez de dejar al Encargado reintentando.
        if (e.tipo === 'estado-final') this.cargar();
      },
    });
  }

  /**
   * Abre el cierre de la reserva.
   *
   * Hace falta el detalle —las líneas con su identificador— y el listado solo
   * trae el recuento, así que se pide antes de abrir el diálogo. Abrirlo vacío
   * y cargar dentro dejaría un diálogo en blanco parpadeando.
   */
  protected atender(reserva: ReservaResumen): void {
    this.api.obtenerDeSucursal(reserva.id).subscribe({
      next: (completa) => this.abrirAtencion(completa),
      error: (e: ErrorReservas) =>
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 }),
    });
  }

  private abrirAtencion(reserva: Reserva): void {
    const datos: DatosAtencionFormulario = { reserva };
    this.dialogo
      .open(AtencionFormulario, { data: datos, width: '680px', disableClose: true })
      .afterClosed()
      .subscribe((cerrada: Reserva | null) => {
        if (!cerrada) return;
        const llevadas = cerrada.lineas.filter(
          (l) => l.resultado_prueba === 'LLEVA',
        ).length;
        this.aviso.open(
          llevadas
            ? `Reserva cerrada: el cliente se llevó ${llevadas} prenda(s).`
            : 'Reserva cerrada: las prendas volvieron al stock.',
          'Cerrar',
          { duration: 6000 },
        );
        this.abierta.set(null);
        this.cargar();
      });
  }

  /** CU-25, disparado a mano. Solo el Administrador. */
  protected expirarVencidas(): void {
    this.api.expirarVencidas().subscribe({
      next: (resultado) => {
        this.aviso.open(
          resultado.expiradas
            ? `${resultado.expiradas} reserva(s) expiradas, ` +
              `${resultado.unidades_liberadas} unidades devueltas al stock.`
            : 'No había reservas vencidas para expirar.',
          'Cerrar',
          { duration: 7000 },
        );
        this.cargar();
      },
      error: (e: ErrorReservas) =>
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 }),
    });
  }
}
