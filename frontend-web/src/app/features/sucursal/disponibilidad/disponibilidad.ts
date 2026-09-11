import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../../core/services/auth.service';
import {
  InventarioService,
  type ErrorInventario,
} from '../../../core/services/inventario.service';
import type { Existencia } from '../../../core/models/inventario.models';
// Los dos diálogos viven en `admin/inventario` porque es donde nacieron, con
// CU-15 y CU-13. No se duplican acá ni se mueven a `shared/`: son la MISMA
// operación —el mismo endpoint, la misma regla del conteo físico— y tener dos
// copias garantizaría que algún día divergieran. Lo que cambia entre las dos
// pantallas es el alcance, y ese lo resuelve el servidor con el token.
import {
  AjusteFormulario,
  type DatosAjusteFormulario,
} from '../../admin/inventario/ajuste-formulario';
import {
  MinimoFormulario,
  type DatosMinimoFormulario,
} from '../../admin/inventario/minimo-formulario';

/**
 * CU-16 · Gestionar disponibilidad de la sucursal — «boundary»
 * PantallaDisponibilidad.
 *
 * Es la pantalla del **Encargado** sobre su propio local, y por eso no tiene
 * selector de sucursal: el servidor le acota el alcance a la suya con el ámbito
 * del token, así que ofrecerle elegir sería ofrecerle un 403.
 *
 * **Las alertas van arriba y separadas del listado**, no como una columna más.
 * Quien abre esto a primera hora viene a hacer una sola pregunta —qué tengo que
 * pedir hoy— y la respuesta no puede estar repartida entre cuarenta filas
 * ordenadas por SKU. El listado completo queda abajo, para cuando la pregunta
 * es otra.
 *
 * **No es la misma pantalla que `/admin/inventario`.** Esa está organizada
 * alrededor del movimiento —ingresos, historial, transferencias entre
 * locales—; esta, alrededor del saldo de un local. Comparten los diálogos y el
 * servicio, que es donde vive lo que de verdad se repite.
 */
@Component({
  selector: 'app-disponibilidad',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './disponibilidad.html',
  styleUrl: './disponibilidad.scss',
})
export class Disponibilidad implements OnInit {
  private readonly api = inject(InventarioService);
  private readonly auth = inject(AuthService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = [
    'sku',
    'producto',
    'disponible',
    'reservada',
    'fisica',
    'minimo',
    'acciones',
  ];
  protected readonly columnasAlerta = ['sku', 'producto', 'disponible', 'minimo', 'faltan'];

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly existencias = signal<Existencia[]>([]);
  protected readonly alertas = signal<Existencia[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly soloConSaldo = new FormControl(false, { nonNullable: true });

  /**
   * El filtro por texto se resuelve acá y no en el servidor a propósito: una
   * sucursal maneja decenas o pocos cientos de existencias, ya vienen todas, y
   * un viaje por cada letra tecleada no compra nada.
   */
  protected readonly visibles = computed(() => {
    const texto = this.textoBuscado().trim().toLowerCase();
    if (!texto) return this.existencias();
    return this.existencias().filter(
      (e) =>
        e.sku.toLowerCase().includes(texto) ||
        e.producto.toLowerCase().includes(texto) ||
        e.color.toLowerCase().includes(texto) ||
        e.talla.toLowerCase().includes(texto),
    );
  });

  private readonly textoBuscado = signal('');

  protected readonly nombreDeSucursal = computed(
    () => this.existencias()[0]?.sucursal ?? this.alertas()[0]?.sucursal ?? '',
  );

  ngOnInit(): void {
    this.refrescar();
    this.busqueda.valueChanges.subscribe((t) => this.textoBuscado.set(t));
    this.soloConSaldo.valueChanges.subscribe(() => this.refrescar());
  }

  protected refrescar(): void {
    this.cargando.set(true);

    this.api.listarExistencias({ solo_con_saldo: this.soloConSaldo.value }).subscribe({
      next: (filas) => {
        this.existencias.set(filas);
        this.error.set(null);
        this.cargando.set(false);
      },
      error: (e: ErrorInventario) => {
        this.existencias.set([]);
        this.error.set(e.mensaje);
        this.cargando.set(false);
      },
    });

    this.api.listarAlertas().subscribe({
      next: (filas) => this.alertas.set(filas),
      error: () => this.alertas.set([]),
    });
  }

  /** Cuántas unidades faltan para volver al umbral. Nunca negativo. */
  protected faltan(existencia: Existencia): number {
    return Math.max(0, existencia.stock_minimo - existencia.cantidad_disponible);
  }

  // --- Acciones -----------------------------------------------------------

  protected ajustar(existencia: Existencia): void {
    const datos: DatosAjusteFormulario = { existencia };
    this.dialogo
      .open(AjusteFormulario, { data: datos, width: '560px', disableClose: true })
      .afterClosed()
      .subscribe((ajuste) => {
        if (!ajuste) return;
        const signo = ajuste.diferencia > 0 ? '+' : '';
        this.aviso.open(
          `Ajuste registrado: ${signo}${ajuste.diferencia} unidades.`,
          'Cerrar',
          { duration: 6000 },
        );
        this.refrescar();
      });
  }

  protected fijarMinimo(existencia: Existencia): void {
    const datos: DatosMinimoFormulario = { existencia };
    this.dialogo
      .open(MinimoFormulario, { data: datos, width: '520px', disableClose: true })
      .afterClosed()
      .subscribe((actualizada) => {
        if (!actualizada) return;
        this.aviso.open(
          actualizada.stock_minimo === 0
            ? `${actualizada.sku} deja de vigilarse.`
            : `${actualizada.sku} avisará cuando queden ${actualizada.stock_minimo} o menos.`,
          'Cerrar',
          { duration: 5000 },
        );
        this.refrescar();
      });
  }
}
