import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import type {
  DevolucionIn,
  EstadoLocal,
  LoteOut,
  OperacionDeSucursal,
  OperacionGuardada,
  OperacionOfflineIn,
  PaqueteDeMostrador,
} from '../models/offline.models';
import { OPERACIONES, PAQUETES, borrar, guardar, leer, todos } from './almacen-local';
import { sinRespuesta } from '../sin-respuesta';

/** Igual que `MAXIMO_POR_LOTE` del backend. */
const POR_LOTE = 50;
const CLAVE_PAQUETE = 'mostrador';
/** Cada cuánto se reintenta sola la cola mientras haya pendientes. */
const REINTENTO_MS = 60_000;

const PENDIENTES: readonly EstadoLocal[] = ['local', 'enviada', 'en_conflicto'];

/**
 * CU-13, CU-14, CU-16, CU-17 y CU-18 en la web · el trabajo sin conexión.
 *
 * LA REGLA QUE SOSTIENE TODO (RNF06)
 * ----------------------------------
 * **Una operación sale de la cola solo cuando el servidor la confirma o la
 * rechaza.** Intentar enviarla no alcanza: si la respuesta se pierde, la
 * operación sigue en `enviada` y se vuelve a mandar; el UUID hace que el
 * servidor no la registre dos veces. Ninguna rama de este servicio borra una
 * operación que el servidor no decidió.
 *
 * El servicio vive en la raíz: la cola tiene que seguir sincronizando aunque
 * el cajero cambie de pantalla.
 */
