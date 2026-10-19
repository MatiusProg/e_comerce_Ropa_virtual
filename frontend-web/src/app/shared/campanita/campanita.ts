import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';

import { AuthService } from '../../core/services/auth.service';
import {
  Notificacion,
  NotificacionesService,
  iconoDe,
} from '../../core/services/notificaciones.service';

/**
 * CU-40 · La campanita del encabezado.
 *
 * Va en las cáscaras de las áreas cuyos usuarios reciben avisos —la del
 * Cliente y la del Encargado de Sucursal— y también en la de administración,
 * desde donde se llega a la pantalla completa y al despacho de correos.
 *
 * **EL CONTADOR VIVE EN EL SERVICIO, NO ACÁ.** Hay una campanita por cáscara y
 * tres contadores independientes mostrarían números distintos en la misma
 * sesión. El servicio lo mantiene y todas leen el mismo.
 *
 * **Abrir el menú NO marca nada como leído.** Leer es una acción de la persona,
 * no un efecto de pasar el mouse: si abrir vaciara la campanita, un clic por
 * error borraría el único rastro de que algo pedía atención. Se marca al entrar
 * al aviso o con «marcar todas».
 */
@Component({
  selector: 'app-campanita',
  imports: [
    RouterLink,
    MatBadgeModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
  ],
  templateUrl: './campanita.html',
  styleUrl: './campanita.scss',
})
export class Campanita implements OnInit {
  private readonly servicio = inject(NotificacionesService);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  /**
   * A dónde lleva «ver todos», según el rol.
   *
   * Es la MISMA pantalla en las tres: cuelga de cada cáscara para que quien
   * entra desde su campanita no se quede sin navegación. El Cliente no tiene
   * cáscara —su barra viaja como componente— así que usa la ruta suelta.
   */
  protected readonly enlaceTodos = computed(() => {
    switch (this.auth.rol()) {
      case 'ADMINISTRADOR':
        return '/admin/avisos';
      case 'ENCARGADO':
        return '/sucursal/avisos';
      default:
        return '/avisos';
    }
  });

  protected readonly globito = this.servicio.globito;
  protected readonly recientes = signal<Notificacion[]>([]);
  protected readonly cargando = signal(false);
  protected readonly icono = iconoDe;

  ngOnInit(): void {
    // Solo el contador al arrancar. La lista se pide al abrir el menú: traerla
    // en cada carga de pantalla serían veinte filas que casi nadie despliega.
    this.servicio.refrescarContador().subscribe({ error: () => undefined });
  }

  protected abrir(): void {
    this.cargando.set(true);
    this.servicio.listar({ tamano: 6 }).subscribe({
      next: (pagina) => {
        this.recientes.set(pagina.items);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }

  /**
   * Marca el aviso y va a donde apunta.
   *
   * La navegación **no espera** a que el servidor confirme la marca: lo que la
   * persona pidió es ir, y hacerla esperar por un detalle de contabilidad
   * volvería lento un clic que debería ser inmediato. Si la marca falla, el
   * aviso sigue sin leer —que es lo correcto— y se vuelve a intentar la próxima.
   */
  protected entrar(aviso: Notificacion): void {
    if (!aviso.leida_en) {
      this.servicio.marcarLeida(aviso.id).subscribe({ error: () => undefined });
    }
    if (aviso.enlace) {
      this.router.navigateByUrl(aviso.enlace);
    }
  }

  protected marcarTodas(): void {
    this.servicio.marcarTodasLeidas().subscribe({
      next: () =>
        this.recientes.update((lista) =>
          lista.map((a) => ({ ...a, leida_en: a.leida_en ?? new Date().toISOString() })),
        ),
      error: () => undefined,
    });
  }
}
