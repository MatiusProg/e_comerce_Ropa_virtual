import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  AjusteCrear,
  AjusteRegistrado,
  Existencia,
  FiltrosExistencias,
  FiltrosIngresos,
  FiltrosMovimientos,
  IngresoCrear,
  IngresoRegistrado,
  IngresoResumen,
  Movimiento,
  PaginaIngresos,
  PaginaMovimientos,
  TipoManual,
  TransferenciaCrear,
  TransferenciaRegistrada,
} from '../models/inventario.models';

/**
 * Errores previstos de CU-13 y CU-15, traducidos desde el código HTTP.
 *
 * Se distinguen y no se colapsan en «error» porque cada uno lleva a una acción
 * distinta en la pantalla:
 *
 * - `lineas-invalidas` trae **qué variantes** fallaron (E1), y eso permite
 *   señalar las filas del remito en vez de invalidar el formulario entero.
 * - `sin-diferencia` (E7) no es un fallo: el conteo coincidió, y la pantalla
 *   tiene que decirlo como una confirmación tranquila, no como un error rojo.
 * - `reservas-comprometidas` (E8) manda a cancelar una reserva primero, que es
 *   otra pantalla y otro caso de uso.
 * - `stock-insuficiente` (E6) devuelve el control al campo de cantidad.
 */
export type ErrorInventario =
  | { tipo: 'lineas-invalidas'; mensaje: string; variantes: number[] }
  | { tipo: 'stock-insuficiente'; mensaje: string }
  | { tipo: 'sin-diferencia'; mensaje: string }
  | { tipo: 'reservas-comprometidas'; mensaje: string }
  | { tipo: 'no-encontrado'; mensaje: string }
  | { tipo: 'dado-de-baja'; mensaje: string }
  | { tipo: 'sin-permiso'; mensaje: string }
  | { tipo: 'validacion'; mensaje: string }
  | { tipo: 'sistema'; mensaje: string };

@Injectable({ providedIn: 'root' })
export class InventarioService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/inventario`;

  // --- CU-13 · Ingreso de mercadería -------------------------------------

  registrarIngreso(datos: IngresoCrear): Observable<IngresoRegistrado> {
    return this.http
      .post<IngresoRegistrado>(`${this.base}/ingresos`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  listarIngresos(filtros: FiltrosIngresos = {}): Observable<PaginaIngresos> {
    let params = new HttpParams();
    if (filtros.sucursal_id) params = params.set('sucursal_id', filtros.sucursal_id);
    if (filtros.proveedor_id) params = params.set('proveedor_id', filtros.proveedor_id);
    if (filtros.pagina) params = params.set('pagina', filtros.pagina);
    if (filtros.tamano) params = params.set('tamano', filtros.tamano);
    return this.http
      .get<PaginaIngresos>(`${this.base}/ingresos`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * Las líneas de un ingreso del historial.
   *
   * Se identifica por instante, sucursal y remito porque el ingreso no tiene
   * fila propia: son los mismos datos que lo agrupan en el listado.
   */
  detalleDeIngreso(ingreso: IngresoResumen): Observable<Movimiento[]> {
    let params = new HttpParams()
      .set('registrado_en', ingreso.registrado_en)
      .set('sucursal_id', ingreso.sucursal_id);
    if (ingreso.referencia) params = params.set('referencia', ingreso.referencia);
    return this.http
      .get<Movimiento[]>(`${this.base}/ingresos/detalle`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Consultas del depósito --------------------------------------------

  listarExistencias(filtros: FiltrosExistencias = {}): Observable<Existencia[]> {
    let params = new HttpParams();
    if (filtros.sucursal_id) params = params.set('sucursal_id', filtros.sucursal_id);
    if (filtros.producto_id) params = params.set('producto_id', filtros.producto_id);
    if (filtros.solo_con_saldo) params = params.set('solo_con_saldo', true);
    return this.http
      .get<Existencia[]>(`${this.base}/existencias`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  listarMovimientos(filtros: FiltrosMovimientos = {}): Observable<PaginaMovimientos> {
    let params = new HttpParams();
    if (filtros.sucursal_id) params = params.set('sucursal_id', filtros.sucursal_id);
    if (filtros.variante_id) params = params.set('variante_id', filtros.variante_id);
    if (filtros.tipo) params = params.set('tipo', filtros.tipo);
    if (filtros.desde) params = params.set('desde', filtros.desde);
    if (filtros.hasta) params = params.set('hasta', filtros.hasta);
    if (filtros.pagina) params = params.set('pagina', filtros.pagina);
    if (filtros.tamano) params = params.set('tamano', filtros.tamano);
    return this.http
      .get<PaginaMovimientos>(`${this.base}/movimientos`, { params })
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  /**
   * Los tipos que se cargan a mano, para el selector.
   *
   * Se piden al servidor en vez de escribirlos acá por el mismo motivo que los
   * cargos de CU-06: el CHECK los fija en la base, y repetirlos en la interfaz
   * garantiza que algún día digan cosas distintas.
   */
  tiposManuales(): Observable<TipoManual[]> {
    return this.http
      .get<TipoManual[]>(`${this.base}/tipos-movimiento`)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- CU-15 · Movimientos -----------------------------------------------

  registrarAjuste(datos: AjusteCrear): Observable<AjusteRegistrado> {
    return this.http
      .post<AjusteRegistrado>(`${this.base}/movimientos/ajuste`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  registrarTransferencia(
    datos: TransferenciaCrear,
  ): Observable<TransferenciaRegistrada> {
    return this.http
      .post<TransferenciaRegistrada>(`${this.base}/movimientos/transferencia`, datos)
      .pipe(catchError((e) => throwError(() => this.traducir(e))));
  }

  // --- Traducción de errores ---------------------------------------------

  private traducir(error: HttpErrorResponse): ErrorInventario {
    const bruto = error.error?.detail;
    const detalle: string = typeof bruto === 'string' ? bruto : '';

    if (error.status === 403) {
      return {
        tipo: 'sin-permiso',
        mensaje: detalle || 'No tiene permisos para esta operación.',
      };
    }

    if (error.status === 404) {
      return {
        tipo: 'no-encontrado',
        mensaje: detalle || 'El registro indicado ya no existe.',
      };
    }

    if (error.status === 409) {
      // El backend usa el mismo 409 para E6, E7 y E8, y se distinguen por el
      // texto que el propio caso de uso redacta. Se buscan las palabras de
      // cada uno, que no se solapan entre sí.
      if (detalle.includes('reservas')) {
        return { tipo: 'reservas-comprometidas', mensaje: detalle };
      }
      if (detalle.includes('coincide')) {
        return { tipo: 'sin-diferencia', mensaje: detalle };
      }
      return {
        tipo: 'stock-insuficiente',
        mensaje: detalle || 'No hay unidades suficientes.',
      };
    }

    if (error.status === 422) {
      // E1 viaja como objeto y no como texto: trae qué variantes fallaron,
      // para poder señalar las líneas del remito.
      if (bruto && typeof bruto === 'object' && Array.isArray(bruto.variantes)) {
        return {
          tipo: 'lineas-invalidas',
          mensaje: bruto.mensaje ?? 'Hay líneas del ingreso que no se pueden recibir.',
          variantes: bruto.variantes,
        };
      }
      if (detalle.includes('baja')) {
        return { tipo: 'dado-de-baja', mensaje: detalle };
      }
      // FastAPI manda `detail` como lista en los errores de validación de
      // esquema, así que `detalle` queda vacío y se usa el genérico.
      return {
        tipo: 'validacion',
        mensaje: detalle || 'Revise los datos del formulario.',
      };
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
