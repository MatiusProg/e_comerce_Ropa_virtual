import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  TemporadasService,
  type ErrorTemporadas,
} from '../../../core/services/temporadas.service';
import type { Coleccion, Temporada } from '../../../core/models/temporadas.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { TemporadaFormulario } from './temporada-formulario';
import { ColeccionFormulario, type DatosColeccion } from './coleccion-formulario';

/**
 * CU-09 · Gestionar temporadas y colecciones — «boundary» PantallaTemporadas.
 *
 * Una sola pantalla con dos pestañas y no dos rutas, porque así está escrito
 * el caso de uso: el paso 1 es «entrar a los maestros del catálogo y elegir
 * Temporadas», y las colecciones son su flujo alternativo 1a. Una colección no
 * existe fuera de una temporada, y tenerlas al lado hace evidente ese orden.
 *
 * Sin paginación, como en el resto de los maestros: una tienda maneja unas
 * pocas temporadas por año.
 */
@Component({
  selector: 'app-temporadas',
  imports: [
    ReactiveFormsModule,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './temporadas.html',
  styleUrl: './temporadas.scss',
})
export class Temporadas implements OnInit {
  private readonly api = inject(TemporadasService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnasTemporada = [
    'temporada',
    'vigencia',
    'colecciones',
    'estado',
    'acciones',
  ];
  protected readonly columnasColeccion = ['coleccion', 'temporada', 'estado', 'acciones'];

  protected readonly cargando = signal(false);
  /** Mensaje del último fallo al listar, o null. Distingue «no se pudo
   *  consultar» de «no hay nada», que en pantalla se confundían. */
  protected readonly error = signal<string | null>(null);
  protected readonly temporadas = signal<Temporada[]>([]);
  protected readonly colecciones = signal<Coleccion[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroEstado = new FormControl<string>('', { nonNullable: true });
  protected readonly filtroTemporada = new FormControl<number | ''>('', { nonNullable: true });

  /** 0 = Temporadas, 1 = Colecciones. Decide qué listado se recarga. */
  protected readonly pestana = signal(0);

  ngOnInit(): void {
    // El debounce evita disparar una consulta por cada tecla.
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.cargar());
    this.filtroEstado.valueChanges.subscribe(() => this.cargar());
    this.filtroTemporada.valueChanges.subscribe(() => this.cargar());
    this.cargar();
  }

  protected cambiarPestana(indice: number): void {
    this.pestana.set(indice);
    // Los filtros son de la pestaña que se deja: se limpian para no arrastrar
    // una búsqueda que no aplica al otro listado.
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.filtroTemporada.setValue('', { emitEvent: false });
    this.cargar();
  }

  /**
   * Recarga lo que hace falta.
   *
   * Las temporadas se piden siempre, aun en la pestaña de colecciones: pueblan
   * el filtro y el selector del formulario de colección.
   */
  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    const estado = this.filtroEstado.value;
    const activa = estado === '' ? undefined : estado === 'activas';
    const enTemporadas = this.pestana() === 0;

    this.api
      .listarTemporadas({
        busqueda: enTemporadas ? this.busqueda.value || undefined : undefined,
        activa: enTemporadas ? activa : undefined,
      })
      .subscribe({
        next: (t) => {
          this.temporadas.set(t);
          if (enTemporadas) this.cargando.set(false);
        },
        error: (e: ErrorTemporadas) => {
          this.cargando.set(false);
          this.error.set(e.mensaje);
          this.mostrar(e.mensaje);
        },
      });

    if (enTemporadas) return;

    const temporadaId = this.filtroTemporada.value;
    this.api
      .listarColecciones({
        busqueda: this.busqueda.value || undefined,
        temporada_id: temporadaId === '' ? undefined : temporadaId,
        activa,
      })
      .subscribe({
        next: (c) => {
          this.colecciones.set(c);
          this.cargando.set(false);
        },
        error: (e: ErrorTemporadas) => {
          this.cargando.set(false);
          this.error.set(e.mensaje);
          this.mostrar(e.mensaje);
        },
      });
  }

  protected limpiarFiltros(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.filtroTemporada.setValue('', { emitEvent: false });
    this.cargar();
  }

  protected get hayFiltros(): boolean {
    return !!(
      this.busqueda.value ||
      this.filtroEstado.value ||
      this.filtroTemporada.value !== ''
    );
  }

  // --- Temporadas --------------------------------------------------------

  protected nuevaTemporada(): void {
    this.abrirTemporada(null);
  }

  /** Flujo alternativo 3a. */
  protected editarTemporada(temporada: Temporada): void {
    this.abrirTemporada(temporada);
  }

  private abrirTemporada(temporada: Temporada | null): void {
    this.dialogo
      .open(TemporadaFormulario, { data: temporada, width: '600px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar(temporada ? 'Temporada actualizada.' : 'Temporada registrada.');
          this.cargar();
        }
      });
  }

  /** Flujo alternativo 3b: cerrar o reabrir. */
  protected cambiarEstadoTemporada(temporada: Temporada): void {
    const cerrando = temporada.activa;
    const datos: DatosConfirmacion = {
      titulo: cerrando ? 'Cerrar la temporada' : 'Reabrir la temporada',
      mensaje: cerrando
        ? `${temporada.nombre} dejará de considerarse temporada vigente. Sus productos siguen siendo consultables, y podrá reabrirla cuando quiera.`
        : `${temporada.nombre} volverá a contar como temporada abierta.`,
      confirmar: cerrando ? 'Cerrar' : 'Reabrir',
      peligrosa: cerrando,
    };

    this.confirmar(datos, () => this.enviarEstado(temporada, !temporada.activa, false));
  }

  private enviarEstado(temporada: Temporada, activa: boolean, confirmado: boolean): void {
    this.api.cambiarEstadoTemporada(temporada.id, activa, confirmado).subscribe({
      next: () => {
        this.mostrar(activa ? 'Temporada reabierta.' : 'Temporada cerrada.');
        this.cargar();
      },
      error: (e: ErrorTemporadas) => {
        // Reabrir puede volver a cruzarla con otra abierta: excepción E2, que
        // advierte y pide confirmación en vez de rechazar.
        if (e.tipo === 'solapamiento') {
          this.confirmar(
            {
              titulo: 'Las fechas se superponen',
              mensaje: `El rango ${e.mensaje}. ¿Desea reabrirla de todos modos?`,
              confirmar: 'Reabrir igual',
              peligrosa: true,
            },
            () => this.enviarEstado(temporada, activa, true),
          );
          return;
        }
        this.mostrar(e.mensaje);
      },
    });
  }

  /** Excepción E3: no se puede eliminar una temporada con colecciones. */
  protected eliminarTemporada(temporada: Temporada): void {
    if (temporada.colecciones > 0) {
      this.mostrar(
        `${temporada.nombre} tiene ${temporada.colecciones} colección(es) y no puede eliminarse. Ciérrela en su lugar.`,
      );
      return;
    }

    this.confirmar(
      {
        titulo: 'Eliminar temporada',
        mensaje: `Se eliminará ${temporada.nombre}. Esta acción no se puede deshacer. Si solo quiere dejar de usarla, ciérrela.`,
        confirmar: 'Eliminar',
        peligrosa: true,
      },
      () =>
        this.api.eliminarTemporada(temporada.id).subscribe({
          next: () => {
            this.mostrar('Temporada eliminada.');
            this.cargar();
          },
          // El servidor vuelve a comprobarlo: entre que se pintó la fila y
          // este clic pudo crearse una colección.
          error: (e: ErrorTemporadas) => this.mostrar(e.mensaje),
        }),
    );
  }

  // --- Colecciones (flujo alternativo 1a) --------------------------------

  protected nuevaColeccion(): void {
    if (!this.temporadas().length) {
      // Sin temporada no hay dónde poner la colección: se dice por qué en vez
      // de abrir un formulario con el selector vacío.
      this.mostrar('Registre primero una temporada para poder crear colecciones.');
      return;
    }
    const filtro = this.filtroTemporada.value;
    this.abrirColeccion({
      temporadas: this.temporadas(),
      coleccion: null,
      temporadaId: filtro === '' ? null : filtro,
    });
  }

  protected editarColeccion(coleccion: Coleccion): void {
    this.abrirColeccion({ temporadas: this.temporadas(), coleccion });
  }

  private abrirColeccion(datos: DatosColeccion): void {
    this.dialogo
      .open(ColeccionFormulario, { data: datos, width: '560px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar(datos.coleccion ? 'Colección actualizada.' : 'Colección registrada.');
          this.cargar();
        }
      });
  }

  protected cambiarEstadoColeccion(coleccion: Coleccion): void {
    const dandoDeBaja = coleccion.activa;
    this.confirmar(
      {
        titulo: dandoDeBaja ? 'Dar de baja la colección' : 'Reactivar la colección',
        mensaje: dandoDeBaja
          ? `${coleccion.nombre} dejará de ofrecerse para asociar productos. Se conserva para la trazabilidad histórica.`
          : `${coleccion.nombre} volverá a estar disponible.`,
        confirmar: dandoDeBaja ? 'Dar de baja' : 'Reactivar',
        peligrosa: dandoDeBaja,
      },
      () =>
        this.api.cambiarEstadoColeccion(coleccion.id, !coleccion.activa).subscribe({
          next: () => {
            this.mostrar(dandoDeBaja ? 'Colección dada de baja.' : 'Colección reactivada.');
            this.cargar();
          },
          error: (e: ErrorTemporadas) => this.mostrar(e.mensaje),
        }),
    );
  }

  // --- Utilidades --------------------------------------------------------

  private confirmar(datos: DatosConfirmacion, accion: () => void): void {
    this.dialogo
      .open(Confirmacion, { data: datos, width: '480px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => si && accion());
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 6000 });
  }
}
