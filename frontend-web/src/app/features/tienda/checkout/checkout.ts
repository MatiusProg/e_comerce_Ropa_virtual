import { CurrencyPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatRadioModule } from '@angular/material/radio';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  PedidosService,
  type ErrorCrearPedido,
} from '../../../core/services/pedidos.service';
import type {
  ConflictoDePrecio,
  ModalidadEntrega,
  OpcionesDePedido,
} from '../../../core/models/pedidos.models';
import { NavegacionCliente } from '../../../shared/navegacion-cliente/navegacion-cliente';

/**
 * Dónde se guarda el código del pedido antes de irse a la pasarela.
 *
 * **Hace falta porque la URL de retorno no siempre lo trae.** El proveedor
 * `simulada` vuelve con `?sesion=...&pedido=VB-...`, pero Stripe arma su
 * `success_url` con `?sesion={CHECKOUT_SESSION_ID}` y nada más, y su
 * `cancel_url` no lleva ningún parámetro. Sin esto, la pantalla de retorno no
 * sabría qué pedido consultar en cuanto se cambie de proveedor.
 *
 * Es `sessionStorage` y no `localStorage` a propósito: muere con la pestaña,
 * que es exactamente lo que dura el viaje a la pasarela y la vuelta.
 */
export const CLAVE_PEDIDO_EN_CURSO = 'vb.pedido-en-curso';

/**
 * CU-27 · Realizar pedido y pagar en línea — «boundary» PantallaConfirmar.
 *
 * Paso 1 y 2 del flujo: el cliente revisa lo que va a comprar, elige cómo lo
 * recibe, y confirma. Lo que sigue —la pasarela— no es una pantalla nuestra.
 *
 * **La web es de Karen; el backend, de Mateo** (acuerdo del 17/09, que también
 * le dio a él la parte móvil). El contrato está en
 * `backend/app/modules/ventas/schemas.py`.
 *
 * TRES COSAS QUE ESTA PANTALLA HACE Y NO SE VEN
 * ----------------------------------------------
 * **1. Manda el total que el cliente vio.** `total_esperado` viaja en la
 * confirmación, y si la tienda cambió un precio en el medio el servidor se
 * planta con un 409 en vez de cobrar el precio nuevo callado. Acá eso se pinta
 * como un aviso con el total viejo y el nuevo, no como un error.
 *
 * **2. Dice cuando el pago es de mentira.** Si `pago_real` es `false`, la
 * pantalla lo declara antes de que el cliente pulse. En la demostración el
 * proveedor es el simulado, y dejar que parezca real sería engañar al tribunal.
 *
 * **3. Guarda el código antes de redirigir.** Ver `CLAVE_PEDIDO_EN_CURSO`.
 */
@Component({
  selector: 'app-checkout',
  imports: [
    NavegacionCliente,
    CurrencyPipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatRadioModule,
    MatTooltipModule,
  ],
  templateUrl: './checkout.html',
  styleUrl: './checkout.scss',
})
export class Checkout implements OnInit {
  private readonly api = inject(PedidosService);
  private readonly router = inject(Router);

  protected readonly cargando = signal(true);
  protected readonly confirmando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly conflicto = signal<ConflictoDePrecio | null>(null);
  protected readonly opciones = signal<OpcionesDePedido | null>(null);

  protected readonly modalidad = new FormControl<ModalidadEntrega>('RETIRO', {
    nonNullable: true,
  });
  protected readonly sucursalElegida = signal<number | null>(null);
  protected readonly direccionElegida = signal<number | null>(null);

  /** Las sucursales que pueden abastecer el pedido entero. */
  protected readonly sucursalesUtiles = computed(
    () => this.opciones()?.sucursales.filter((s) => s.abastece_todo) ?? [],
  );

  /** Las que no llegan. Se muestran igual, apagadas y con el motivo. */
  protected readonly sucursalesCortas = computed(
    () => this.opciones()?.sucursales.filter((s) => !s.abastece_todo) ?? [],
  );

