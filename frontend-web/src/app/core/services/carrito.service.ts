import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  AgregarAlCarrito,
  CARRITO_VACIO,
  type Carrito,
} from '../models/carrito.models';

/** Errores previstos de CU-26, traducidos desde el código HTTP. */
export type ErrorCarrito =
  | { tipo: 'no-ofrecible'; mensaje: string }
  | { tipo: 'fuera-del-carrito'; mensaje: string }
  | { tipo: 'tope'; mensaje: string }
  | { tipo: 'sin-sesion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

/**
 * P7 · Ventas — CU-26 Gestionar carrito de compras (RF14).
 *
 * **Guarda el carrito en una señal compartida.** No es caché por comodidad: la
 * burbuja del ícono y la pantalla del carrito muestran el mismo número, y si
 * cada una lo pidiera por su cuenta se desincronizarían en cuanto el cliente
 * agregara algo desde la ficha del producto. Todos los endpoints devuelven el
 * carrito entero justamente para que actualizarla sea una sola línea.
 *
 * La señal arranca vacía y sólo se llena cuando alguien pide el carrito: no se
 * consulta al arrancar la aplicación, porque la vitrina es pública y la mayoría
 * de quienes la miran no tienen sesión.
 */
@Injectable({ providedIn: 'root' })
export class CarritoService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/tienda/carrito`;

  private readonly _carrito = signal<Carrito>(CARRITO_VACIO);

  /** El carrito tal como lo devolvió el servidor la última vez. */
  readonly carrito = this._carrito.asReadonly();
  /** Prendas distintas: es el número de la burbuja. */
  readonly items = computed(() => this._carrito().items);
  readonly total = computed(() => this._carrito().total);

  /** Vacía la señal sin llamar al servidor. La usa el cierre de sesión. */
  olvidar(): void {
    this._carrito.set(CARRITO_VACIO);
  }

  ver(): Observable<Carrito> {
    return this.http.get<Carrito>(this.base).pipe(
      tap((c) => this._carrito.set(c)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))),
    );
  }

  /**
   * Agrega una prenda. **Suma** a lo que ya hubiera de esa variante.
   *
   * Es lo que espera quien pulsa «Agregar» dos veces desde la ficha: la segunda
   * vez no reemplaza la primera.
   */
  agregar(datos: AgregarAlCarrito): Observable<Carrito> {
    return this.http.post<Carrito>(`${this.base}/items`, datos).pipe(
      tap((c) => this._carrito.set(c)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))),
    );
  }

  /**
   * **Fija** la cantidad de una línea; no la suma.
   *
   * Es la operación del selector del carrito, y va por otro método que
   * `agregar` a propósito: uno que a veces suma y a veces fija sería imposible
   * de usar sin mirar el código.
   */
  cambiarCantidad(varianteId: number, cantidad: number): Observable<Carrito> {
    return this.http.patch<Carrito>(`${this.base}/items/${varianteId}`, { cantidad }).pipe(
      tap((c) => this._carrito.set(c)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))),
    );
  }

  quitar(varianteId: number): Observable<Carrito> {
    return this.http.delete<Carrito>(`${this.base}/items/${varianteId}`).pipe(
      tap((c) => this._carrito.set(c)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))),
    );
  }

  vaciar(): Observable<Carrito> {
    return this.http.delete<Carrito>(this.base).pipe(
      tap((c) => this._carrito.set(c)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducir(e))),
    );
  }

  // --- Traducción de errores ---------------------------------------------

  private traducir(error: HttpErrorResponse): ErrorCarrito {
    const detalle: string = error.error?.detail ?? '';

    if (error.status === 401 || error.status === 403) {
      return {
        tipo: 'sin-sesion',
        mensaje: 'Inicie sesión como cliente para usar el carrito.',
      };
    }
    if (error.status === 404) {
      // El servidor usa 404 para dos cosas distintas y el texto las separa:
      // una prenda que ya no se ofrece, y una línea que no está en el carrito.
      if (detalle.toLowerCase().includes('carrito')) {
        return { tipo: 'fuera-del-carrito', mensaje: detalle };
      }
      return {
        tipo: 'no-ofrecible',
        mensaje: detalle || 'La prenda que busca ya no está disponible.',
      };
    }
    if (error.status === 409) {
      return { tipo: 'tope', mensaje: detalle };
    }
    if (error.status === 0) {
      return {
        tipo: 'sistema',
        mensaje: 'No se pudo contactar al servidor. Verifique su conexión.',
      };
    }
    return { tipo: 'sistema', mensaje: detalle || 'No se pudo completar la operación.' };
  }
}