@Injectable({ providedIn: 'root' })
export class OfflineService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/offline`;

  private readonly _enLinea = signal(typeof navigator === 'undefined' ? true : navigator.onLine);
  private readonly _paquete = signal<PaqueteDeMostrador | null>(null);
  private readonly _operaciones = signal<OperacionGuardada[]>([]);
  private readonly _sincronizando = signal(false);
  private readonly _ahora = signal(Date.now());

  readonly enLinea = this._enLinea.asReadonly();
  readonly paquete = this._paquete.asReadonly();
  readonly sincronizando = this._sincronizando.asReadonly();

  /** De la más nueva a la más vieja. */
  readonly operaciones = computed(() =>
    [...this._operaciones()].sort((a, b) =>
      b.operacion.creada_en.localeCompare(a.operacion.creada_en),
    ),
  );
  readonly pendientes = computed(() =>
    this._operaciones().filter((o) => PENDIENTES.includes(o.estado)),
  );
  /** RF-13: el paquete pasó su vigencia. No bloquea, avisa. */
  readonly vencido = computed(() => {
    const p = this._paquete();
    return p !== null && Date.parse(p.vigente_hasta) < this._ahora();
  });

  /** Se resuelve cuando ya se leyó lo guardado en el navegador. */
  readonly listo: Promise<void>;

  constructor() {
    this.listo = this.cargar();
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        this._enLinea.set(true);
        void this.sincronizar();
      });
      window.addEventListener('offline', () => this._enLinea.set(false));
      setInterval(() => {
        this._ahora.set(Date.now());
        if (this.pendientes().length) void this.sincronizar();
        else if (!this._enLinea()) void this.probarConexion();
      }, REINTENTO_MS);
    }
  }

  /**
   * ¿Volvió el servidor? El evento `online` solo avisa cuando vuelve la red
   * del equipo; si lo que se cayó fue el servidor, el navegador nunca se
   * entera. Por eso, sin red, se pregunta cada minuto.
   */
  async probarConexion(): Promise<boolean> {
    try {
      await firstValueFrom(this.http.get(`${environment.apiUrl.replace(/\/api\/v1$/, '')}/health`));
      this._enLinea.set(true);
      return true;
    } catch {
      return false;
    }
  }

  private async cargar(): Promise<void> {
    try {
      this._paquete.set((await leer<PaqueteDeMostrador>(PAQUETES, CLAVE_PAQUETE)) ?? null);
      this._operaciones.set(await todos<OperacionGuardada>(OPERACIONES));
    } catch {
      // Sin IndexedDB (modo privado de algunos navegadores) la web sigue
      // funcionando en línea; solo no puede trabajar sin red.
    }
  }

  /** Lo marca la pantalla cuando una petición falla sin respuesta (status 0). */
  marcarSinRed(): void {
    this._enLinea.set(false);
  }

  // --- CU-13 Preparar el dispositivo ---------------------------------------

  async preparar(): Promise<PaqueteDeMostrador> {
    const paquete = await firstValueFrom(
      this.http.get<PaqueteDeMostrador>(`${this.base}/paquete`),
    );
    // Lo vendido sin red y todavía no confirmado ya salió del cajón: si el
    // paquete nuevo no lo descontara, el cajero vería unidades que ya entregó.
    const vendido = new Map<number, number>();
    for (const o of this.pendientes()) {
      if (o.operacion.tipo !== 'VENTA') continue;
      for (const l of o.operacion.lineas) {
        vendido.set(l.variante_id, (vendido.get(l.variante_id) ?? 0) + l.cantidad);
      }
    }
    paquete.prendas = paquete.prendas.map((p) => ({
      ...p,
      disponible: Math.max(0, p.disponible - (vendido.get(p.variante_id) ?? 0)),
    }));
    await guardar(PAQUETES, paquete, CLAVE_PAQUETE);
    this._paquete.set(paquete);
    this._ahora.set(Date.now());
    return paquete;
  }

  // --- CU-14 + CU-16 Registrar venta y pago sin conexión -------------------

  /**
   * Guarda la venta en el navegador y descuenta del paquete. **No la
   * confirma**: cobrar no confirma (RN-05), la confirma el servidor al
   * sincronizar.
   */
  async registrarVenta(
    operacion: Omit<OperacionOfflineIn, 'uuid' | 'creada_en' | 'tipo' | 'turno_caja_id'>,
    resumen: string,
    total: string,
  ): Promise<OperacionGuardada> {
    const paquete = this._paquete();
    if (!paquete) throw new Error('El dispositivo no está preparado para trabajar sin conexión.');

    const guardada: OperacionGuardada = {
      uuid: crypto.randomUUID(),
      estado: 'local',
      operacion: {
        ...operacion,
        uuid: '',
        tipo: 'VENTA',
        creada_en: new Date().toISOString(),
        turno_caja_id: paquete.turno_caja_id,
      },
      resumen,
      total,
      intentos: 0,
      motivo: null,
      venta_codigo: null,
      requiere_devolucion: false,
      actualizada_en: new Date().toISOString(),
    };
    guardada.operacion.uuid = guardada.uuid;

    // Primero la operación y después el paquete: si el navegador se cierra
    // entre las dos escrituras, lo peor es un saldo local de más, que el
    // servidor corrige. Al revés se perdería una venta cobrada.
    await guardar(OPERACIONES, guardada);
    this._operaciones.update((ops) => [...ops, guardada]);

    const cantidades = new Map(operacion.lineas.map((l) => [l.variante_id, l.cantidad]));
    const actualizado: PaqueteDeMostrador = {
      ...paquete,
      prendas: paquete.prendas.map((p) =>
        cantidades.has(p.variante_id)
          ? { ...p, disponible: Math.max(0, p.disponible - cantidades.get(p.variante_id)!) }
          : p,
      ),
    };
    await guardar(PAQUETES, actualizado, CLAVE_PAQUETE);
    this._paquete.set(actualizado);
    return guardada;
  }

  // --- CU-17 Sincronizar operaciones pendientes ----------------------------

  /** Manda la cola por lotes. Nunca falla: lo que no se pudo, queda. */
  async sincronizar(): Promise<{ confirmadas: number; rechazadas: number } | null> {
    if (this._sincronizando()) return null;
    await this.listo;
    const cola = this.pendientes();
    if (!cola.length) return { confirmadas: 0, rechazadas: 0 };

    this._sincronizando.set(true);
    const cuenta = { confirmadas: 0, rechazadas: 0 };
    try {
      for (let i = 0; i < cola.length; i += POR_LOTE) {
        if ((await this.enviar(cola.slice(i, i + POR_LOTE), cuenta)) === 'parar') break;
      }
    } finally {
      this._sincronizando.set(false);
    }
    return cuenta;
  }

  /**
   * Manda un lote y anota lo que decidió el servidor.
   *
   * Si el servidor no acepta el lote entero (422, 403, 409), ninguna se
   * decidió: una sola mal formada lo tumba. Entonces se reintentan de a una,
   * y solo la culpable queda `en_conflicto`, a la vista y sin borrarse.
   */
  private async enviar(
    lote: OperacionGuardada[],
    cuenta: { confirmadas: number; rechazadas: number },
  ): Promise<'seguir' | 'parar'> {
    for (const o of lote) {
      await this.actualizar(o.uuid, { estado: 'enviada', intentos: o.intentos + 1 });
    }
    try {
      const r = await firstValueFrom(
        this.http.post<LoteOut>(`${this.base}/sincronizar`, {
          dispositivo: this.nombreDelDispositivo(),
          operaciones: lote.map((o) => o.operacion),
        }),
      );
      this._enLinea.set(true);
      for (const res of r.resultados) {
        await this.actualizar(res.uuid, {
          estado: res.estado === 'CONFIRMADA' ? 'confirmada' : 'rechazada',
          motivo: res.motivo,
          venta_codigo: res.venta_codigo,
          requiere_devolucion: res.requiere_devolucion,
        });
      }
      cuenta.confirmadas += r.confirmadas;
      cuenta.rechazadas += r.rechazadas;
      return 'seguir';
    } catch (e) {
      const error = e as HttpErrorResponse;
      if (sinRespuesta(error)) {
        // Sin red: quedan en `enviada` y se reintentan. El UUID protege.
        this._enLinea.set(false);
        return 'parar';
      }
      // Sesión vencida o servidor caído: se reintenta más tarde, igual.
      if (error.status === 401 || error.status >= 500) return 'parar';
      if (lote.length > 1) {
        for (const o of lote) {
          if ((await this.enviar([o], cuenta)) === 'parar') return 'parar';
        }
        return 'seguir';
      }
      const detalle =
        typeof error.error?.detail === 'string'
          ? error.error.detail
          : 'El servidor no aceptó la operación. Revísela.';
      await this.actualizar(lote[0].uuid, { estado: 'en_conflicto', motivo: detalle });
      return 'seguir';
    }
  }

  /** Saca de la vista las ya confirmadas. Las rechazadas quedan: hay que devolver. */
  async limpiarConfirmadas(): Promise<void> {
    for (const o of this._operaciones().filter((x) => x.estado === 'confirmada')) {
      await borrar(OPERACIONES, o.uuid);
    }
    this._operaciones.update((ops) => ops.filter((o) => o.estado !== 'confirmada'));
  }

  private async actualizar(uuid: string, cambios: Partial<OperacionGuardada>): Promise<void> {
    const actual = this._operaciones().find((o) => o.uuid === uuid);
    if (!actual) return;
    const nueva = { ...actual, ...cambios, actualizada_en: new Date().toISOString() };
    await guardar(OPERACIONES, nueva);
    this._operaciones.update((ops) => ops.map((o) => (o.uuid === uuid ? nueva : o)));
  }

  private nombreDelDispositivo(): string {
    return `web · ${navigator.userAgent}`.slice(0, 80);
  }

  // --- CU-19 Atender operaciones rechazadas (encargado) --------------------

  deSucursal(porDevolver: boolean) {
    return this.http.get<OperacionDeSucursal[]>(`${this.base}/operaciones`, {
      params: { por_devolver: porDevolver },
    });
  }

  registrarDevolucion(uuid: string, datos: DevolucionIn) {
    return this.http.post<OperacionDeSucursal>(`${this.base}/operaciones/${uuid}/devolucion`, datos);
  }
}
