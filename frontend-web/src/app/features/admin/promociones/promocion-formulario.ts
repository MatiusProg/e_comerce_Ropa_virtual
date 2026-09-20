import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

import { MaestrosService } from '../../../core/services/maestros.service';
import { ProductosService } from '../../../core/services/productos.service';
import { TemporadasService } from '../../../core/services/temporadas.service';
import type { Alcance, Promocion } from '../../../core/models/promociones.models';

/** Lo que el diálogo recibe: nada para crear, la promoción para editar. */
export interface DatosPromocion {
  promocion: Promocion | null;
}

/** Una opción del desplegable de objetivos, venga de donde venga. */
interface Objetivo {
  id: number;
  nombre: string;
}

/**
 * CU-12 · Alta y edición de una promoción.
 *
 * DOS PREGUNTAS, NO TRES CAMPOS
 * ------------------------------
 * El contrato manda `alcance` y un `objetivo_id`, en vez de tres campos
 * nulables. Es el orden en que se piensa: primero *sobre qué* —un producto,
 * una categoría, una temporada— y después *cuál*. Con tres campos, el
 * Administrador tendría que dejar dos vacíos y la pantalla tendría que
 * explicarle por qué.
 *
 * Al cambiar el alcance, la lista de objetivos se vuelve a cargar y **lo
 * elegido se borra**: dejar el identificador viejo con la lista nueva haría
 * que el formulario mandara una categoría como si fuera un producto.
 *
 * EL ALCANCE Y EL OBJETIVO NO SE EDITAN
 * --------------------------------------
 * En modo edición los dos campos se muestran apagados, con lo que hay. No se
 * esconden: quien abre a editar tiene que ver sobre qué estaba definida. El
 * servidor tampoco los acepta —cambiarle el alcance a una promoción viva es
 * otra promoción, y los pedidos ya cobrados con ella quedarían explicados por
 * una regla que ya no dice lo mismo—.
 */
@Component({
  selector: 'app-promocion-formulario',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatDatepickerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './promocion-formulario.html',
  styleUrl: './promocion-formulario.scss',
})
export class PromocionFormulario implements OnInit {
  private readonly referencia = inject(MatDialogRef<PromocionFormulario>);
  private readonly datos = inject<DatosPromocion>(MAT_DIALOG_DATA);
  private readonly maestros = inject(MaestrosService);
  private readonly productos = inject(ProductosService);
  private readonly temporadas = inject(TemporadasService);

  protected readonly editando = this.datos.promocion !== null;
  protected readonly cargandoObjetivos = signal(false);
  protected readonly objetivos = signal<Objetivo[]>([]);

