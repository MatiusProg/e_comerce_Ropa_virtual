import { Component, OnInit, computed, inject, input, signal, viewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { debounceTime, distinctUntilChanged, filter, switchMap } from 'rxjs/operators';

import {
  ContratacionService,
  type ErrorContratacion,
} from '../../core/services/contratacion.service';
import type {
  CiudadPublica,
  Contratacion,
  PlanPublico,
} from '../../core/models/contratacion.models';
import { PATRON_SLUG } from '../../core/models/plataforma.models';
import { recordarEmpresa } from '../../core/empresa-recordada';
import { BsPipe, formatoBs } from '../../shared/bs.pipe';

/** «Moda Andina S.R.L.» → «moda-andina-s-r-l». La regla del slug (RN-14). */
function aSlug(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
    .replace(/-+$/, '');
}

/** Una cuadrícula de QR de adorno, estable para el mismo texto: el pago es simulado. */
function celdasQr(semilla: string, lado = 21): boolean[] {
  let h = 2166136261;
  for (const c of semilla) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  const celdas: boolean[] = [];
  for (let i = 0; i < lado * lado; i++) {
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    const fila = Math.floor(i / lado);
    const col = i % lado;
    const enEsquina = (f: number, c: number) => f < 7 && c < 7;
    const marco =
      enEsquina(fila, col) || enEsquina(fila, lado - 1 - col) || enEsquina(lado - 1 - fila, col);
    if (marco) {
      const f = fila < 7 ? fila : lado - 1 - fila;
      const c = col < 7 ? col : lado - 1 - col;
      celdas.push(f === 0 || f === 6 || c === 0 || c === 6 || (f > 1 && f < 5 && c > 1 && c < 5));
    } else {
      celdas.push((h & 1) === 1);
    }
  }
  return celdas;
}

const CODIGO_RECHAZO = '000000';

/**
 * CU-11 · Contratar un plan desde la web — «boundary» FormularioContratacion.
 *
 * Paso 4: los datos de la empresa, el slug, la sucursal y el administrador.
 * Paso 5: el slug se verifica mientras se escribe y, si está ocupado, se
 * sugieren otros (5a). Paso 6: el pago por QR simulado; rechazado, no se crea
 * nada (6a). Paso 8: el comprobante y el acceso con el slug.
 */
@Component({
  selector: 'app-contratar',
  imports: [
    BsPipe,
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatStepperModule,
  ],
  templateUrl: './contratar.html',
  styleUrl: './contratar.scss',
})
export class Contratar implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ContratacionService);
  private readonly router = inject(Router);

  /** El `:codigo` del plan elegido en la página de planes. */
  readonly codigo = input.required<string>();

  private readonly pasos = viewChild(MatStepper);

  protected readonly cargando = signal(true);
  protected readonly plan = signal<PlanPublico | null>(null);
  protected readonly ciudades = signal<CiudadPublica[]>([]);
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly resultado = signal<Contratacion | null>(null);
  protected readonly verContrasena = signal(false);

  /** Paso 5: el estado del slug que se está escribiendo. */
  protected readonly slug = signal<{
    estado: 'vacio' | 'verificando' | 'libre' | 'ocupado' | 'invalido';
    sugerencias: string[];
  }>({ estado: 'vacio', sugerencias: [] });
  private slugEditado = false;

  protected readonly empresa = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(120)]],
    razon_social: ['', Validators.maxLength(160)],
    nit: ['', Validators.maxLength(30)],
    correo_contacto: ['', [Validators.email, Validators.maxLength(120)]],
    slug: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(40),
        Validators.pattern(PATRON_SLUG),
      ],
    ],
  });

  protected readonly cuenta = this.fb.nonNullable.group({
    ciudad_id: this.fb.control<number | null>(null, Validators.required),
    sucursal: ['Casa matriz', [Validators.required, Validators.maxLength(80)]],
    direccion: ['', [Validators.required, Validators.maxLength(200)]],
    nombres: ['', [Validators.required, Validators.maxLength(80)]],
    apellidos: ['', [Validators.required, Validators.maxLength(80)]],
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
    contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(128),
        Validators.pattern(/^(?=.*[A-Za-z])(?=.*\d).+$/),
      ],
    ],
  });

  protected readonly pago = this.fb.nonNullable.group({
    codigo_operacion: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
  });

  protected readonly monto = computed(() => {
    const p = this.plan();
    return p ? (p.precio_mensual * p.duracion_dias) / 30 : 0;
  });

  private readonly slugActual = toSignal(this.empresa.controls.slug.valueChanges, {
    initialValue: '',
  });
  protected readonly qr = computed(() => celdasQr(`${this.slugActual()}|${this.monto()}`));
  protected readonly codigoRechazo = CODIGO_RECHAZO;

  ngOnInit(): void {
    this.api.planes().subscribe({
      next: (planes) => {
        this.plan.set(planes.find((p) => p.codigo === this.codigo().toUpperCase()) ?? null);
        this.cargando.set(false);
      },
      error: (e: ErrorContratacion) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
    this.api.ciudades().subscribe({ next: (c) => this.ciudades.set(c) });

    // El slug sale del nombre hasta que la persona lo toca.
    this.empresa.controls.nombre.valueChanges.subscribe((nombre) => {
      if (!this.slugEditado) this.empresa.controls.slug.setValue(aSlug(nombre));
    });

    // Paso 5: se verifica mientras se escribe.
    this.empresa.controls.slug.valueChanges
      .pipe(
        debounceTime(400),
        distinctUntilChanged(),
        filter((valor) => {
          if (!valor) {
            this.slug.set({ estado: 'vacio', sugerencias: [] });
            return false;
          }
          if (this.empresa.controls.slug.invalid) {
            this.slug.set({ estado: 'invalido', sugerencias: [] });
            return false;
          }
          this.slug.set({ estado: 'verificando', sugerencias: [] });
          return true;
        }),
        switchMap((valor) => this.api.verificarSlug(valor)),
      )
      .subscribe({
        next: (r) => {
          if (r.slug !== this.empresa.controls.slug.value) return;
          this.slug.set({ estado: r.disponible ? 'libre' : 'ocupado', sugerencias: r.sugerencias });
          if (!r.disponible) this.empresa.controls.slug.setErrors({ ocupado: true });
        },
      });
  }

  protected tocarSlug(): void {
    this.slugEditado = true;
  }

  protected usarSlug(sugerido: string): void {
    this.slugEditado = true;
    this.empresa.controls.slug.setValue(sugerido);
    this.empresa.controls.slug.markAsTouched();
  }

  protected montoTexto(): string {
    return formatoBs(this.monto());
  }

  /** Pasos 5 a 8. */
  protected contratar(): void {
    const plan = this.plan();
    if (!plan || this.empresa.invalid || this.cuenta.invalid || this.pago.invalid) {
      this.pago.markAllAsTouched();
      return;
    }
    const e = this.empresa.getRawValue();
    const c = this.cuenta.getRawValue();
    const vacio = (v: string) => (v.trim() === '' ? null : v.trim());
    this.enviando.set(true);
    this.error.set(null);
    this.api
      .contratar({
        nombre: e.nombre.trim(),
        razon_social: vacio(e.razon_social),
        nit: vacio(e.nit),
        slug: e.slug,
        correo_contacto: vacio(e.correo_contacto),
        plan_codigo: plan.codigo,
        sucursal: { ciudad_id: c.ciudad_id!, nombre: c.sucursal.trim(), direccion: c.direccion.trim() },
        administrador: {
          correo: c.correo.trim().toLowerCase(),
          nombres: c.nombres.trim(),
          apellidos: c.apellidos.trim(),
          contrasena: c.contrasena,
        },
        pago: { metodo: 'QR', codigo_operacion: this.pago.getRawValue().codigo_operacion },
      })
      .subscribe({
        next: (r) => {
          this.enviando.set(false);
          recordarEmpresa(r.slug);
          this.resultado.set(r);
        },
        error: (err: ErrorContratacion) => {
          this.enviando.set(false);
          if (err.tipo === 'slug-ocupado') {
            // 5a: alguien se lo llevó entre la verificación y el pago.
            this.slug.set({ estado: 'ocupado', sugerencias: err.sugerencias });
            this.empresa.controls.slug.setErrors({ ocupado: true });
            const pasos = this.pasos();
            if (pasos) pasos.selectedIndex = 0;
          }
          this.error.set(err.mensaje);
        },
      });
  }

  protected irALogin(): void {
    this.router.navigate(['/login']);
  }
}
