import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { EmpleadosService, type ErrorEmpleados } from '../../../core/services/empleados.service';
import { OrganizacionService } from '../../../core/services/organizacion.service';
import {
  ETIQUETA_CARGO,
  type Cargo,
  type Empleado,
} from '../../../core/models/empleados.models';
import type { SucursalBreve } from '../../../core/models/organizacion.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { EmpleadoFormulario, type DatosFormularioEmpleado } from './empleado-formulario';

/**
 * CU-06 · Gestionar empleados — «boundary» PantallaEmpleados.
 *
 * Realiza el paso 2 (listado con filtro por sucursal y por cargo) y ofrece las
 * acciones de los flujos alternativos 3a (editar y reasignar) y 3b (dar de
 * baja). El 3c vive dentro del formulario.
 */
@Component({
  selector: 'app-empleados',
  imports: [
    ReactiveFormsModule,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './empleados.html',
  styleUrl: './empleados.scss',
})
export class Empleados implements OnInit {
  private readonly api = inject(EmpleadosService);
  private readonly organizacion = inject(OrganizacionService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = [
    'empleado',
    'cargo',
    'sucursal',
    'ingreso',
    'estado',
    'acciones',
  ];

  /**
   * Nombre legible de un cargo.
   *
   * Es un método y no un acceso directo al mapa porque las filas de
   * `mat-table` llegan a la plantilla sin tipo, y en modo estricto no pueden
   * indexar un `Record<Cargo, string>`.
   */
  protected nombreCargo(cargo: string): string {
    return ETIQUETA_CARGO[cargo as Cargo] ?? cargo;
  }

  protected readonly cargando = signal(false);
  protected readonly empleados = signal<Empleado[]>([]);
  protected readonly sucursales = signal<SucursalBreve[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroSucursal = new FormControl<number | ''>('', {
    nonNullable: true,
  });
  protected readonly filtroCargo = new FormControl<string>('', { nonNullable: true });
  protected readonly filtroEstado = new FormControl<string>('', { nonNullable: true });

  protected get hayFiltros(): boolean {
    return Boolean(
      this.busqueda.value ||
        this.filtroSucursal.value !== '' ||
        this.filtroCargo.value ||
        this.filtroEstado.value,
    );
  }

  ngOnInit(): void {
    // El selector de sucursal del filtro y el del formulario salen de la misma
    // consulta. `sucursales()` devuelve solo las activas, que es exactamente lo
    // que la excepción E2 permite asignar.
    this.organizacion.sucursales().subscribe({
      next: (s) => this.sucursales.set(s),
      error: () => this.sucursales.set([]),
    });

    this.busqueda.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe(() => this.cargar());

    // Se suscriben de a uno y no en un bucle: los tres controles tienen tipos
    // de valor distintos, y TypeScript no unifica las firmas de `subscribe`
    // sobre el array heterogéneo.
    this.filtroSucursal.valueChanges.subscribe(() => this.cargar());
    this.filtroCargo.valueChanges.subscribe(() => this.cargar());
    this.filtroEstado.valueChanges.subscribe(() => this.cargar());

    this.cargar();
  }

  /** Paso 2 del flujo principal. */
  protected cargar(): void {
    this.cargando.set(true);

    const estado = this.filtroEstado.value;
    this.api
      .listar({
        busqueda: this.busqueda.value || undefined,
        sucursal_id:
          this.filtroSucursal.value === '' ? undefined : Number(this.filtroSucursal.value),
        cargo: (this.filtroCargo.value || undefined) as Cargo | undefined,
        activo: estado === '' ? undefined : estado === 'activos',
      })
      .subscribe({
        next: (lista) => {
          this.empleados.set(lista);
          this.cargando.set(false);
        },
        error: (e: ErrorEmpleados) => {
          this.cargando.set(false);
          this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 });
        },
      });
  }

  protected limpiarFiltros(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroSucursal.setValue('', { emitEvent: false });
    this.filtroCargo.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.cargar();
  }

  protected nuevo(): void {
    this.abrirFormulario({ sucursales: this.sucursales(), empleado: null });
  }

  /** Flujo alternativo 3a. */
  protected editar(empleado: Empleado): void {
    this.abrirFormulario({ sucursales: this.sucursales(), empleado });
  }

  private abrirFormulario(datos: DatosFormularioEmpleado): void {
    this.dialogo
      .open<EmpleadoFormulario, DatosFormularioEmpleado, boolean>(EmpleadoFormulario, {
        width: '640px',
        maxWidth: '94vw',
        data: datos,
      })
      .afterClosed()
      .subscribe((guardado) => {
        if (!guardado) return;
        this.cargar();
        this.aviso.open(
          datos.empleado ? 'Empleado actualizado.' : 'Empleado registrado.',
          'Cerrar',
          { duration: 3500 },
        );
      });
  }

  /**
   * Flujo alternativo 3b.
   *
   * Se confirma antes porque no hay vuelta atrás en esta pantalla: la baja
   * desactiva la cuenta y corta el acceso del empleado en el acto.
   */
  protected darDeBaja(empleado: Empleado): void {
    const datos: DatosConfirmacion = {
      titulo: 'Dar de baja al empleado',
      mensaje:
        `${empleado.nombres} ${empleado.apellidos} dejará de figurar en ` +
        `${empleado.sucursal}. Su cuenta se desactiva y sus sesiones abiertas se ` +
        `cierran en el acto.`,
      confirmar: 'Dar de baja',
      peligrosa: true,
    };

    this.dialogo
      .open<Confirmacion, DatosConfirmacion, boolean>(Confirmacion, { data: datos })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.api.darDeBaja(empleado.id).subscribe({
          next: () => {
            this.cargar();
            this.aviso.open('Empleado dado de baja.', 'Cerrar', { duration: 3500 });
          },
          error: (e: ErrorEmpleados) =>
            this.aviso.open(e.mensaje, 'Cerrar', { duration: 5000 }),
        });
      });
  }
}
