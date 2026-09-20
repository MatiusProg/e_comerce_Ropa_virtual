import { Injectable, NgZone, inject, signal } from '@angular/core';

/**
 * CU-35 · Reconocimiento de voz, en el NAVEGADOR.
 *
 * POR QUÉ ACÁ Y NO EN EL SERVIDOR
 * --------------------------------
 * Web Speech API viene con el navegador: es gratis, no consume cuota de
 * ningún modelo y no sube audio a ningún lado. Transcribir en el servidor
 * obligaría a un servicio de pago y a mandar megabytes por cada pedido —para
 * obtener exactamente el mismo texto—.
 *
 * NO ESTÁ EN TODOS LOS NAVEGADORES
 * ---------------------------------
 * Chrome y Edge sí; Firefox no, y Safari a medias. Por eso `soportado` existe
 * y la pantalla esconde el micrófono cuando no está, en vez de ofrecer un
 * botón que no hace nada. **La lista de reportes sigue funcionando igual**:
 * la voz es un atajo, no el único camino.
 *
 * Chrome manda el audio a los servidores de Google para transcribirlo. Es la
 * implementación del navegador, no una decisión de esta aplicación, pero
 * conviene saberlo antes de dictar algo delicado —acá solo se dictan nombres
 * de reportes—.
 */
@Injectable({ providedIn: 'root' })
export class DictadoService {
  private readonly zone = inject(NgZone);
  private reconocimiento: any = null;

  /** Si el navegador puede escuchar. */
  readonly soportado = signal(this.detectar());

  readonly escuchando = signal(false);

  /** Lo último que se escuchó, incluso parcial mientras se habla. */
  readonly texto = signal('');

  readonly error = signal<string | null>(null);

  private detectar(): boolean {
    if (typeof window === 'undefined') return false;
    const w = window as any;
    return !!(w.SpeechRecognition || w.webkitSpeechRecognition);
  }

  /**
   * Empieza a escuchar. Llama a [alTerminar] con la frase final.
   *
   * El resultado parcial se va publicando en `texto` para que se vea que
   * está funcionando: sin eso, hablar contra un botón mudo se siente roto y
   * la gente lo toca otra vez, cortando su propio dictado.
   */
  escuchar(alTerminar: (frase: string) => void): void {
    if (!this.soportado() || this.escuchando()) return;

    const w = window as any;
    const Reconocedor = w.SpeechRecognition || w.webkitSpeechRecognition;
    const r = new Reconocedor();
    this.reconocimiento = r;

    r.lang = 'es-BO';
    r.continuous = false;
    r.interimResults = true;
    r.maxAlternatives = 1;

    this.texto.set('');
    this.error.set(null);
    this.escuchando.set(true);

    let ultima = '';

    // Web Speech API dispara sus eventos FUERA de la zona de Angular, así
    // que sin `zone.run` las señales cambian y la pantalla no se entera.
    r.onresult = (evento: any) => {
      let frase = '';
      for (let i = evento.resultIndex; i < evento.results.length; i++) {
        frase += evento.results[i][0].transcript;
      }
      ultima = frase.trim();
      this.zone.run(() => this.texto.set(ultima));
    };

    r.onerror = (evento: any) => {
      this.zone.run(() => {
        this.escuchando.set(false);
        this.error.set(this.explicar(evento.error));
      });
    };

    r.onend = () => {
      this.zone.run(() => {
        this.escuchando.set(false);
        // `onend` llega también cuando se corta solo por silencio. Solo se
        // interpreta si de verdad se escuchó algo: mandar una cadena vacía
        // haría que el servidor conteste «no entendí» a alguien que no dijo
        // nada, lo cual se lee como un fallo.
        if (ultima.length >= 2) alTerminar(ultima);
      });
    };

    try {
      r.start();
    } catch {
      this.escuchando.set(false);
      this.error.set('No se pudo iniciar el micrófono.');
    }
  }

  detener(): void {
    try {
      this.reconocimiento?.stop();
    } catch {
      /* ya estaba detenido */
    }
    this.escuchando.set(false);
  }

  /** Los errores de la API son códigos; acá se vuelven algo accionable. */
  private explicar(codigo: string): string {
    switch (codigo) {
      case 'not-allowed':
      case 'service-not-allowed':
        return 'El navegador bloqueó el micrófono. Permitilo y probá de nuevo.';
      case 'no-speech':
        return 'No se escuchó nada. Probá de nuevo, más cerca del micrófono.';
      case 'audio-capture':
        return 'No se encontró ningún micrófono.';
      case 'network':
        return 'El reconocimiento de voz necesita conexión.';
      default:
        return 'No se pudo escuchar. Escribí el pedido si preferís.';
    }
  }
}
