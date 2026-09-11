import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { AbstractControl, FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  ConsolidadoService,
  type ErrorConsolidado,
} from '../../../core/services/consolidado.service';
import { OrganizacionService } from '../../../core/services/organizacion.service';
import type {
  EstadoExistencia,
  ExistenciaConsolidada,
  InventarioConsolidado,
  OrdenConsolidado,
} from '../../../core/models/consolidado.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';

/**
 * CU-14 · Consultar inventario consolidado — «boundary» PantallaConsolidado.
 *
 * La vista de red del Administrador: **una fila por variante**, con su reparto
 * entre sucursales desplegable.
 *
 * **Por qué es una pantalla aparte de la de inventario (CU-13 y CU-15).**
 * Aquélla responde «sobre qué fila opero»: lista el par (variante, sucursal)
 * porque un ingreso o un ajuste se hacen sobre una tienda concreta. Ésta
 * responde «cómo está repartida la prenda en la red», que es lo que permite ver
 * el desbalance entre tiendas —uno de los problemas que el proyecto dice
 * resolver— y que un listado plano obliga a reconstruir a ojo.
 *
 * Son además de personas distintas: CU-14 es de Karen por la §4.1 de la
 * contrapropuesta, por ser el único caso de uso de inventario que no escribe
 * ninguna tabla.
 */
@Component({
  selector: 'app-consolidado',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './consolidado.html',
  styleUrl: './consolidado.scss',
})
export class Consolidado implements OnInit {
  private readonly api = inject(ConsolidadoService);
  private readonly organizacion = inject(OrganizacionService);

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly datos = signal<InventarioConsolidado | null>(null);
  protected readonly sucursales = signal<SucursalBreve[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroSucursal = new FormControl<number | ''>('', {
    nonNullable: true,
  });
  protected readonly filtroEstado = new FormControl<EstadoExistencia | ''>('', {
    nonNullable: true,
  });
  protected readonly orden = new FormControl<OrdenConsolidado>('prenda', {
    nonNullable: true,
  });

  private indice = 0;
  private tamano = 20;

  private readonly version = signal(0);

  protected readonly hayFiltros = computed(() => {
    void this.version();
    return Boolean(
      this.busqueda.value || this.filtroSucursal.value || this.filtroEstado.value,
    );
  });

  /** Si se está mirando una sucursal sola, el encabezado tiene que decirlo:
   *  los totales dejan de ser «de la red» y son de esa tienda. */
  protected readonly sucursalElegida = computed(() => {
    void this.version();
    const id = this.filtroSucursal.value;
    if (!id) return null;
    return this.sucursales().find((s) => s.id === id)?.nombre ?? null;
  });

  ngOnInit(): void {
    this.organizacion.sucursales().subscribe({
      next: (sucursales) => this.sucursales.set(sucursales),
      // Perder las sucursales cuesta el filtro, no la pantalla.
      error: () => this.sucursales.set([]),
    });

    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.reiniciar());

    // `AbstractControl[]` por lo mismo que en la vitrina: tres controles con
    // tipos de valor distintos producen una unión de firmas de `subscribe` que
    // no son compatibles entre sí, y el `build` falla.
    const controles: AbstractControl[] = [
      this.filtroSucursal,
      this.filtroEstado,
      this.orden,
    ];
    for (const control of controles) {
      control.valueChanges.subscribe(() => this.reiniciar());
    }

    this.consultar();
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.tamano = evento.pageSize;
    this.consultar();
  }

  protected limpiar(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroSucursal.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.reiniciar();
  }

  protected recargar(): void {
    this.consultar();
  }

  /** El rótulo del estado, para no repetir el `switch` en la plantilla. */
  protected rotuloEstado(estado: EstadoExistencia): string {
    switch (estado) {
      case 'disponible':
        return 'Disponible';
      case 'reservada':
        return 'Reservada';
      case 'agotada':
        return 'Agotada';
      case 'proxima_a_ingresar':
        return 'Próxima a ingresar';
    }
  }

  /**
   * Si la prenda está concentrada en una sola tienda teniendo varias unidades.
   *
   * Es el desbalance que esta pantalla existe para mostrar: sesenta unidades
   * en una sucursal y cero en las otras cuatro no es lo mismo que sesenta
   * repartidas, y el número solo no lo dice.
   */
  protected estaConcentrada(fila: ExistenciaConsolidada): boolean {
    return (
      this.sucursales().length > 1 &&
      fila.sucursales_con_saldo === 1 &&
      fila.total_fisico > 1 &&
      !this.filtroSucursal.value
    );
  }

  private reiniciar(): void {
    this.indice = 0;
    this.consultar();
  }

  private consultar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.version.update((n) => n + 1);

    this.api
      .consultar({
        busqueda: this.busqueda.value || undefined,
        sucursal_id: this.filtroSucursal.value || undefined,
        estado: this.filtroEstado.value || undefined,
        orden: this.orden.value,
        pagina: this.indice + 1,
        tamano: this.tamano,
      })
      .subscribe({
        next: (datos) => {
          this.datos.set(datos);
          this.cargando.set(false);
        },
        error: (fallo: ErrorConsolidado) => {
          this.error.set(fallo.mensaje);
          this.datos.set(null);
          this.cargando.set(false);
        },
      });
  }
}
