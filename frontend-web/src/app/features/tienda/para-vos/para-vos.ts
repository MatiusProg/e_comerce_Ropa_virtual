import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import { TiendaService, type ErrorTienda } from '../../../core/services/tienda.service';
import type { Recomendaciones } from '../../../core/models/tienda.models';
import { NavegacionCliente } from '../../../shared/navegacion-cliente/navegacion-cliente';

/**
 * CU-33 · Recibir recomendaciones de prendas — «boundary» PantallaParaVos.
 *
 * Realiza el **RF25**: la funcionalidad basada en inteligencia artificial.
 *
 * POR QUÉ ESTA PANTALLA EXISTE
 * -----------------------------
 * Hasta el 19/09 el recomendador solo existía por API: estaba construido,
 * probado y desplegado, y **no había forma de llegar a él desde ninguna
 * interfaz**. Un caso de uso al que no se puede entrar no está hecho.
 *
 * LO QUE HAY QUE ENTENDER PARA TOCAR ESTO
 * ----------------------------------------
 * El servidor **nunca falla por falta de datos ni por el modelo**. Sin talla
 * cargada, sin categorías elegidas, sin historial, sin proveedor de IA o sin
 * cuota, responde igual: las mismas prendas, ordenadas por popularidad y con
 * `motor` en `popularidad`. Por eso acá no hay camino de error para eso — solo
 * para que la red se caiga.
 *
 * De ahí salen las dos reglas de dibujo:
 *
 * 1. **Sin motivo no se dibuja la etiqueta.** Viene vacío cuando ordenó la
 *    popularidad. Poner un texto fijo repetido seis veces se lee como un
 *    error, y le atribuye a la tienda una razón que nadie eligió.
 * 2. **Se dice con qué se generó.** Una sugerencia hecha por un modelo tiene
 *    que poder decir que lo es; presentarla sin distinguir sería atribuirle a
 *    la tienda un criterio que no tomó.
 *
 * La primera visita del día tarda unos segundos porque la hace el modelo; las
 * siguientes doce horas salen de lo guardado. La barra de progreso no es
 * decorativa.
 */
@Component({
  selector: 'app-para-vos',
  imports: [
    NavegacionCliente,
    RouterLink,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './para-vos.html',
  styleUrl: './para-vos.scss',
})
export class ParaVos implements OnInit {
  private readonly api = inject(TiendaService);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly datos = signal<Recomendaciones | null>(null);

  ngOnInit(): void {
    this.traer();
  }

  /**
   * [forzar] vuelve a llamar al modelo aunque lo guardado siga vigente.
   *
   * Está a la vista, en un botón, y es deliberado: **sin esto, mostrar que la
   * recomendación cambia al cargar las medidas o marcar favoritos obligaría a
   * esperar doce horas.** En una defensa eso es no poder mostrarlo.
   */
  protected traer(forzar = false): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.recomendaciones(forzar).subscribe({
      next: (datos) => {
        this.datos.set(datos);
        this.cargando.set(false);
      },
      error: (e: ErrorTienda) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  protected urlDe(url: string | null): string | null {
    return this.api.urlDeImagen(url);
  }

  /** Si las ordenó el modelo. Cambia el texto del pie, no el contenido. */
  protected porIa(): boolean {
    const motor = this.datos()?.motor;
    return !!motor && motor !== 'popularidad';
  }
}
