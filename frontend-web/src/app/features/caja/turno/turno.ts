import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CajaService, type ErrorCaja } from '../../../core/services/caja.service';
import type { Caja, Turno as TurnoModelo } from '../../../core/models/caja.models';

/**
 * CU-30 · Abrir y cerrar caja — «boundary» PantallaTurno.
 *
 * Una sola pantalla con dos caras, porque **el Cajero nunca está en las dos a
 * la vez**: o tiene turno abierto o no lo tiene. Partirla en dos rutas obligaría
 * a decidir a cuál entra al iniciar sesión, y esa decisión ya la tiene el
 * servidor en `/turnos/mio`.
 *
 * EL ARQUEO NO SE VALIDA CONTRA LO ESPERADO, Y ESO ES EL PUNTO
 * -------------------------------------------------------------
 * El campo de cierre acepta cualquier monto: **el arqueo es justamente la
 * diferencia**. Rechazar un conteo que no cuadra sería impedir registrar el
 * problema que el arqueo existe para registrar.
 *
 * Lo que sí hace la pantalla es **mostrar la diferencia antes de confirmar**,
 * para que quien cierra vea lo que está por declarar y no se entere después.
 */
@Component({
  selector: 'app-turno',
  imports: [
    CurrencyPipe,
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './turno.html',
  styleUrl: './turno.scss',
})
export class Turno implements OnInit {
  private readonly api = inject(CajaService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly ocupado = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly cajas = signal<Caja[]>([]);
  /** El turno recién cerrado, para mostrar su arqueo antes de volver a empezar. */
  protected readonly cerrado = signal<TurnoModelo | null>(null);

  protected readonly turno = this.api.turno;

  protected readonly cajaElegida = signal<number | null>(null);
  protected readonly montoApertura = new FormControl('0', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)],
  });
  protected readonly montoCierre = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)],
  });

  /** Las cajas que se pueden abrir. Las ocupadas se muestran, apagadas. */
  protected readonly libres = computed(() => this.cajas().filter((c) => !c.ocupada));
  protected readonly ocupadas = computed(() => this.cajas().filter((c) => c.ocupada));

  /**
   * La diferencia que va a quedar registrada, calculada mientras se escribe.
   *
   * Nula si todavía no hay un monto válido: mostrar «−Bs 1.234,00» porque la
   * persona escribió el primer dígito sería alarmarla por nada.
   */
  protected readonly diferencia = computed(() => {
    const t = this.turno();
    if (!t) return null;
    const contado = this.aNumero(this.montoCierre.value);
    if (contado === null) return null;
    return contado - Number(t.monto_esperado);
  });

  ngOnInit(): void {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.miTurno().subscribe({
      next: (t) => {
        if (t === null) this.cargarCajas();
        else this.cargando.set(false);
      },
      error: (e: ErrorCaja) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  private cargarCajas(): void {
    this.api.cajas().subscribe({
      next: (filas) => {
        this.cajas.set(filas);
        const libre = filas.find((c) => !c.ocupada);
        // Si hay una sola libre no tiene sentido hacerla elegir.
        if (libre) this.cajaElegida.set(libre.id);
        this.cargando.set(false);
      },
      error: (e: ErrorCaja) => {
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });
  }

  protected elegir(caja: Caja): void {
    if (caja.ocupada) return;
    this.cajaElegida.set(caja.id);
  }

  protected abrir(): void {
    const caja = this.cajaElegida();
    if (caja === null || this.montoApertura.invalid || this.ocupado()) return;

    this.ocupado.set(true);
    this.error.set(null);
    this.cerrado.set(null);
    this.api
      .abrir({ caja_id: caja, monto_apertura: this.normalizar(this.montoApertura.value) })
      .subscribe({
        next: () => {
          this.ocupado.set(false);
          this.montoCierre.setValue('');
        },
        error: (e: ErrorCaja) => {
          this.ocupado.set(false);
          this.aviso.open(e.mensaje, 'Entendido', { duration: 6000 });
          // Si la caja se ocupó entre que se listó y se pulsó, la lista quedó
          // vieja: se vuelve a pedir en vez de dejarla mintiendo.
          if (e.tipo === 'ocupada') this.cargarCajas();
        },
      });
  }

  protected cerrar(): void {
    const t = this.turno();
    if (!t || this.montoCierre.invalid || this.ocupado()) return;

    this.ocupado.set(true);
    this.error.set(null);
    this.api
      .cerrar(t.id, { monto_cierre: this.normalizar(this.montoCierre.value) })
      .subscribe({
        next: (turno) => {
          this.ocupado.set(false);
          this.cerrado.set(turno);
          this.montoApertura.setValue('0');
          this.cargarCajas();
        },
        error: (e: ErrorCaja) => {
          this.ocupado.set(false);
          this.aviso.open(e.mensaje, 'Entendido', { duration: 6000 });
        },
      });
  }

  protected volverAEmpezar(): void {
    this.cerrado.set(null);
  }

  /**
   * De lo que se escribió a lo que entiende el servidor.
   *
   * Se acepta coma **y** punto: un teclado numérico en español produce coma, y
   * rechazar «120,50» por eso sería inventar un requisito que el cajero no
   * tiene por qué conocer.
   */
  private normalizar(valor: string): string {
    return valor.trim().replace(',', '.');
  }

  private aNumero(valor: string): number | null {
    const limpio = this.normalizar(valor);
    if (!/^\d+(\.\d{1,2})?$/.test(limpio)) return null;
    return Number(limpio);
  }
}