  /**
   * Si se puede pulsar confirmar.
   *
   * Tres condiciones, y cada una tapa un agujero distinto: que el backend diga
   * que el pedido es posible, que haya un destino elegido para la modalidad, y
   * que no haya una confirmación ya en vuelo —sin lo último, un doble clic
   * crearía dos pedidos y apartaría el stock dos veces—.
   */
  protected readonly puedeConfirmar = computed(() => {
    const o = this.opciones();
    if (!o?.se_puede_pedir || this.confirmando()) return false;
    return this.modalidad.value === 'RETIRO'
      ? this.sucursalElegida() !== null
      : this.direccionElegida() !== null;
  });

  ngOnInit(): void {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.opciones().subscribe({
      next: (o) => {
        this.opciones.set(o);
        this.preseleccionar(o);
        this.cargando.set(false);
      },
      error: (e: ErrorCrearPedido) => {
        this.error.set(this.mensaje(e));
        this.cargando.set(false);
      },
    });
  }

  /**
   * Elige por el cliente lo que se puede elegir sin ambigüedad.
   *
   * Si hay una sola sucursal capaz, no tiene sentido hacerle pulsar; si tiene
   * una dirección predeterminada, es la que quiere. Preseleccionar lo obvio
   * deja la pantalla lista para confirmar de una, que es el caso normal.
   */
  private preseleccionar(o: OpcionesDePedido): void {
    const utiles = o.sucursales.filter((s) => s.abastece_todo);
    if (utiles.length > 0) this.sucursalElegida.set(utiles[0].id);

    const favorita = o.direcciones.find((d) => d.predeterminada) ?? o.direcciones[0];
    if (favorita) this.direccionElegida.set(favorita.id);
  }

  protected elegirSucursal(id: number): void {
    this.sucursalElegida.set(id);
  }

  protected elegirDireccion(id: number): void {
    this.direccionElegida.set(id);
  }

  protected confirmar(): void {
    const o = this.opciones();
    if (!o || !this.puedeConfirmar()) return;

    this.confirmando.set(true);
    this.error.set(null);
    this.conflicto.set(null);

    const esRetiro = this.modalidad.value === 'RETIRO';
    this.api
      .crear({
        modalidad_entrega: this.modalidad.value,
        // Sólo uno de los dos viaja: el backend rechaza la combinación
        // contraria con un 422, y su validador dice que en un envío la
        // sucursal que despacha la elige el sistema.
        sucursal_id: esRetiro ? (this.sucursalElegida() ?? undefined) : undefined,
        direccion_id: esRetiro ? undefined : (this.direccionElegida() ?? undefined),
        total_esperado: o.total,
      })
      .subscribe({
        next: (respuesta) => {
          this.recordarPedido(respuesta.pedido.codigo);
          // `location.href` y no el Router: `url_pago` es de otro origen —la
          // pasarela—, y el Router de Angular sólo navega dentro de la
          // aplicación. Con el proveedor simulado la URL vuelve a esta misma
          // web, y aun así se sale y se entra: así el flujo que se demuestra
          // es el mismo que el real.
          window.location.href = respuesta.url_pago;
        },
        error: (e: ErrorCrearPedido) => {
          this.confirmando.set(false);
          if (e.tipo === 'precio-cambiado') {
            this.conflicto.set(e.conflicto);
            // Se recarga para que el resto de la pantalla —el carrito, las
            // sucursales que abastecen— quede al día con el precio nuevo. El
            // aviso del conflicto sobrevive a la recarga.
            const guardado = e.conflicto;
            this.api.opciones().subscribe({
              next: (o2) => {
                this.opciones.set(o2);
                this.conflicto.set(guardado);
              },
            });
            return;
          }
          this.error.set(this.mensaje(e));
        },
      });
  }

  private recordarPedido(codigo: string): void {
    try {
      sessionStorage.setItem(CLAVE_PEDIDO_EN_CURSO, codigo);
    } catch {
      // Una pestaña privada o con el almacenamiento bloqueado lanza acá. No
      // es motivo para no dejar comprar: la pantalla de retorno tiene el
      // parámetro de la URL como respaldo, y si tampoco está, pide el código.
    }
  }

  protected cerrarConflicto(): void {
    this.conflicto.set(null);
  }

  protected reintentar(): void {
    this.cargar();
  }

  private mensaje(e: ErrorCrearPedido): string {
    return e.tipo === 'precio-cambiado' ? e.conflicto.detalle : e.mensaje;
  }
}
