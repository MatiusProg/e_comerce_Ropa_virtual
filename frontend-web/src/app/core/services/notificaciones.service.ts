import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { environment } from '../../../environments/environment';

/**
 * CU-40 · Notificar eventos a los usuarios. Realiza el RF11.
 *
 * Espejo de `backend/app/modules/notificaciones/schemas.py`.
 *
 * **No hay `crear`.** El actor de CU-40 es el Sistema: los avisos nacen en los
 * servicios de reservas, pagos e inventario cuando el hecho ocurre. El servidor
 * tampoco expone un `POST /notificaciones`, así que un método acá no tendría a
 * dónde llamar.
 */

export type TipoNotificacion =
  | 'RESERVA_EN_SUCURSAL'
  | 'RESERVA_PREPARADA'
  | 'PEDIDO_PAGADO'
  | 'STOCK_BAJO';

export interface Notificacion {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  cuerpo: string;

  /** Ruta **relativa** de esta misma aplicación; se usa tal cual en routerLink. */
  enlace: string | null;

  entidad: string | null;
  entidad_id: number | null;

  /**
   * Ya viene **en hora boliviana**, convertida por el servidor.
   *
   * Por eso se formatea sin volver a convertir, igual que en la bitácora:
   * hacerlo en el navegador la pasaría a la zona del aparato.
   */
  creada_en: string;
  leida_en: string | null;

  correo_estado: 'OMITIDO' | 'PENDIENTE' | 'ENVIADO' | 'FALLIDO';
}

export interface PaginaNotificaciones {
  total: number;
  pagina: number;
  tamano: number;
  /** De **todas** las suyas, no las de esta página: es el número de la campanita. */
  no_leidas: number;
  items: Notificacion[];
}

export interface Despacho {
  intentadas: number;
  enviadas: number;
  fallidas: number;
}

/** El ícono de cada tipo. Acá y no en la plantilla: lo usan la campanita y la
 *  pantalla, y duplicarlo haría que un aviso se viera distinto en cada una. */
const ICONOS: Record<TipoNotificacion, string> = {
  RESERVA_EN_SUCURSAL: 'event_available',
  RESERVA_PREPARADA: 'inventory_2',
  PEDIDO_PAGADO: 'payments',
  STOCK_BAJO: 'warning',
};

export function iconoDe(tipo: TipoNotificacion): string {
  return ICONOS[tipo] ?? 'notifications';
}

@Injectable({ providedIn: 'root' })
export class NotificacionesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/notificaciones`;

  /**
   * Cuántas hay sin leer. Es el número del globito.
   *
   * Vive en el servicio y no en la campanita porque hay una campanita por
   * cáscara —cliente, sucursal, administración— y tres contadores que se
   * enteran por separado mostrarían números distintos en la misma sesión.
   */
  private readonly _noLeidas = signal(0);
  readonly noLeidas = this._noLeidas.asReadonly();

  /** Para el globito de Material, que oculta el badge cuando es `null`. */
  readonly globito = computed(() => this._noLeidas() || null);

  /**
   * Refresca el contador.
   *
   * Pide `/resumen` y no la lista: se llama en cada carga de pantalla, y traer
   * veinte filas para pintar un número es lo que vuelve lenta la navegación.
   */
  refrescarContador(): Observable<{ no_leidas: number }> {
    return this.http
      .get<{ no_leidas: number }>(`${this.base}/resumen`)
      .pipe(tap((r) => this._noLeidas.set(r.no_leidas)));
  }

  listar(opciones: {
    soloNoLeidas?: boolean;
    pagina?: number;
    tamano?: number;
  } = {}): Observable<PaginaNotificaciones> {
    let params = new HttpParams();
    if (opciones.soloNoLeidas) params = params.set('solo_no_leidas', 'true');
    if (opciones.pagina) params = params.set('pagina', String(opciones.pagina));
    if (opciones.tamano) params = params.set('tamano', String(opciones.tamano));
    // El listado también trae el contador, así que se aprovecha para
    // sincronizarlo: es el mismo número y evita una segunda llamada.
    return this.http
      .get<PaginaNotificaciones>(this.base, { params })
      .pipe(tap((p) => this._noLeidas.set(p.no_leidas)));
  }

  marcarLeida(id: number): Observable<void> {
    return this.http
      .post<void>(`${this.base}/${id}/leer`, {})
      .pipe(tap(() => this._noLeidas.update((n) => Math.max(0, n - 1))));
  }

  marcarTodasLeidas(): Observable<{ marcadas: number }> {
    return this.http
      .post<{ marcadas: number }>(`${this.base}/leer-todas`, {})
      .pipe(tap(() => this._noLeidas.set(0)));
  }

  /**
   * Manda los correos pendientes. **Solo Administrador.**
   *
   * Es el mismo arreglo que la expiración de reservas de CU-25: pensado para un
   * planificador, y expuesto además como botón para dispararlo a mano en la
   * defensa y mostrar el correo llegando.
   */
  despachar(): Observable<Despacho> {
    return this.http.post<Despacho>(
      `${environment.apiUrl}/mantenimiento/notificaciones/despacho`,
      {},
    );
  }

  /** Devuelve a la cola los avisos que fallaron. **Solo Administrador.** */
  reintentar(): Observable<{ encolados: number }> {
    return this.http.post<{ encolados: number }>(
      `${environment.apiUrl}/mantenimiento/notificaciones/reintento`,
      {},
    );
  }
}
