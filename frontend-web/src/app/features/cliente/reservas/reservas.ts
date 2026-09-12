import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
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
import { MatToolbarModule } from '@angular/material/toolbar';
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
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { ReservaFormulario } from './reserva-formulario';

/** Cómo se explica cada estado al cliente, que no leyó el diagrama. */
const LEYENDA: Record<EstadoReserva, string> = {
  PENDIENTE: 'Te esperamos en la sucursal',
  PREPARADA: 'Ya tenemos tus prendas separadas',
  ATENDIDA: 'Ya pasaste a probártelas',
  CANCELADA: 'La cancelaste',
  EXPIRADA: 'Venció sin que pasaras',
};

/**
 * CU-22 y CU-23 · Mis reservas — «boundary» PantallaReservas.
 *
 * **Las vivas arriba y en tarjetas; las cerradas abajo y en tabla.** No es
 * decoración: son dos preguntas distintas. «¿Cuándo tengo que ir y qué reservé?»
 * necesita ver la franja, la sucursal y las prendas de un vistazo, y es sobre lo
 * único que el cliente puede actuar —cancelar—. «¿Qué reservé el mes pasado?» es
 * historial y se lee en lista.
 *
 * Tiene barra propia y no un *layout* compartido porque el área de cliente
 * todavía no tiene uno: la pantalla de perfil (CU-04) declara la suya igual.
 * Cuando el Ciclo 3 agregue carrito e historial de compras va a valer la pena
 * extraerlo; hoy serían dos pantallas compartiendo un componente.
 */
@Component({
  selector: 'app-reservas',
  imports: [
    DatePipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatToolbarModule,
    MatTooltipModule,
  ],
  templateUrl: './reservas.html',
  styleUrl: './reservas.scss',
})
export class Reservas implements OnInit {
  private readonly api = inject(ReservasService);
  private readonly auth = inject(AuthService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly usuario = this.auth.usuario;

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly vivas = signal<ReservaResumen[]>([]);
  protected readonly cerradas = signal<PaginaReservas | null>(null);

  /** Detalle desplegado, o null. Se pide al abrir, no con el listado. */
  protected readonly abierta = signal<Reserva | null>(null);
  protected readonly cargandoDetalle = signal(false);

  protected readonly filtroCerradas = new FormControl<EstadoReserva | ''>('', {
    nonNullable: true,
  });

  private indice = 0;
  private readonly tamano = 10;

  protected readonly iniciales = computed(() => {
    const u = this.usuario();
    if (!u) return '';
    return `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase();
  });

  ngOnInit(): void {
    this.refrescar();
    this.filtroCerradas.valueChanges.subscribe(() => {
      this.indice = 0;
      this.cargarCerradas();
    });
  }

  protected refrescar(): void {
    this.cargando.set(true);
    this.api.misReservas({ vivas: true, tamano: 50 }).subscribe({
      next: (p) => {
        this.vivas.set(p.items);
        this.error.set(null);
        this.cargando.set(false);
      },
      error: (e: ErrorReservas) => {
        this.vivas.set([]);
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
    this.cargarCerradas();
  }

  private cargarCerradas(): void {
    const estado = this.filtroCerradas.value;
    this.api
      .misReservas({
        // Con un estado concreto se filtra por él; sin estado, por «no vivas».
        ...(estado ? { estado } : { vivas: false }),
        pagina: this.indice + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => this.cerradas.set(p),
        error: (e: ErrorReservas) => this.error.set(e.mensaje),
      });
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.cargarCerradas();
  }

  // --- Detalle --------------------------------------------------------------

  /**
   * Despliega el detalle de una reserva, o lo pliega si ya estaba abierta.
   *
   * Las prendas se piden al desplegar y no junto con el listado: el listado trae
   * el recuento —«3 prendas»— que es lo que se muestra, y traer el detalle de
   * todas para abrir una sola sería pedir el historial entero.
   */
  protected alternarDetalle(reserva: ReservaResumen): void {
    if (this.abierta()?.id === reserva.id) {
      this.abierta.set(null);
      return;
    }
    this.abierta.set(null);
    this.cargandoDetalle.set(true);
    this.api.obtener(reserva.id).subscribe({
      next: (r) => {
        this.abierta.set(r);
        this.cargandoDetalle.set(false);
      },
      error: (e: ErrorReservas) => {
        this.cargandoDetalle.set(false);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 });
      },
    });
  }

  protected estaAbierta(reserva: ReservaResumen): boolean {
    return this.abierta()?.id === reserva.id;
  }

  // --- Acciones -------------------------------------------------------------

  protected nueva(): void {
    this.dialogo
      .open(ReservaFormulario, { width: '900px', disableClose: true })
      .afterClosed()
      .subscribe((reserva: Reserva | null) => {
        if (!reserva) return;
        this.aviso.open(
          `Reserva confirmada en ${reserva.sucursal}. Te esperamos.`,
          'Cerrar',
          { duration: 7000 },
        );
        this.refrescar();
      });
  }

  protected cancelar(reserva: ReservaResumen): void {
    const datos: DatosConfirmacion = {
      titulo: '¿Cancelar esta reserva?',
      mensaje:
        `Las prendas que apartamos para vos en ${reserva.sucursal} vuelven a ` +
        'estar disponibles para otros clientes. Esta acción no se puede deshacer.',
      confirmar: 'Sí, cancelar',
      peligrosa: true,
    };
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px' })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.api.cancelar(reserva.id).subscribe({
          next: () => {
            this.aviso.open('Reserva cancelada.', 'Cerrar', { duration: 5000 });
            this.abierta.set(null);
            this.refrescar();
          },
          error: (e: ErrorReservas) => {
            // `estado-final` casi siempre significa que la pantalla está vieja
            // —la atendieron o expiró mientras miraba—, así que además de
            // avisar se refresca: reintentar no va a servir.
            this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 });
            if (e.tipo === 'estado-final') this.refrescar();
          },
        });
      });
  }

  protected salir(): void {
    // `cerrarSesion` ya navega a /login, gane o falle la llamada.
    this.auth.cerrarSesion();
  }

  // --- Presentación ---------------------------------------------------------

  protected leyenda(estado: EstadoReserva): string {
    return LEYENDA[estado] ?? estado;
  }

  protected claseDeEstado(estado: EstadoReserva): string {
    return `estado-${estado.toLowerCase()}`;
  }
}