  protected readonly nombre = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(2), Validators.maxLength(80)],
  });
  protected readonly alcance = new FormControl<Alcance>('CATEGORIA', {
    nonNullable: true,
    validators: [Validators.required],
  });
  protected readonly objetivoId = new FormControl<number | null>(null, {
    validators: [Validators.required],
  });
  protected readonly porcentaje = new FormControl('', {
    nonNullable: true,
    // (0, 100]. Se valida acá y en el servidor: el CHECK de la base lo rechaza
    // igual, pero como error de integridad, que se lee como «error del sistema».
    validators: [Validators.required, Validators.pattern(/^(100(\.0{1,2})?|\d{1,2}(\.\d{1,2})?)$/)],
  });
  protected readonly desde = new FormControl<Date | null>(new Date(), {
    validators: [Validators.required],
  });
  /** Nulo = sin fecha de fin. «Hasta agotar stock» no tiene fecha. */
  protected readonly hasta = new FormControl<Date | null>(null);

  private readonly alcanceElegido = toSignal(this.alcance.valueChanges, {
    initialValue: this.alcance.value,
  });

  protected readonly etiquetaObjetivo = computed(() => {
    switch (this.alcanceElegido()) {
      case 'PRODUCTO':
        return 'Qué producto';
      case 'TEMPORADA':
        return 'Qué temporada';
      default:
        return 'Qué categoría';
    }
  });

  ngOnInit(): void {
    const p = this.datos.promocion;
    if (p) {
      this.nombre.setValue(p.nombre);
      this.alcance.setValue(p.alcance);
      this.objetivoId.setValue(p.objetivo_id);
      this.porcentaje.setValue(p.porcentaje);
      this.desde.setValue(this._aFecha(p.desde));
      this.hasta.setValue(p.hasta ? this._aFecha(p.hasta) : null);
      // No se editan: se muestran con lo que hay y apagados.
      this.alcance.disable();
      this.objetivoId.disable();
      this.objetivos.set([{ id: p.objetivo_id, nombre: p.objetivo_nombre }]);
      return;
    }

    this.cargarObjetivos();
    this.alcance.valueChanges.subscribe(() => {
      // Lo elegido se borra: dejar el identificador viejo con la lista nueva
      // mandaría una categoría como si fuera un producto.
      this.objetivoId.setValue(null);
      this.cargarObjetivos();
    });
  }

  private cargarObjetivos(): void {
    this.cargandoObjetivos.set(true);
    const alcance = this.alcance.value;

    const listo = (filas: Objetivo[]) => {
      this.objetivos.set(filas);
      this.cargandoObjetivos.set(false);
    };
    const fallo = () => {
      this.objetivos.set([]);
      this.cargandoObjetivos.set(false);
    };

    if (alcance === 'CATEGORIA') {
      this.maestros.categorias().subscribe({
        next: (cs) => listo(cs.map((c) => ({ id: c.id, nombre: c.nombre }))),
        error: fallo,
      });
      return;
    }
    if (alcance === 'TEMPORADA') {
      this.temporadas.listarTemporadas().subscribe({
        next: (ts) => listo(ts.map((t) => ({ id: t.id, nombre: t.nombre }))),
        error: fallo,
      });
      return;
    }
    // Productos: se piden muchos de una porque el desplegable no pagina. Una
    // tienda con miles necesitaría un buscador; con este catálogo alcanza.
    this.productos.listar({ tamano: 200 }).subscribe({
      next: (p) => listo(p.items.map((i) => ({ id: i.id, nombre: i.nombre }))),
      error: fallo,
    });
  }

  protected get valido(): boolean {
    return (
      this.nombre.valid &&
      this.porcentaje.valid &&
      this.desde.valid &&
      (this.editando || this.objetivoId.valid) &&
      this.vigenciaCoherente
    );
  }

  /** La fecha de fin no puede ser anterior a la de inicio. */
  protected get vigenciaCoherente(): boolean {
    const d = this.desde.value;
    const h = this.hasta.value;
    if (!d || !h) return true;
    return h >= d;
  }

  protected guardar(): void {
    if (!this.valido) {
      this.nombre.markAsTouched();
      this.porcentaje.markAsTouched();
      this.objetivoId.markAsTouched();
      return;
    }

    if (this.editando) {
      this.referencia.close({
        nombre: this.nombre.value.trim(),
        porcentaje: this.porcentaje.value,
        desde: this._aTexto(this.desde.value!),
        ...(this.hasta.value
          ? { hasta: this._aTexto(this.hasta.value) }
          : { quitar_hasta: true }),
      });
      return;
    }

    this.referencia.close({
      nombre: this.nombre.value.trim(),
      alcance: this.alcance.value,
      objetivo_id: this.objetivoId.value,
      porcentaje: this.porcentaje.value,
      desde: this._aTexto(this.desde.value!),
      hasta: this.hasta.value ? this._aTexto(this.hasta.value) : null,
      activa: true,
    });
  }

  protected cancelar(): void {
    this.referencia.close();
  }

  protected quitarHasta(): void {
    this.hasta.setValue(null);
  }

  /**
   * De `Date` a `AAAA-MM-DD` **en horario local**.
   *
   * `toISOString()` pasa por UTC, y en Bolivia (UTC−4) eso le resta un día a
   * toda fecha elegida antes de las 4 de la mañana... y, peor, a cualquiera
   * cuando el navegador está en una zona negativa: el 1 de octubre se
   * guardaría como el 30 de septiembre. El servidor guarda una fecha, no un
   * instante, y esta conversión no puede inventar un huso.
   */
  private _aTexto(fecha: Date): string {
    const mes = `${fecha.getMonth() + 1}`.padStart(2, '0');
    const dia = `${fecha.getDate()}`.padStart(2, '0');
    return `${fecha.getFullYear()}-${mes}-${dia}`;
  }

  /** De `AAAA-MM-DD` a `Date` local, por el mismo motivo. */
  private _aFecha(texto: string): Date {
    const [a, m, d] = texto.split('-').map(Number);
    return new Date(a, m - 1, d);
  }
}
