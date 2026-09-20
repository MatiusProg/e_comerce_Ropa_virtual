import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, type PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  PromocionesService,
  type ErrorPromociones,
} from '../../../core/services/promociones.service';
import type { Alcance, Promocion } from '../../../core/models/promociones.models';
import { PromocionFormulario, type DatosPromocion } from './promocion-formulario';

/**
 * CU-12 · Gestionar promociones — «boundary» PantallaPromociones.
 *
 * LO QUE ESTA PANTALLA TIENE QUE DEJAR CLARO
 * -------------------------------------------
 * **«Activa» y «vigente» no son lo mismo**, y confundirlas es la forma más
 * fácil de creer que el sistema está roto. Una promoción activa que empieza el
 * mes que viene no está descontando nada; una vencida tampoco, aunque siga
 * encendida. La fila dice las dos cosas: el interruptor es `activa` —lo que el
 * Administrador controla— y la etiqueta es `vigente` —lo que hoy pasa—.
 *
 * **No hay borrado.** Una promoción se apaga. Las ventas ya cobradas con ella
 * la nombran en su historial, y volver a encenderla la temporada que viene es
 * lo normal. Ofrecer un botón de borrar invitaría a romper esa explicación.
 */
@Component({
  selector: 'app-promociones',
  imports: [
    DatePipe,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSlideToggleModule,
    MatTooltipModule,
  ],
  templateUrl: './promociones.html',
  styleUrl: './promociones.scss',
})
export class Promociones implements OnInit {
  private readonly api = inject(PromocionesService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly promociones = signal<Promocion[]>([]);

  protected readonly total = signal(0);
  protected readonly pagina = signal(1);
  protected readonly tamano = signal(20);

  protected readonly filtroAlcance = signal<Alcance | null>(null);
  protected readonly soloVigentes = signal(false);

  /** Cuántas están descontando ahora mismo. Es el número que importa. */
  protected readonly vigentes = computed(
    () => this.promociones().filter((p) => p.vigente).length,
  );

  ngOnInit(): void {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api
      .listar(this.pagina(), this.tamano(), this.filtroAlcance(), this.soloVigentes())
      .subscribe({
        next: (p) => {
          this.promociones.set(p.items);
          this.total.set(p.total);
          this.cargando.set(false);
        },
        error: (e: ErrorPromociones) => {
          this.error.set(e.mensaje);
          this.cargando.set(false);
        },
      });
  }

  protected paginar(evento: PageEvent): void {
    this.pagina.set(evento.pageIndex + 1);
    this.tamano.set(evento.pageSize);
    this.cargar();
  }

  protected filtrarPorAlcance(alcance: Alcance | null): void {
    this.filtroAlcance.set(alcance);
    this.pagina.set(1);
    this.cargar();
  }

  protected alternarVigentes(): void {
    this.soloVigentes.set(!this.soloVigentes());
    this.pagina.set(1);
    this.cargar();
  }

  protected nueva(): void {
    this.abrir(null);
  }

  protected editar(promocion: Promocion): void {
    this.abrir(promocion);
  }

  private abrir(promocion: Promocion | null): void {
    const datos: DatosPromocion = { promocion };
    this.dialogo
      .open(PromocionFormulario, { data: datos, autoFocus: 'first-tabbable' })
      .afterClosed()
      .subscribe((resultado) => {
        if (!resultado) return;

        const peticion = promocion
          ? this.api.editar(promocion.id, resultado)
          : this.api.crear(resultado);

        peticion.subscribe({
          next: () => {
            this.aviso.open(
              promocion ? 'Promoción actualizada.' : 'Promoción creada.',
              'Listo',
              { duration: 4000 },
            );
            this.cargar();
          },
          error: (e: ErrorPromociones) => {
            this.aviso.open(e.mensaje, 'Entendido', { duration: 7000 });
            // Si el objetivo dejó de existir, la lista del formulario estaba
            // vieja: se recarga para no ofrecerlo de nuevo.
            if (e.tipo === 'objetivo-inexistente' || e.tipo === 'no-existe') {
              this.cargar();
            }
          },
        });
      });
  }

  protected cambiarEstado(promocion: Promocion, activa: boolean): void {
    this.api.cambiarEstado(promocion.id, activa).subscribe({
      next: (actualizada) => {
        this.promociones.set(
          this.promociones().map((p) => (p.id === actualizada.id ? actualizada : p)),
        );
        // Si se está filtrando por vigentes, apagar una la saca de la lista:
        // dejarla ahí diría que sigue descontando.
        if (this.soloVigentes()) this.cargar();
      },
      error: (e: ErrorPromociones) => {
        this.aviso.open(e.mensaje, 'Entendido', { duration: 7000 });
        this.cargar();
      },
    });
  }

  protected iconoDe(alcance: Alcance): string {
    if (alcance === 'PRODUCTO') return 'checkroom';
    return alcance === 'CATEGORIA' ? 'category' : 'wb_sunny';
  }

  protected nombreDe(alcance: Alcance): string {
    if (alcance === 'PRODUCTO') return 'Producto';
    return alcance === 'CATEGORIA' ? 'Categoría' : 'Temporada';
  }

  /**
   * Por qué una promoción encendida no está descontando.
   *
   * Sin esto, el Administrador ve el interruptor en «sí» y la etiqueta en «no»
   * y no tiene forma de saber cuál de los dos motivos es.
   */
  protected porQueNoDescuenta(p: Promocion): string {
    if (!p.activa) return 'Está apagada.';
    const hoy = this.hoyTexto();
    if (p.desde > hoy) return `Empieza el ${this.legible(p.desde)}.`;
    if (p.hasta && p.hasta < hoy) return `Terminó el ${this.legible(p.hasta)}.`;
    return '';
  }

  /** El día de hoy como `AAAA-MM-DD` local, para comparar con las del servidor. */
  private hoyTexto(): string {
    const d = new Date();
    return `${d.getFullYear()}-${`${d.getMonth() + 1}`.padStart(2, '0')}-${`${d.getDate()}`.padStart(2, '0')}`;
  }

  private legible(fecha: string): string {
    const [a, m, d] = fecha.split('-');
    return `${d}/${m}/${a}`;
  }
}
