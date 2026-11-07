import {
  Component,
  ElementRef,
  OnInit,
  computed,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import {
  AJUSTE_EN_PALABRAS,
  ProbadorService,
  type ErrorProbador,
  type MedidasDelCliente,
  type PrendaDelProbador,
  type PruebaDeProducto,
  type SesionProbador,
} from '../../../core/services/probador.service';
import { UrlMediaPipe } from '../../../shared/url-media.pipe';
import { environment } from '../../../../environments/environment';

/** Un punto en píxeles del lienzo. */
interface Px {
  x: number;
  y: number;
}

/**
 * Qué fracción del contorno de busto mide el ancho de hombros, de punta a
 * punta (biacromial). Para el cuerpo se usa con el busto del cliente y para la
 * prenda con el busto de la talla: la RAZÓN entre los dos es la misma que usa
 * `medidas.tallaje.factor_de_ancho`, así que la escala respeta los centímetros
 * aunque esta constante sea una aproximación antropométrica (busto 92 cm →
 * hombros de 38,6 cm, dentro del rango publicado para mujeres adultas).
 */
const HOMBROS_SOBRE_BUSTO = 0.42;

/** Lado mayor del lienzo. La foto de un teléfono es enorme y no hace falta. */
const LADO_LIENZO = 900;

/** MediaPipe Tasks Vision, por CDN de versión fija (no se agrega al bundle). */
const MEDIAPIPE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14';
const MODELO_POSE =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';

/**
 * CU-37 · Probarse una prenda con su talla real — «boundary» PantallaProbador.
 * CU-38 · Generar foto realista de la prueba (botón de esta misma pantalla).
 *
 * LA DIFERENCIA CON UN PROBADOR GENERATIVO
 * ----------------------------------------
 * La prenda NO se acomoda al cuerpo. Se dibuja a su tamaño real: los hombros
 * de la foto (detectados con MediaPipe Pose, o marcados a mano) y el busto del
 * cliente dicen cuántos píxeles es un centímetro de su cuerpo; los puntos que
 * marcó el administrador (CU-36) y los centímetros de la talla dicen cuántos
 * píxeles tiene que medir la prenda. Si la talla le queda grande, se VE grande.
 *
 * La foto del cliente no sale de su navegador para probarse: solo sube una
 * imagen si pide la foto realista del CU-38.
 */
@Component({
  selector: 'app-probador',
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
    RouterLink,
    UrlMediaPipe,
  ],
  templateUrl: './probador.html',
  styleUrl: './probador.scss',
})
export class Probador implements OnInit {
  /** El `:id` de la ruta (withComponentInputBinding). */
  readonly id = input.required<string>();

  private readonly api = inject(ProbadorService);
  private readonly aviso = inject(MatSnackBar);
  private readonly lienzo = viewChild<ElementRef<HTMLCanvasElement>>('lienzo');

  protected readonly palabras = AJUSTE_EN_PALABRAS;

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly prueba = signal<PruebaDeProducto | null>(null);
  protected readonly elegida = signal<PrendaDelProbador | null>(null);

  // Medidas (si el cliente no las cargó todavía)
  protected readonly medidas: MedidasDelCliente = {
    busto_cm: 0,
    cintura_cm: 0,
    cadera_cm: 0,
    altura_cm: null,
  };
  protected readonly guardandoMedidas = signal(false);
  protected readonly errorMedidas = signal<string | null>(null);

  // La foto y los hombros
  private foto: HTMLImageElement | null = null;
  private readonly prendas = new Map<string, HTMLImageElement>();
  protected readonly hayFoto = signal(false);
  protected readonly hombros = signal<Px[]>([]);
  protected readonly metodo = signal<'POSE' | 'MANUAL'>('MANUAL');
  protected readonly detectando = signal(false);
  protected readonly avisoPose = signal<string | null>(null);
  protected readonly aproximado = signal(false);

  // La prueba registrada y la foto realista
  protected readonly sesion = signal<SesionProbador | null>(null);
  protected readonly guardando = signal(false);
  protected readonly generando = signal(false);
  protected readonly errorFoto = signal<string | null>(null);
  protected readonly misPruebas = signal<SesionProbador[]>([]);

  protected readonly tallas = computed(() => {
    const vistas = new Map<number, string>();
    for (const p of this.prueba()?.prendas ?? []) vistas.set(p.talla_id, p.talla);
    return [...vistas.entries()].map(([id, codigo]) => ({ id, codigo }));
  });

