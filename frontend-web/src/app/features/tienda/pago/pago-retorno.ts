import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { PedidosService, type ErrorPedido } from '../../../core/services/pedidos.service';
import type { Pedido } from '../../../core/models/pedidos.models';
import { CLAVE_PEDIDO_EN_CURSO } from '../checkout/checkout';
import { NavegacionCliente } from '../../../shared/navegacion-cliente/navegacion-cliente';

/**
 * CU-27 · Paso 5 — «boundary» PantallaRetornoDePago.
 *
 * Adonde vuelve el navegador desde la pasarela. Sirve para las dos salidas
 * —`/pago/exito` y `/pago/cancelado`— porque hacen lo mismo: preguntar al
 * backend y mostrar lo que diga la venta.
 *
 * ESTA PANTALLA NO DECIDE SI SE PAGÓ. NUNCA.
 * -------------------------------------------
 * Es la decisión **D5** del análisis: el estado del pago sólo lo determina la
 * pasarela, y llega por el webhook firmado de CU-28. La URL por la que el
 * navegador volvió no prueba nada —cualquiera puede escribir `/pago/exito` en
 * la barra de direcciones—, así que se usa **únicamente** para saber qué
 * pedido consultar y con qué tono recibir a la persona.
 *
 * Lo que se muestra sale de `GET /tienda/pedidos/{codigo}`, es decir, de la
 * base. Por eso alguien que llegue a `/pago/exito` a mano va a ver su pedido
 * tal como está: esperando el pago.
 *
 * DE DÓNDE SALE EL CÓDIGO DEL PEDIDO
 * -----------------------------------
 * Tres fuentes, en este orden, y hacen falta las tres:
 *
 *   1. `?pedido=` — lo manda el proveedor `simulada`.
 *   2. `sessionStorage` — lo guardó la pantalla de confirmación antes de
 *      redirigir. Es la única que sirve con **Stripe**, cuyo `success_url`
 *      lleva sólo `?sesion={CHECKOUT_SESSION_ID}` y cuyo `cancel_url` no lleva
 *      ningún parámetro.
 *   3. Se lo pedimos a la persona. Queda como último recurso para el caso
 *      Stripe + almacenamiento bloqueado (una ventana privada, o un navegador
 *      con los datos de sitio desactivados), donde las dos primeras fallan.
 *
 * La tercera existe para que esta pantalla **nunca sea un callejón sin
 * salida**: quien acaba de pagar tiene que poder llegar a su pedido aunque el
 * navegador no coopere.
 *
 * > La forma limpia de cerrar el caso 3 es del lado del backend: que
 * > `stripe_hospedado.py` agregue `&pedido=<referencia>` a su `success_url`,
 * > como ya hace el proveedor simulado. Es una línea, está anotada en la ficha
 * > del caso de uso y es de Mateo —el backend de CU-27 es suyo—, así que desde
 * > acá se resuelve sin tocarlo.
 */
@Component({
  selector: 'app-pago-retorno',
  imports: [
    NavegacionCliente,
    CurrencyPipe,
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
  ],
  templateUrl: './pago-retorno.html',
  styleUrl: './pago-retorno.scss',
})
export class PagoRetorno implements OnInit {
  private readonly api = inject(PedidosService);
  private readonly ruta = inject(ActivatedRoute);

  /**
   * Con qué tono recibir. Lo fija la ruta, no el servidor.
   *
   * `cancelado` sólo cambia el encabezado: el pedido igual se consulta y se
   * muestra su estado real. Alguien puede cerrar la pasarela y que el pago
   * haya entrado igual.
   */
  readonly salida = input<'exito' | 'cancelado'>('exito');

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly pedido = signal<Pedido | null>(null);
  protected readonly cancelando = signal(false);
  /** Cuando no se pudo averiguar de qué pedido se trata. */
  protected readonly sinCodigo = signal(false);

