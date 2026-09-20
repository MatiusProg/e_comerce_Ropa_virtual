import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  AbastecimientoService,
  type Anuncio,
  type ErrorAbastecimiento,
  type VarianteAnunciable,
} from '../../../core/services/abastecimiento.service';

/**
 * CU-39 · Informar disponibilidad y plazo — «boundary» PantallaAbastecimiento.
 *
 * Realiza el **RF38** y cierra el agujero H1: hasta el 20/09/2026 el estado
 * «próxima a ingresar» del inventario consolidado estaba declarado y ninguna
 * fila lo devolvía, porque nada en el sistema anunciaba lo que estaba por
 * llegar.
 *
 * LO QUE EL PROVEEDOR TIENE QUE ENTENDER SIN QUE NADIE SE LO EXPLIQUE
 * --------------------------------------------------------------------
 * Que lo que informa acá **se ve en el inventario de la tienda**. Si no, esto
 * parece un cuaderno privado y nadie lo llena. Por eso el encabezado lo dice
 * con todas las letras en vez de titular «Mis avisos» y ya.
 */
@Component({
  selector: 'app-abastecimiento',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './abastecimiento.html',
  styleUrl: './abastecimiento.scss',
})
export class Abastecimiento implements OnInit {
  private readonly api = inject(AbastecimientoService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = ['prenda', 'cantidad', 'plazo', 'estado', 'quitar'];

  /** Tres estados. «Entregado» es el que faltaba hasta el 20/09. */
  protected textoDeEstado(estado: string): string {
    if (estado === 'RECIBIDO') return 'Entregado';
    if (estado === 'CANCELADO') return 'Retirado';
    return 'Informado';
  }

  protected readonly cargando = signal(true);
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly variantes = signal<VarianteAnunciable[]>([]);
  protected readonly anuncios = signal<Anuncio[]>([]);
  protected readonly verCancelados = signal(false);

  protected readonly hayVariantes = computed(() => this.variantes().length > 0);

  protected readonly formulario = new FormGroup({
    variante_id: new FormControl<number | null>(null, Validators.required),
    cantidad: new FormControl<number>(1, [
      Validators.required,
      Validators.min(1),
      Validators.max(100000),
    ]),
    dias_plazo: new FormControl<number>(7, [
      Validators.required,
      Validators.min(0),
      Validators.max(365),
    ]),
    observacion: new FormControl<string>('', Validators.maxLength(200)),
  });

  ngOnInit(): void {
    this.api.variantes().subscribe({
      next: (lista) => this.variantes.set(lista),
      error: (e: ErrorAbastecimiento) => this.error.set(e.mensaje),
    });
    this.refrescar();
  }

  protected refrescar(): void {
    this.cargando.set(true);
    this.api.mios(this.verCancelados()).subscribe({
      next: (lista) => {
        this.anuncios.set(lista);
        this.cargando.set(false);
      },
      error: (e: ErrorAbastecimiento) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  protected alternarCancelados(ver: boolean): void {
    this.verCancelados.set(ver);
    this.refrescar();
  }

  protected etiquetaDe(v: VarianteAnunciable): string {
    return `${v.prenda} · ${v.talla} · ${v.color}`;
  }

  protected informar(): void {
    if (this.formulario.invalid || this.guardando()) return;
    this.guardando.set(true);

    const valor = this.formulario.getRawValue();
    this.api
      .informar({
        variante_id: valor.variante_id!,
        cantidad: valor.cantidad!,
        dias_plazo: valor.dias_plazo!,
        observacion: valor.observacion?.trim() || null,
      })
      .subscribe({
        next: () => {
          this.guardando.set(false);
          // Se limpia la prenda pero NO el plazo: quien informa varias
          // prendas seguidas suele darles el mismo, y volver a escribir «7»
          // cada vez es trabajo que la pantalla puede ahorrarle.
          this.formulario.patchValue({ variante_id: null, cantidad: 1, observacion: '' });
          this.aviso.open(
            'Informado. Ya figura como próxima a ingresar en el inventario.',
            'Cerrar',
            { duration: 6000 },
          );
          this.refrescar();
        },
        error: (e: ErrorAbastecimiento) => {
          this.guardando.set(false);
          this.aviso.open(e.mensaje, 'Cerrar', { duration: 8000 });
        },
      });
  }

  protected cancelar(anuncio: Anuncio): void {
    this.api.cancelar(anuncio.id).subscribe({
      next: () => {
        this.aviso.open('Aviso retirado.', 'Cerrar', { duration: 4000 });
        this.refrescar();
      },
      error: (e: ErrorAbastecimiento) =>
        this.aviso.open(e.mensaje, 'Cerrar', { duration: 7000 }),
    });
  }

  protected textoDePlazo(dias: number): string {
    if (dias === 0) return 'Disponible ahora';
    if (dias === 1) return 'En 1 día';
    return `En ${dias} días`;
  }
}
