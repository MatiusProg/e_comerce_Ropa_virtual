import { HttpClient } from '@angular/common/http';
import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { SwPush } from '@angular/service-worker';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

/** Dónde se recuerda la suscripción de ESTE navegador, para darla de baja al
 *  cerrar sesión. La lee también `AuthService.cerrarSesion`. */
export const CLAVE_PUSH_LOCAL = 'vb.push.endpoint';

interface ConfiguracionPush {
  clave_publica_vapid: string | null;
  simulado: boolean;
}

/**
 * CU-42 · Los avisos push en la web instalada (PWA).
 *
 * Usa el service worker de Angular (`ngsw-worker.js`), que ya está registrado
 * para el modo sin conexión: él recibe el push aunque la pestaña esté cerrada
 * y muestra la notificación del sistema. Al tocarla, abre el `enlace` del aviso
 * (`data.onActionClick`, lo arma el servidor).
 *
 * **Solo existe en producción.** En `ng serve` el service worker no se
 * registra (`enabled: !isDevMode()`), así que `disponible` es falso y la
 * campanita no ofrece el botón. Para probarlo: `ng build` y servir `dist`.
 */
@Injectable({ providedIn: 'root' })
export class PushWebService {
  private readonly http = inject(HttpClient);
  private readonly swPush = inject(SwPush);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);
  private readonly base = `${environment.apiUrl}/notificaciones/push`;

  private readonly clavePublica = signal<string | null>(null);
  private readonly _activo = signal(false);
  readonly activo = this._activo.asReadonly();
  readonly ocupado = signal(false);

  /** El navegador puede y el servidor tiene Web Push configurado. */
  readonly disponible = computed(
    () => this.swPush.isEnabled && this.clavePublica() !== null,
  );

  readonly permisoDenegado = signal(
    typeof Notification !== 'undefined' && Notification.permission === 'denied',
  );

  private iniciado = false;

  constructor() {
    // Al cerrar sesión se olvida lo de la sesión: si no, quien entra después
    // en esta misma pestaña nunca volvía a pasar por `iniciar()` (quedaba
    // `iniciado = true`) y su navegador no se registraba a su nombre.
    // Solo en el paso de «con sesión» a «sin sesión»: al arrancar, el usuario
    // todavía puede estar restaurándose y no hay nada que olvidar.
    let habiaSesion = false;
    effect(() => {
      const haySesion = this.auth.usuario() !== null;
      if (habiaSesion && !haySesion) {
        this.iniciado = false;
        this.clavePublica.set(null);
      }
      habiaSesion = haySesion;
    });
    if (!this.swPush.isEnabled) return;
    this.swPush.subscription.subscribe((s) => this._activo.set(s !== null));
    // Tocar la notificación con la app abierta: navegar dentro de ella.
    this.swPush.notificationClicks.subscribe(({ notification }) => {
      const enlace = (notification.data as { onActionClick?: { default?: { url?: string } } })
        ?.onActionClick?.default?.url;
      if (enlace) void this.router.navigateByUrl(enlace);
    });
  }

  /** Pide la clave pública una vez por sesión. Sin sesión, no hace nada. */
  async iniciar(): Promise<void> {
    if (this.iniciado || !this.swPush.isEnabled) return;
    this.iniciado = true;
    try {
      const cfg = await firstValueFrom(this.http.get<ConfiguracionPush>(`${this.base}/configuracion`));
      this.clavePublica.set(cfg.clave_publica_vapid);
      // Si ya estaba suscrito (otra sesión en este navegador), se re-registra:
      // la suscripción pasa a quien inició sesión ahora.
      const actual = await firstValueFrom(this.swPush.subscription);
      if (actual) await this.registrar(actual);
    } catch {
      this.iniciado = false;
    }
  }

  async activar(): Promise<void> {
    const clave = this.clavePublica();
    if (!clave) return;
    this.ocupado.set(true);
    try {
      const sub = await this.swPush.requestSubscription({ serverPublicKey: clave });
      await this.registrar(sub);
    } catch (e) {
      this.permisoDenegado.set(
        typeof Notification !== 'undefined' && Notification.permission === 'denied',
      );
      throw e;
    } finally {
      this.ocupado.set(false);
    }
  }

  async desactivar(): Promise<void> {
    this.ocupado.set(true);
    try {
      const sub = await firstValueFrom(this.swPush.subscription);
      if (sub) {
        await firstValueFrom(
          this.http.post<void>(`${this.base}/dispositivos/baja`, { direccion: sub.endpoint }),
        ).catch(() => undefined);
      }
      await this.swPush.unsubscribe().catch(() => undefined);
      this.olvidar();
    } finally {
      this.ocupado.set(false);
    }
  }

  private async registrar(sub: PushSubscription): Promise<void> {
    const json = sub.toJSON();
    await firstValueFrom(
      this.http.post(`${this.base}/dispositivos`, {
        canal: 'WEBPUSH',
        direccion: sub.endpoint,
        clave_p256dh: json.keys?.['p256dh'],
        clave_auth: json.keys?.['auth'],
        dispositivo: this.nombreDelDispositivo(),
      }),
    );
    try {
      localStorage.setItem(CLAVE_PUSH_LOCAL, sub.endpoint);
    } catch {
      /* sin almacenamiento: la baja al salir no se hace, la pasa el próximo login */
    }
  }

  private olvidar(): void {
    try {
      localStorage.removeItem(CLAVE_PUSH_LOCAL);
    } catch {
      /* nada */
    }
  }

  private nombreDelDispositivo(): string {
    const ua = navigator.userAgent;
    const navegador = /Edg\//.test(ua) ? 'Edge' : /Chrome\//.test(ua) ? 'Chrome' : /Firefox\//.test(ua) ? 'Firefox' : 'Navegador';
    const sistema = /Android/.test(ua) ? 'Android' : /Windows/.test(ua) ? 'Windows' : /Mac OS/.test(ua) ? 'macOS' : /Linux/.test(ua) ? 'Linux' : '';
    return `${navegador} ${sistema}`.trim().slice(0, 120);
  }
}
