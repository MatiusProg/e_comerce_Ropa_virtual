import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  ConflictoDePrecio,
  CrearPedidoIn,
  CrearPedidoRespuesta,
  OpcionesDePedido,
  Pedido,
} from '../models/pedidos.models';

/**
 * El 409 del total cambiado viaja aparte de los demás errores.
 *
 * No es «algo salió mal»: es una respuesta con contenido que la pantalla tiene
 * que mostrar —el total nuevo y el carrito al día— para que el cliente decida
 * de nuevo. Tratarlo como un error genérico perdería justo lo que lo hace útil.
 */
export type ErrorPedido =
  | { tipo: 'conflicto'; mensaje: string }
  | { tipo: 'pasarela'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'no-existe'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * Los errores de **crear** un pedido, que son los de siempre más uno.
 *
 * El conflicto de precio se declara sólo acá y no en `ErrorPedido` porque
 * únicamente `crear` puede producirlo: consultar o cancelar un pedido ya hecho
 * no compara totales con nada. Separarlos deja que el compilador garantice que
 * las otras pantallas siempre tengan un `mensaje` que mostrar, en vez de que
 * cada una tenga que acordarse de descartar un caso que no puede ocurrirle.
 */
export type ErrorCrearPedido =
  | ErrorPedido
  | { tipo: 'precio-cambiado'; conflicto: ConflictoDePrecio };

/**
 * CU-27 — el cliente HTTP de los pedidos y el pago.
 *
 * Servicio propio y no un método dentro de `CarritoService`: son dos casos de
 * uso con contratos distintos, y el carrito lo puede tocar cualquiera mientras
 * que un pedido, una vez creado, ya no.
 */
@Injectable({ providedIn: 'root' })
export class PedidosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/tienda/pedidos`;

  /** Paso 1: el carrito, las sucursales que lo abastecen y mis direcciones. */
  opciones(): Observable<OpcionesDePedido> {
    return this.http
      .get<OpcionesDePedido>(`${this.base}/opciones`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /** Paso 2: se crea el pedido y vuelve la URL de la pasarela. */
  crear(datos: CrearPedidoIn): Observable<CrearPedidoRespuesta> {
    return this.http
      .post<CrearPedidoRespuesta>(this.base, datos)
      .pipe(catchError((e) => throwError(() => this.traducirCrear(e))));
  }

  /**
   * Paso 5: qué dice la BASE de este pedido.
   *
   * Es lo que consulta la pantalla de retorno. **No se usa la URL de la
   * pasarela para decidir si se pagó**: esa URL la puede escribir cualquiera a
   * mano. Es la decisión D5.
   */
  ver(codigo: string): Observable<Pedido> {
    return this.http
      .get<Pedido>(`${this.base}/${encodeURIComponent(codigo)}`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  cancelar(codigo: string): Observable<Pedido> {
    return this.http
      .post<Pedido>(`${this.base}/${encodeURIComponent(codigo)}/cancelar`, {})
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * El conflicto de precio, que sólo `crear` puede recibir.
   *
   * El backend manda este conflicto como un **objeto** dentro de `detail`,
   * mientras que los demás 409 mandan una cadena. La forma es lo único que los
   * separa, así que es lo que se mira.
   */
  private traducirCrear(error: HttpErrorResponse): ErrorCrearPedido {
    const detalle: unknown = error.error?.detail;
    if (
      error.status === 409 &&
      detalle &&
      typeof detalle === 'object' &&
      'total_actual' in detalle
    ) {
      return { tipo: 'precio-cambiado', conflicto: detalle as ConflictoDePrecio };
    }
    return this.traducir(error);
  }

  private traducir(error: HttpErrorResponse): ErrorPedido {
    const detalle: unknown = error.error?.detail;

    if (error.status === 409) {
      return {
        tipo: 'conflicto',
        mensaje:
          typeof detalle === 'string' ? detalle : 'El pedido ya no se puede hacer así.',
      };
    }
    if (error.status === 502) {
      return {
        tipo: 'pasarela',
        mensaje:
          typeof detalle === 'string'
            ? detalle
            : 'No pudimos contactar a la pasarela de pago. Intente de nuevo.',
      };
    }
    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: typeof detalle === 'string' ? detalle : 'Los pedidos son del Cliente.',
      };
    }
    if (error.status === 404) {
      return { tipo: 'no-existe', mensaje: 'No encontramos ese pedido.' };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return {
      tipo: 'sistema',
      mensaje: typeof detalle === 'string' ? detalle : 'No se pudo completar el pedido.',
    };
  }
}