  protected readonly colores = computed(() => {
    const talla = this.elegida()?.talla_id;
    return (this.prueba()?.prendas ?? []).filter((p) => p.talla_id === talla);
  });

  protected readonly ajusteElegido = computed(() => {
    const talla = this.elegida()?.talla_id;
    return this.prueba()?.ajuste.tallas.find((t) => t.talla_id === talla) ?? null;
  });

  protected readonly listaParaProbar = computed(
    () => this.hayFoto() && this.hombros().length === 2 && !!this.elegida(),
  );

  ngOnInit(): void {
    this.cargar();
    this.cargarMisPruebas();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.api.prueba(Number(this.id())).subscribe({
      next: (p) => {
        this.prueba.set(p);
        const recomendada = p.prendas.find((x) => x.talla_id === p.ajuste.talla_recomendada_id);
        if (!this.elegida()) this.elegida.set(recomendada ?? p.prendas[0] ?? null);
        this.cargando.set(false);
        this.dibujar();
      },
      error: (e: ErrorProbador) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  private cargarMisPruebas(): void {
    this.api.misPruebas().subscribe({
      next: (lista) =>
        this.misPruebas.set(lista.filter((s) => s.producto_id === Number(this.id()))),
      error: () => undefined,
    });
  }

  // --- Medidas -------------------------------------------------------------

  protected guardarMedidas(): void {
    const m = this.medidas;
    if (!m.busto_cm || !m.cintura_cm || !m.cadera_cm) {
      this.errorMedidas.set('Cargá busto, cintura y cadera.');
      return;
    }
    if (this.guardandoMedidas()) return;
    this.guardandoMedidas.set(true);
    this.errorMedidas.set(null);
    this.api.guardarMisMedidas({ ...m, altura_cm: m.altura_cm || null }).subscribe({
      next: () => {
        this.guardandoMedidas.set(false);
        this.cargar();
      },
      error: (e: ErrorProbador) => {
        this.guardandoMedidas.set(false);
        this.errorMedidas.set(e.mensaje);
      },
    });
  }

  // --- Talla y color -------------------------------------------------------

  protected elegirTalla(tallaId: number): void {
    const actual = this.elegida();
    const prendas = this.prueba()?.prendas ?? [];
    const mismoColor = prendas.find(
      (p) => p.talla_id === tallaId && p.color_id === actual?.color_id,
    );
    this.cambiarPrenda(mismoColor ?? prendas.find((p) => p.talla_id === tallaId) ?? null);
  }

  protected cambiarPrenda(prenda: PrendaDelProbador | null): void {
    this.elegida.set(prenda);
    this.sesion.set(null); // otra talla es otra prueba
    this.errorFoto.set(null);
    this.dibujar();
  }

  // --- La foto ------------------------------------------------------------

  protected elegirFoto(evento: Event): void {
    const entrada = evento.target as HTMLInputElement;
    const archivo = entrada.files?.[0];
    if (!archivo) return;
    if (!archivo.type.startsWith('image/')) {
      this.aviso.open('Elegí una imagen.', 'Cerrar', { duration: 4000 });
      return;
    }
    const lector = new FileReader();
    lector.onload = () => {
      const img = new Image();
      img.onload = () => {
        this.foto = img;
        this.hayFoto.set(true);
        this.hombros.set([]);
        this.sesion.set(null);
        this.avisoPose.set(null);
        this.dibujar();
        void this.detectarPose();
      };
      img.src = lector.result as string;
    };
    lector.readAsDataURL(archivo);
    entrada.value = '';
  }

  /** Detecta los hombros con MediaPipe Pose. Si no puede, queda el modo a mano. */
  protected async detectarPose(): Promise<void> {
    const lienzo = this.lienzo()?.nativeElement;
    if (!this.foto || !lienzo || this.detectando()) return;
    this.detectando.set(true);
    this.avisoPose.set(null);
    try {
      const url = `${MEDIAPIPE}/vision_bundle.mjs`;
      const vision = await import(/* @vite-ignore */ url);
      const archivos = await vision.FilesetResolver.forVisionTasks(`${MEDIAPIPE}/wasm`);
      const detector = await vision.PoseLandmarker.createFromOptions(archivos, {
        baseOptions: { modelAssetPath: MODELO_POSE },
        runningMode: 'IMAGE',
        numPoses: 1,
      });
      const resultado = detector.detect(this.foto);
      detector.close();
      const puntos = resultado.landmarks?.[0];
      if (!puntos || puntos.length < 13) throw new Error('sin persona');
      const a = { x: puntos[11].x * lienzo.width, y: puntos[11].y * lienzo.height };
      const b = { x: puntos[12].x * lienzo.width, y: puntos[12].y * lienzo.height };
      this.hombros.set(a.x < b.x ? [a, b] : [b, a]);
      this.metodo.set('POSE');
      this.dibujar();
    } catch {
      this.avisoPose.set(
        'No se pudo detectar la pose automáticamente. Marcá tus dos hombros con un clic sobre la foto.',
      );
      this.metodo.set('MANUAL');
    } finally {
      this.detectando.set(false);
    }
  }

  /** Marcar los hombros a mano: dos clics. Un tercero vuelve a empezar. */
  protected marcarHombro(evento: MouseEvent): void {
    const lienzo = this.lienzo()?.nativeElement;
    if (!lienzo || !this.foto) return;
    const caja = lienzo.getBoundingClientRect();
    const punto = {
      x: ((evento.clientX - caja.left) / caja.width) * lienzo.width,
      y: ((evento.clientY - caja.top) / caja.height) * lienzo.height,
    };
    const actuales = this.hombros().length >= 2 ? [] : [...this.hombros()];
    actuales.push(punto);
    actuales.sort((p, q) => p.x - q.x);
    this.hombros.set(actuales);
    this.metodo.set('MANUAL');
    this.sesion.set(null);
    this.dibujar();
  }

  private imagenDe(prenda: PrendaDelProbador): Promise<HTMLImageElement> {
    const guardada = this.prendas.get(prenda.imagen_url);
    if (guardada?.complete) return Promise.resolve(guardada);
    return new Promise((resolver, rechazar) => {
      const img = new Image();
      // Sin esto el lienzo queda «contaminado» y no se puede exportar para el CU-38.
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        this.prendas.set(prenda.imagen_url, img);
        resolver(img);
      };
      img.onerror = rechazar;
      img.src = urlMedia(prenda.imagen_url);
    });
  }

  /** Dibuja la foto y, si hay hombros y talla, la prenda a su tamaño real. */
  protected async dibujar(): Promise<void> {
    const lienzo = this.lienzo()?.nativeElement;
    if (!lienzo || !this.foto) return;
    const escala = Math.min(1, LADO_LIENZO / Math.max(this.foto.width, this.foto.height));
    const ancho = Math.round(this.foto.width * escala);
    const alto = Math.round(this.foto.height * escala);
    if (lienzo.width !== ancho || lienzo.height !== alto) {
      lienzo.width = ancho;
      lienzo.height = alto;
    }
    const ctx = lienzo.getContext('2d')!;
    ctx.clearRect(0, 0, ancho, alto);
    ctx.drawImage(this.foto, 0, 0, ancho, alto);

    const [izq, der] = this.hombros();
    const prenda = this.elegida();
    if (izq && der && prenda) {
      try {
        const img = await this.imagenDe(prenda);
        this.superponer(ctx, img, prenda, izq, der);
      } catch {
        this.aviso.open('No se pudo cargar la imagen de la prenda.', 'Cerrar', { duration: 4000 });
      }
    }
    // Los hombros marcados, encima de todo (no van en la foto del CU-38: se
    // dibujan solo mientras no hay prenda puesta).
    if (!(izq && der && prenda)) {
      for (const h of this.hombros()) {
        ctx.beginPath();
        ctx.arc(h.x, h.y, 7, 0, Math.PI * 2);
        ctx.fillStyle = '#d81b60';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  }

  private superponer(
    ctx: CanvasRenderingContext2D,
    img: HTMLImageElement,
    prenda: PrendaDelProbador,
    izq: Px,
    der: Px,
  ): void {
    const p = prenda.puntos;
    // La prenda, en píxeles de SU imagen.
    const gIzq = { x: p.hombro_izq.x * img.width, y: p.hombro_izq.y * img.height };
    const gDer = { x: p.hombro_der.x * img.width, y: p.hombro_der.y * img.height };
    const gMedio = { x: (gIzq.x + gDer.x) / 2, y: (gIzq.y + gDer.y) / 2 };
    const gHombros = Math.hypot(gDer.x - gIzq.x, gDer.y - gIzq.y);
    const gLargo = p.ruedo.y * img.height - gMedio.y;

    // El cuerpo, en píxeles del lienzo.
    const bMedio = { x: (izq.x + der.x) / 2, y: (izq.y + der.y) / 2 };
    const bHombros = Math.hypot(der.x - izq.x, der.y - izq.y);
    const angulo = Math.atan2(der.y - izq.y, der.x - izq.x);

    const cuerpo = this.prueba()?.medidas;
    const talla = this.ajusteElegido();
    let anchoObjetivo: number;
    let largoObjetivo: number;
    if (cuerpo && talla) {
      // cm → px con el cuerpo del cliente; la prenda se dibuja con SUS cm.
      const pxPorCm = bHombros / (Number(cuerpo.busto_cm) * HOMBROS_SOBRE_BUSTO);
      anchoObjetivo = Number(talla.busto_cm) * HOMBROS_SOBRE_BUSTO * pxPorCm;
      largoObjetivo = Number(talla.largo_cm) * pxPorCm;
      this.aproximado.set(false);
    } else {
      // Sin medidas no hay escala real: tamaño aproximado, y se avisa.
      anchoObjetivo = bHombros * 1.1;
      largoObjetivo = gLargo * (anchoObjetivo / gHombros);
      this.aproximado.set(true);
    }
    const sx = anchoObjetivo / gHombros;
    const sy = largoObjetivo / gLargo;

    ctx.save();
    ctx.translate(bMedio.x, bMedio.y);
    ctx.rotate(angulo);
    ctx.scale(sx, sy);
    ctx.drawImage(img, -gMedio.x, -gMedio.y);
    ctx.restore();
  }

  // --- Registrar y foto realista ----------------------------------------------

  protected guardarPrueba(): void {
    const prenda = this.elegida();
    if (!prenda || !this.listaParaProbar() || this.guardando()) return;
    this.guardando.set(true);
    this.api.registrar(prenda.variante_id, this.metodo()).subscribe({
      next: (s) => {
        this.guardando.set(false);
        this.sesion.set(s);
        this.misPruebas.update((l) => [s, ...l]);
        this.aviso.open('Prueba guardada en «Mis pruebas».', 'Cerrar', { duration: 3000 });
      },
      error: (e: ErrorProbador) => {
        this.guardando.set(false);
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 });
      },
    });
  }

  protected generarFoto(): void {
    const prenda = this.elegida();
    const lienzo = this.lienzo()?.nativeElement;
    if (!prenda || !lienzo || !this.listaParaProbar() || this.generando()) return;
    this.generando.set(true);
    this.errorFoto.set(null);

    const conSesion = (s: SesionProbador) => {
      let blob: Promise<Blob | null>;
      try {
        blob = new Promise((r) => lienzo.toBlob(r, 'image/png'));
      } catch {
        this.generando.set(false);
        this.errorFoto.set('No se pudo exportar la composición.');
        return;
      }
      void blob.then((archivo) => {
        if (!archivo) {
          this.generando.set(false);
          this.errorFoto.set('No se pudo exportar la composición.');
          return;
        }
        this.api.generarFoto(s.id, archivo).subscribe({
          next: (actualizada) => {
            this.generando.set(false);
            this.sesion.set(actualizada);
            this.misPruebas.update((l) => [actualizada, ...l.filter((x) => x.id !== s.id)]);
            this.cargar(); // el cupo pudo agotarse
          },
          error: (e: ErrorProbador) => {
            this.generando.set(false);
            this.errorFoto.set(e.mensaje);
            if (e.plan) this.cargar();
          },
        });
      });
    };

    const actual = this.sesion();
    if (actual && !actual.foto_url) {
      conSesion(actual);
      return;
    }
    this.api.registrar(prenda.variante_id, this.metodo()).subscribe({
      next: (s) => {
        this.sesion.set(s);
        this.misPruebas.update((l) => [s, ...l]);
        conSesion(s);
      },
      error: (e: ErrorProbador) => {
        this.generando.set(false);
        this.errorFoto.set(e.mensaje);
      },
    });
  }

  protected borrar(s: SesionProbador): void {
    this.api.borrar(s.id).subscribe({
      next: () => {
        this.misPruebas.update((l) => l.filter((x) => x.id !== s.id));
        if (this.sesion()?.id === s.id) this.sesion.set(null);
      },
      error: (e: ErrorProbador) => this.aviso.open(e.mensaje, 'Cerrar', { duration: 4000 }),
    });
  }

  protected generadaPor(s: SesionProbador): string {
    const por = s.foto_generada_por ?? '';
    return por.startsWith('simulado')
      ? 'Vista simulada (sin IA generativa)'
      : `Generada con IA (${por})`;
  }
}

function urlMedia(ruta: string): string {
  if (/^https?:\/\//.test(ruta)) return ruta;
  return `${new URL(environment.apiUrl).origin}${ruta}`;
}
