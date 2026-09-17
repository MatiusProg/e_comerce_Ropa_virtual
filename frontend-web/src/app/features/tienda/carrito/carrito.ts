import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CarritoService, type ErrorCarrito } from '../../../core/services/carrito.service';
import { CANTIDAD_MAXIMA, type LineaCarrito } from '../../../core/models/carrito.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';

/**
 * CU-26 · Gestionar carrito de compras — «boundary» PantallaCarrito.
 *
 * Realiza los pasos 2 a 4 y los flujos alternativos 3a, 3b y 3c.
 *
 * **Los precios que se ven son los vigentes, no los de cuando se agregó la
 * prenda.** El carrito no guarda precios: es una intención, no un contrato, y
 * el precio se fija al generar el pedido (CU-27). Por eso la pantalla se
 * recarga al entrar en vez de confiar en lo que tuviera la señal.
 *
 * **Una prenda que dejó de ofrecerse sigue en la lista**, marcada y sin sumar
 * al total. Si desapareciera, el cliente vería bajar el total sin entender por
 * qué; así puede sacarla él, o preguntar.
 *
 * El botón de pagar está deshabilitado y lo dice: CU-27 es el caso de uso
 * siguiente y todavía no existe. Un botón que no lleva a ninguna parte es peor
 * que uno que explica por qué no se puede usar.
 */
@Component({
  selector: 'app-carrito',
  imports: [
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './carrito.html',
  styleUrl: './carrito.scss',
})
export class CarritoPantalla implements OnInit {
  private readonly api = inject(CarritoService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly maximo = CANTIDAD_MAXIMA;

  protected readonly carrito = this.api.carrito;
  protected readonly cargando = signal(true);
  protected readonly error = signal<ErrorCarrito | null>(null);

  /**
   * La línea que está esperando respuesta, para deshabilitar sólo sus botones.
   *
   * Bloquear la pantalla entera por cambiar una cantidad haría parpadear todo;
   * no bloquear nada dejaría que dos toques rápidos manden dos peticiones que
   * llegan desordenadas.
   */
  protected readonly ocupada = signal<number | null>(null);

  ngOnInit(): void {
    this.recargar();
  }

  private recargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.ver().subscribe({
      next: () => this.cargando.set(false),
      error: (e: ErrorCarrito) => {
        this.cargando.set(false);
        this.error.set(e);
      },
    });
  }

  protected sumar(linea: LineaCarrito): void {
    this.fijar(linea, linea.cantidad + 1);
  }

  protected restar(linea: LineaCarrito): void {
    // En 1 el botón de restar está deshabilitado: bajar a cero no es «cantidad
    // cero», es quitar la prenda, y para eso está su propio botón.
    if (linea.cantidad <= 1) return;
    this.fijar(linea, linea.cantidad - 1);
  }

  private fijar(linea: LineaCarrito, cantidad: number): void {
    if (cantidad > this.maximo || this.ocupada() !== null) return;

    this.ocupada.set(linea.variante_id);
    this.api.cambiarCantidad(linea.variante_id, cantidad).subscribe({
      next: () => this.ocupada.set(null),
      error: (e: ErrorCarrito) => {
        this.ocupada.set(null);
        this.avisar(e);
      },
    });
  }

  protected quitar(linea: LineaCarrito): void {
    this.ocupada.set(linea.variante_id);
    this.api.quitar(linea.variante_id).subscribe({
      next: () => {
        this.ocupada.set(null);
        this.aviso.open(`«${linea.producto_nombre}» salió del carrito.`, 'Cerrar', {
          duration: 4000,
        });
      },
      error: (e: ErrorCarrito) => {
        this.ocupada.set(null);
        this.avisar(e);
      },
    });
  }

  protected vaciar(): void {
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'Vaciar el carrito',
          mensaje: '¿Sacar todas las prendas del carrito? No se puede deshacer.',
          confirmar: 'Vaciar',
          peligrosa: true,
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.api.vaciar().subscribe({
          error: (e: ErrorCarrito) => this.avisar(e),
        });
      });
  }

  private avisar(e: ErrorCarrito): void {
    this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 });
    // Un 404 acá significa que la pantalla está vieja: alguien tocó el carrito
    // desde otra pestaña, o la prenda se desactivó. Recargar la deja diciendo
    // la verdad en vez de mostrar una línea que ya no existe.
    if (e.tipo === 'fuera-del-carrito' || e.tipo === 'no-ofrecible') this.recargar();
  }
}