  /** El código que la persona escribe a mano cuando fallan las dos primeras. */
  protected readonly codigoAMano = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    const codigo = this.resolverCodigo();
    if (!codigo) {
      this.sinCodigo.set(true);
      this.cargando.set(false);
      return;
    }
    this.consultar(codigo);
  }

  /**
   * Buscar con el código escrito a mano.
   *
   * Se normaliza —sin espacios y en mayúsculas— porque el código se lee de una
   * pantalla o se dicta por teléfono, y llega con la forma que llegue. Rechazar
   * `vb-20260917-a3f9c1` por minúsculas sería inventar un requisito.
   */
  protected buscarAMano(): void {
    const codigo = this.codigoAMano.value.trim().toUpperCase();
    if (!codigo) return;
    this.sinCodigo.set(false);
    this.consultar(codigo);
  }

  /** Volver al formulario tras un código equivocado, sin rehacer el camino. */
  protected pedirCodigo(): void {
    this.error.set(null);
    this.pedido.set(null);
    this.sinCodigo.set(true);
  }

  private resolverCodigo(): string | null {
    const enLaUrl = this.ruta.snapshot.queryParamMap.get('pedido');
    if (enLaUrl) return enLaUrl;
    try {
      return sessionStorage.getItem(CLAVE_PEDIDO_EN_CURSO);
    } catch {
      // Pestaña privada o almacenamiento bloqueado. Se cae al caso 3.
      return null;
    }
  }

  private consultar(codigo: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.ver(codigo).subscribe({
      next: (p) => {
        this.pedido.set(p);
        this.cargando.set(false);
        // El pedido ya no está en curso: se suelta el código para que una
        // compra siguiente no herede el de la anterior.
        if (p.estado !== 'PENDIENTE_PAGO') this.olvidarPedido();
      },
      error: (e: ErrorPedido) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  /**
   * Cancelar desde acá, sin volver al carrito.
   *
   * Tiene sentido justo en la salida `cancelado`: la persona ya dijo que no
   * quiere pagar, y el pedido sigue teniendo stock apartado hasta que la
   * barrida de vencidos lo suelte. Cancelar ahora lo devuelve enseguida.
   */
  protected cancelar(): void {
    const p = this.pedido();
    if (!p || this.cancelando()) return;
    this.cancelando.set(true);
    this.api.cancelar(p.codigo).subscribe({
      next: (actualizado) => {
        this.pedido.set(actualizado);
        this.cancelando.set(false);
        this.olvidarPedido();
      },
      error: (e: ErrorPedido) => {
        this.error.set(e.mensaje);
        this.cancelando.set(false);
      },
    });
  }

  protected olvidarPedido(): void {
    try {
      sessionStorage.removeItem(CLAVE_PEDIDO_EN_CURSO);
    } catch {
      // Sin almacenamiento no hay nada que olvidar.
    }
  }

  /** Lo que se le dice a la persona, según lo que diga la BASE. */
  protected titulo(): string {
    const p = this.pedido();
    if (!p) return this.salida() === 'cancelado' ? 'Pago cancelado' : 'Volviendo del pago';
    switch (p.estado) {
      case 'PAGADA':
        return '¡Listo! Su pago se confirmó';
      case 'ENTREGADA':
        return 'Su pedido ya fue entregado';
      case 'CANCELADA':
        return 'Este pedido está cancelado';
      default:
        return 'Su pedido todavía espera el pago';
    }
  }

  protected icono(): string {
    const p = this.pedido();
    if (!p) return 'hourglass_top';
    switch (p.estado) {
      case 'PAGADA':
        return 'check_circle';
      case 'ENTREGADA':
        return 'local_shipping';
      case 'CANCELADA':
        return 'cancel';
      default:
        return 'schedule';
    }
  }

  protected esperandoPago(): boolean {
    return this.pedido()?.estado === 'PENDIENTE_PAGO';
  }
}
