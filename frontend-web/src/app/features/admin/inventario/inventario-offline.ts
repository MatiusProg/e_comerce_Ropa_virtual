import { Component, computed, inject, output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { OfflineService } from '../../../core/services/offline.service';
import type { EstadoLocal, PrendaDeInventario } from '../../../core/models/offline.models';

/** Lo mismo que `MOTIVO_LONGITUD_MINIMA` del backend. */
const MOTIVO_MINIMO = 5;

const ETIQUETAS: Record<EstadoLocal, string> = {
  local: 'Guardada en este equipo',
  enviada: 'Esperando al servidor',
  confirmada: 'Confirmada',
  rechazada: 'Rechazada',
  en_conflicto: 'En conflicto',
};

/**
 * CU-21 · Inventario sin conexión — «boundary» PanelInventarioOffline.
 *
 * Solo para el Encargado. Descarga las prendas de su sucursal con su saldo y
 * los proveedores; sin red, registra ingresos y conteos en el navegador
 * (IndexedDB) y los manda por la misma cola de CU-17 cuando vuelve la red.
 *
 * EL CONTEO VIAJA COMO «LO QUE SE VEÍA» Y «LO QUE SE CONTÓ»
 * --------------------------------------------------------
 * El servidor aplica la diferencia, no lo contado: si mientras el encargado
 * contaba sin red se vendieron prendas en línea, esas ventas no se pisan.
 */
@Component({
  selector: 'app-inventario-offline',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  template: `
    <mat-card class="panel vb-filete-superior" appearance="outlined">
      <div class="cabecera">
        <div class="estado" [class.sin-red]="!offline.enLinea()">
          <mat-icon>{{ offline.enLinea() ? 'cloud_done' : 'cloud_off' }}</mat-icon>
          <div>
            <strong>{{ offline.enLinea() ? 'En línea' : 'Sin conexión' }}</strong>
            <span class="detalle">
              @if (offline.paqueteInventario(); as p) {
                Inventario preparado el {{ p.generado_en | date: 'dd/MM HH:mm' }}
                @if (vencido()) { · <span class="viejo">puede estar desactualizado</span> }
              } @else {
                Todavía no se preparó este equipo para trabajar sin conexión.
              }
            </span>
          </div>
        </div>
        <div class="botones">
          @if (pendientes().length) {
            <button matButton="outlined" type="button" [disabled]="offline.sincronizando()" (click)="sincronizar()">
              <mat-icon>sync</mat-icon>
              Sincronizar ({{ pendientes().length }})
            </button>
          }
          <button matButton type="button" [disabled]="!offline.enLinea() || preparando()" (click)="preparar()">
            <mat-icon>download_for_offline</mat-icon>
            {{ offline.paqueteInventario() ? 'Actualizar datos' : 'Preparar sin conexión' }}
          </button>
          @if (offline.paqueteInventario() && offline.enLinea()) {
            <button matButton type="button" (click)="abierto.set(!abierto())">
              <mat-icon>{{ trabajando() ? 'expand_less' : 'expand_more' }}</mat-icon>
              Registrar sin conexión
            </button>
          }
        </div>
      </div>

      @if (trabajando()) {
        @if (offline.paqueteInventario(); as paquete) {
          <!-- ===== Ingreso sin red ===== -->
          @if (modo() === 'ingreso') {
            <section class="formulario">
              <h3>Ingreso de mercadería sin conexión</h3>
              <div class="fila">
                <mat-form-field appearance="outline">
                  <mat-label>Proveedor</mat-label>
                  <mat-select [formControl]="proveedor">
                    @for (p of paquete.proveedores; track p.id) {
                      <mat-option [value]="p.id">{{ p.razon_social }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Remito (opcional)</mat-label>
                  <input matInput maxlength="40" [formControl]="remito" />
                </mat-form-field>
              </div>
              @for (l of lineas(); track l.prenda.variante_id) {
                <div class="linea">
                  <span><code>{{ l.prenda.sku }}</code> {{ l.prenda.producto }} · {{ l.prenda.talla }} · {{ l.prenda.color }}</span>
                  <span>+{{ l.cantidad }}</span>
                  <button matIconButton type="button" matTooltip="Quitar" (click)="quitarLinea(l.prenda.variante_id)">
                    <mat-icon>close</mat-icon>
                  </button>
                </div>
              } @empty {
                <p class="detalle">Agregue prendas desde la lista de abajo con el botón «+».</p>
              }
              <div class="acciones">
                <button matButton type="button" (click)="cancelar()">Cancelar</button>
                <button matButton="filled" class="vb-boton-marca" type="button"
                        [disabled]="guardando() || !proveedor.value || !lineas().length" (click)="guardarIngreso()">
                  Guardar ingreso
                </button>
              </div>
            </section>
          }

          <!-- ===== Conteo sin red ===== -->
          @if (contando(); as prenda) {
            <section class="formulario">
              <h3>Conteo físico sin conexión</h3>
              <p>
                <code>{{ prenda.sku }}</code> {{ prenda.producto }} · {{ prenda.talla }} · {{ prenda.color }}.
                Este equipo ve <strong>{{ fisica(prenda) }}</strong> en el local
                ({{ prenda.disponible }} disponibles y {{ prenda.reservada }} reservadas).
              </p>
              <div class="fila">
                <mat-form-field appearance="outline">
                  <mat-label>Unidades contadas</mat-label>
                  <input matInput type="number" min="0" [formControl]="contado" />
                  <mat-hint>Cuente todo lo que hay en la percha, reservadas incluidas.</mat-hint>
                </mat-form-field>
                <mat-form-field appearance="outline" class="ancho">
                  <mat-label>Motivo</mat-label>
                  <input matInput maxlength="200" [formControl]="motivo" />
                </mat-form-field>
              </div>
              @if (diferencia() !== null) {
                <p class="detalle">
                  Diferencia: <strong>{{ diferencia()! > 0 ? '+' : '' }}{{ diferencia() }}</strong>.
                  Al sincronizar se aplica esta diferencia, no lo contado: las ventas
                  que lleguen mientras tanto no se pisan.
                </p>
              }
              <div class="acciones">
                <button matButton type="button" (click)="cancelar()">Cancelar</button>
                <button matButton="filled" class="vb-boton-marca" type="button"
                        [disabled]="guardando() || contado.invalid || motivo.invalid" (click)="guardarConteo(prenda)">
                  Guardar conteo
                </button>
              </div>
            </section>
          }

          <!-- ===== Prendas del paquete ===== -->
          <section class="prendas">
            <div class="fila">
              <mat-form-field appearance="outline" class="ancho">
                <mat-label>Buscar prenda</mat-label>
                <input matInput [formControl]="busqueda" placeholder="SKU o nombre" />
              </mat-form-field>
              @if (modo() !== 'ingreso') {
                <button matButton="filled" class="vb-boton-marca" type="button" (click)="empezarIngreso()">
                  <mat-icon>local_shipping</mat-icon>
                  Ingreso sin conexión
                </button>
              }
            </div>
            <div class="lista">
              @for (p of filtradas(); track p.variante_id) {
                <div class="prenda">
                  <span><code>{{ p.sku }}</code> {{ p.producto }} · {{ p.talla }} · {{ p.color }}</span>
                  <span class="saldo">{{ p.disponible }} disp. · {{ p.reservada }} res.</span>
                  @if (modo() === 'ingreso') {
                    <input class="cantidad" type="number" min="1" value="1" #cant aria-label="Cantidad" />
                    <button matIconButton type="button" matTooltip="Agregar al ingreso" (click)="agregarLinea(p, +cant.value)">
                      <mat-icon>add</mat-icon>
                    </button>
                  } @else {
                    <button matIconButton type="button" matTooltip="Contar" (click)="empezarConteo(p)">
                      <mat-icon>fact_check</mat-icon>
                    </button>
                  }
                </div>
              } @empty {
                <p class="detalle">No hay prendas que coincidan.</p>
              }
            </div>
          </section>
        }
      }

      <!-- ===== La cola de inventario ===== -->
      @if (deInventario().length) {
        <section class="cola">
          <h3>Registrado sin conexión</h3>
          @for (o of deInventario(); track o.uuid) {
            <div class="operacion" [class]="'estado-' + o.estado">
              <mat-icon>{{ o.operacion.tipo === 'INGRESO' ? 'local_shipping' : 'fact_check' }}</mat-icon>
              <div>
                <strong>{{ o.resumen }}</strong>
                <span class="detalle">
                  {{ etiqueta(o.estado) }} · {{ o.operacion.creada_en | date: 'dd/MM HH:mm' }}
                  @if (o.motivo) { · {{ o.motivo }} }
                </span>
              </div>
            </div>
          }
          @if (hayConfirmadas()) {
            <button matButton type="button" (click)="offline.limpiarConfirmadas()">Quitar las confirmadas</button>
          }
        </section>
      }
    </mat-card>
  `,
  styles: `
    .panel { margin-bottom: 16px; padding: 16px; }
    .cabecera { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; align-items: center; }
    .estado { display: flex; gap: 12px; align-items: center; }
    .estado.sin-red mat-icon { color: var(--mat-sys-error); }
    .detalle { display: block; color: var(--mat-sys-on-surface-variant); font-size: 0.875rem; }
    .viejo { color: var(--mat-sys-error); }
    .botones { display: flex; gap: 8px; flex-wrap: wrap; }
    h3 { margin: 16px 0 8px; font-size: 1rem; }
    .fila { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-start; }
    .ancho { flex: 1 1 260px; }
    .formulario { border: 1px solid var(--mat-sys-outline-variant); border-radius: 8px; padding: 12px 16px; margin-top: 12px; }
    .linea, .prenda { display: flex; gap: 12px; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--mat-sys-outline-variant); }
    .linea span:first-child, .prenda span:first-child { flex: 1; min-width: 0; }
    .saldo { color: var(--mat-sys-on-surface-variant); white-space: nowrap; }
    .cantidad { width: 64px; padding: 4px; }
    .lista { max-height: 320px; overflow-y: auto; }
    .acciones { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
    code { background: var(--mat-sys-surface-container); padding: 1px 4px; border-radius: 4px; }
    .operacion { display: flex; gap: 12px; align-items: center; padding: 6px 0; }
    .estado-rechazada mat-icon, .estado-en_conflicto mat-icon { color: var(--mat-sys-error); }
    .estado-confirmada mat-icon { color: var(--mat-sys-primary); }
  `,
})
export class InventarioOffline {
  protected readonly offline = inject(OfflineService);
  private readonly aviso = inject(MatSnackBar);

  /** Avisa a la pantalla para que recargue las existencias. */
  readonly sincronizado = output<void>();

  protected readonly preparando = signal(false);
  /**
   * Mientras se escribe en este equipo. Cada clic genera una operación con su
   * propio UUID, así que un doble clic grababa dos ingresos o dos conteos y el
   * servidor no tenía cómo saber que era el mismo.
   */
  protected readonly guardando = signal(false);
  /** En línea, el panel de trabajo se abre a pedido; sin red, siempre. */
  protected readonly abierto = signal(false);
  protected readonly trabajando = computed(
    () => !!this.offline.paqueteInventario() && (this.abierto() || !this.offline.enLinea()),
  );
  protected readonly modo = signal<'nada' | 'ingreso'>('nada');
  protected readonly contando = signal<PrendaDeInventario | null>(null);
  protected readonly lineas = signal<{ prenda: PrendaDeInventario; cantidad: number }[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  private readonly textoBusqueda = signal('');
  protected readonly proveedor = new FormControl<number | null>(null);
  protected readonly remito = new FormControl('', { nonNullable: true });
  protected readonly contado = new FormControl<number | null>(null, [
    Validators.required,
    Validators.min(0),
    // Se cuentan prendas enteras.
    Validators.pattern(/^\d+$/),
  ]);
  protected readonly motivo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(MOTIVO_MINIMO)],
  });
  private readonly valorContado = signal<number | null>(null);

  protected readonly vencido = computed(() => {
    const p = this.offline.paqueteInventario();
    return p !== null && Date.parse(p.vigente_hasta) < Date.now();
  });

  protected readonly deInventario = computed(() =>
    this.offline.operaciones().filter((o) => o.operacion.tipo === 'INGRESO' || o.operacion.tipo === 'AJUSTE'),
  );
  protected readonly pendientes = computed(() =>
    this.offline.pendientes().filter((o) => o.operacion.tipo === 'INGRESO' || o.operacion.tipo === 'AJUSTE'),
  );
  protected readonly hayConfirmadas = computed(() => this.deInventario().some((o) => o.estado === 'confirmada'));

  protected readonly filtradas = computed(() => {
    const texto = this.textoBusqueda().trim().toLowerCase();
    const prendas = this.offline.paqueteInventario()?.prendas ?? [];
    const lista = texto
      ? prendas.filter((p) => p.sku.toLowerCase().includes(texto) || p.producto.toLowerCase().includes(texto))
      : prendas;
    return lista.slice(0, 100);
  });

  protected readonly diferencia = computed(() => {
    const prenda = this.contando();
    const contado = this.valorContado();
    if (!prenda || contado === null || contado < 0) return null;
    return contado - this.fisica(prenda);
  });

  constructor() {
    this.busqueda.valueChanges.subscribe((v) => this.textoBusqueda.set(v));
    this.contado.valueChanges.subscribe((v) => this.valorContado.set(v === null ? null : Number(v)));
  }

  protected fisica(p: PrendaDeInventario): number {
    return p.disponible + p.reservada;
  }

  protected etiqueta(estado: EstadoLocal): string {
    return ETIQUETAS[estado];
  }

  protected async preparar(): Promise<void> {
    this.preparando.set(true);
    try {
      const p = await this.offline.prepararInventario();
      this.aviso.open(`Listo: ${p.prendas.length} prendas guardadas en este equipo.`, 'Cerrar', { duration: 5000 });
    } catch (e) {
      const error = e as HttpErrorResponse;
      const detalle = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo preparar el equipo.';
      this.aviso.open(detalle, 'Cerrar', { duration: 6000 });
    } finally {
      this.preparando.set(false);
    }
  }

  protected async sincronizar(): Promise<void> {
    const r = await this.offline.sincronizar();
    if (!r) return;
    this.aviso.open(`Sincronizado: ${r.confirmadas} confirmadas y ${r.rechazadas} rechazadas.`, 'Cerrar', {
      duration: 6000,
    });
    if (this.offline.enLinea()) {
      await this.offline.prepararInventario().catch(() => undefined);
    }
    this.sincronizado.emit();
  }

  // --- Ingreso ---------------------------------------------------------------

  protected empezarIngreso(): void {
    this.contando.set(null);
    this.modo.set('ingreso');
  }

  protected agregarLinea(prenda: PrendaDeInventario, cantidad: number): void {
    if (!Number.isInteger(cantidad) || cantidad < 1) return;
    this.lineas.update((ls) => {
      const otras = ls.filter((l) => l.prenda.variante_id !== prenda.variante_id);
      const previa = ls.find((l) => l.prenda.variante_id === prenda.variante_id)?.cantidad ?? 0;
      return [...otras, { prenda, cantidad: previa + cantidad }];
    });
  }

  protected quitarLinea(variante_id: number): void {
    this.lineas.update((ls) => ls.filter((l) => l.prenda.variante_id !== variante_id));
  }

  protected async guardarIngreso(): Promise<void> {
    const proveedor_id = this.proveedor.value;
    const lineas = this.lineas();
    if (!proveedor_id || !lineas.length || this.guardando()) return;
    const nombre =
      this.offline.paqueteInventario()?.proveedores.find((p) => p.id === proveedor_id)?.razon_social ?? '';
    const unidades = lineas.reduce((t, l) => t + l.cantidad, 0);
    this.guardando.set(true);
    try {
      await this.offline.registrarIngresoOffline(
        {
          proveedor_id,
          referencia: this.remito.value.trim() || null,
          lineas: lineas.map((l) => ({ variante_id: l.prenda.variante_id, cantidad: l.cantidad })),
        },
        `Ingreso de ${nombre}: ${unidades} unidades`,
      );
    } catch {
      this.aviso.open('No se pudo guardar el ingreso en este equipo. Intente de nuevo.', 'Cerrar', { duration: 6000 });
      return;
    } finally {
      this.guardando.set(false);
    }
    this.aviso.open('Ingreso guardado en este equipo. Se confirma al sincronizar.', 'Cerrar', { duration: 5000 });
    this.cancelar();
    if (this.offline.enLinea()) void this.sincronizar();
  }

  // --- Conteo ----------------------------------------------------------------

  protected empezarConteo(prenda: PrendaDeInventario): void {
    this.modo.set('nada');
    this.contando.set(prenda);
    this.contado.reset(null);
    this.motivo.reset('');
  }

  protected async guardarConteo(prenda: PrendaDeInventario): Promise<void> {
    if (this.guardando()) return;
    const contado = Number(this.contado.value);
    this.guardando.set(true);
    try {
      await this.offline.registrarConteoOffline(
        {
          variante_id: prenda.variante_id,
          saldo_visto: this.fisica(prenda),
          cantidad_contada: contado,
          motivo: this.motivo.value.trim(),
        },
        `Conteo de ${prenda.sku}: se veían ${this.fisica(prenda)}, se contaron ${contado}`,
      );
    } catch {
      this.aviso.open('No se pudo guardar el conteo en este equipo. Intente de nuevo.', 'Cerrar', { duration: 6000 });
      return;
    } finally {
      this.guardando.set(false);
    }
    this.aviso.open('Conteo guardado en este equipo. Se confirma al sincronizar.', 'Cerrar', { duration: 5000 });
    this.cancelar();
    if (this.offline.enLinea()) void this.sincronizar();
  }

  protected cancelar(): void {
    this.modo.set('nada');
    this.contando.set(null);
    this.lineas.set([]);
    this.proveedor.reset(null);
    this.remito.reset('');
  }
}
