import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';

import { AuthService } from '../../core/services/auth.service';
import { NavegacionCliente } from '../../shared/navegacion-cliente/navegacion-cliente';
import {
  Notificacion,
  NotificacionesService,
  iconoDe,
} from '../../core/services/notificaciones.service';

/**
 * CU-40 · Mis avisos.
 *
 * Una sola pantalla para los cuatro roles que reciben algo. No se hizo una por
 * área —una del Encargado y otra del Cliente— porque el contenido es idéntico
 * y el ámbito no lo decide la pantalla: el servidor devuelve los avisos del
 * usuario del token y de nadie más.
 *
 * **El bloque de despacho solo lo ve el Administrador.** No es una pantalla
 * distinta por el mismo motivo de arriba, y esconderlo en el cliente no es la
 * seguridad: el servidor exige el rol en los dos endpoints. Acá se esconde
 * para no ofrecer un botón que va a responder 403.
 */
@Component({
  selector: 'app-avisos',
  imports: [
    DatePipe,
    NavegacionCliente,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatPaginatorModule,
    MatSlideToggleModule,
  ],
  templateUrl: './avisos.html',
  styleUrl: './avisos.scss',
})
export class Avisos implements OnInit {
  private readonly servicio = inject(NotificacionesService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly aviso = inject(MatSnackBar);

  protected readonly icono = iconoDe;

  protected readonly items = signal<Notificacion[]>([]);
  protected readonly total = signal(0);
  protected readonly noLeidas = this.servicio.noLeidas;
  protected readonly cargando = signal(false);
  protected readonly despachando = signal(false);

  protected readonly pagina = signal(1);
  protected readonly tamano = signal(20);
  protected readonly soloNoLeidas = signal(false);

  protected readonly esAdministrador = computed(
    () => this.auth.rol() === 'ADMINISTRADOR',
  );

  /** Para el paginador, que cuenta desde cero y acá se cuenta desde uno. */
  protected readonly indicePagina = computed(() => this.pagina() - 1);

  ngOnInit(): void {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.servicio
      .listar({
        soloNoLeidas: this.soloNoLeidas(),
        pagina: this.pagina(),
        tamano: this.tamano(),
      })
      .subscribe({
        next: (p) => {
          this.items.set(p.items);
          this.total.set(p.total);
          this.cargando.set(false);
        },
        error: () => {
          this.cargando.set(false);
          this.aviso.open('No se pudieron cargar los avisos.', 'Cerrar', {
            duration: 4000,
          });
        },
      });
  }

  protected cambiarPagina(evento: PageEvent): void {
    this.pagina.set(evento.pageIndex + 1);
    this.tamano.set(evento.pageSize);
    this.cargar();
  }

  protected cambiarFiltro(soloNoLeidas: boolean): void {
    this.soloNoLeidas.set(soloNoLeidas);
    // Vuelve a la primera hoja: quedarse en la cuarta después de filtrar deja
    // la pantalla vacía y parece que no hay nada.
    this.pagina.set(1);
    this.cargar();
  }

  protected entrar(item: Notificacion): void {
    if (!item.leida_en) {
      this.servicio.marcarLeida(item.id).subscribe({ error: () => undefined });
    }
    if (item.enlace) {
      this.router.navigateByUrl(item.enlace);
    }
  }

  protected marcarLeida(item: Notificacion, evento: Event): void {
    // Para que marcar no abra el aviso: son dos acciones distintas y el botón
    // está dentro de la tarjeta que navega.
    evento.stopPropagation();
    this.servicio.marcarLeida(item.id).subscribe({
      next: () => this.cargar(),
      error: () => undefined,
    });
  }

  protected marcarTodas(): void {
    this.servicio.marcarTodasLeidas().subscribe({
      next: (r) => {
        this.aviso.open(`${r.marcadas} avisos marcados como leídos.`, 'Cerrar', {
          duration: 3000,
        });
        this.cargar();
      },
      error: () => undefined,
    });
  }

  /** CU-40 · dispara el envío de los correos pendientes. Solo Administrador. */
  protected despachar(): void {
    this.despachando.set(true);
    this.servicio.despachar().subscribe({
      next: (r) => {
        this.despachando.set(false);
        this.aviso.open(
          `Intentados ${r.intentadas}: ${r.enviadas} enviados, ${r.fallidas} fallidos.`,
          'Cerrar',
          { duration: 6000 },
        );
        this.cargar();
      },
      error: () => {
        this.despachando.set(false);
        this.aviso.open('No se pudo despachar.', 'Cerrar', { duration: 4000 });
      },
    });
  }

  protected reintentar(): void {
    this.servicio.reintentar().subscribe({
      next: (r) => {
        this.aviso.open(`${r.encolados} avisos vuelven a la cola.`, 'Cerrar', {
          duration: 4000,
        });
        this.cargar();
      },
      error: () => undefined,
    });
  }
}
