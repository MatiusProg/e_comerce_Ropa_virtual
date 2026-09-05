import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
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

import {
  OrganizacionService,
  type ErrorOrganizacion,
} from '../../../core/services/organizacion.service';
import type { Ciudad, Sucursal } from '../../../core/models/organizacion.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { SucursalFormulario, type DatosSucursal } from './sucursal-formulario';

/**
 * CU-05 · Gestionar ciudades y sucursales — «boundary» PantallaSucursales.
 *
 * Realiza el paso 2 (listado con dirección, horario, capacidad y estado) y
 * ofrece las acciones de los flujos alternativos 3b (editar) y 3c (dar de
 * baja). El flujo 3a, gestionar ciudades, tiene su propia pantalla.
 *
 * No hay paginación, a diferencia de CU-03: la cantidad de sucursales de una
 * cadena es del orden de las decenas y no crece sola. Un paginador sobre diez
 * filas es ruido; los filtros alcanzan.
 */
@Component({
  selector: 'app-sucursales',
  imports: [
    ReactiveFormsModule,
    RouterLink,
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
  templateUrl: './sucursales.html',
  styleUrl: './sucursales.scss',
})
export class Sucursales implements OnInit {
  private readonly api = inject(OrganizacionService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = [
    'sucursal',
    'ciudad',
    'horario',
    'vestidores',
    'estado',
    'acciones',
  ];

  protected readonly cargando = signal(false);
  /** Mensaje del ultimo fallo al listar, o null. Distingue «no se pudo
   *  consultar» de «no hay nada», que en pantalla se confundian. */
  protected readonly error = signal<string | null>(null);
  protected readonly sucursales = signal<Sucursal[]>([]);
  protected readonly ciudades = signal<Ciudad[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroCiudad = new FormControl<number | ''>('', { nonNullable: true });
  protected readonly filtroEstado = new FormControl<string>('', { nonNullable: true });

  ngOnInit(): void {
    this.cargarCiudades();

    // El debounce evita disparar una consulta por cada tecla.
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.cargar());

    this.filtroCiudad.valueChanges.subscribe(() => this.cargar());
    this.filtroEstado.valueChanges.subscribe(() => this.cargar());

    this.cargar();
  }

  /** Las ciudades pueblan el filtro y el selector del formulario. */
  private cargarCiudades(): void {
    this.api.listarCiudades().subscribe({
      next: (c) => this.ciudades.set(c),
      error: () => this.ciudades.set([]),
    });
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    const estado = this.filtroEstado.value;
    const ciudad = this.filtroCiudad.value;
    this.api
      .listarSucursales({
        busqueda: this.busqueda.value || undefined,
        ciudad_id: ciudad === '' ? undefined : ciudad,
        activa: estado === '' ? undefined : estado === 'activas',
      })
      .subscribe({
        next: (s) => {
          this.sucursales.set(s);
          this.cargando.set(false);
        },
        error: (e: ErrorOrganizacion) => {
          this.cargando.set(false);
          this.error.set(e.mensaje);
          this.mostrar(e.mensaje);
        },
      });
  }

  protected limpiarFiltros(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroCiudad.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.cargar();
  }

  protected get hayFiltros(): boolean {
    return !!(this.busqueda.value || this.filtroCiudad.value !== '' || this.filtroEstado.value);
  }

  /** `HH:MM:SS` del servidor a `HH:MM`, que es lo que se muestra. */
  protected hora(valor: string): string {
    return valor?.slice(0, 5) ?? '';
  }

  // --- Acciones ----------------------------------------------------------

  /** Pasos 3 a 7 del flujo principal. */
  protected nueva(): void {
    this.abrirFormulario({ ciudades: this.ciudades(), sucursal: null });
  }

  /** Flujo alternativo 3b. */
  protected editar(sucursal: Sucursal): void {
    this.abrirFormulario({ ciudades: this.ciudades(), sucursal });
  }

  private abrirFormulario(datos: DatosSucursal): void {
    if (!datos.ciudades.length) {
      // Sin ciudades no hay dónde poner la sucursal: se dice por qué en vez de
      // abrir un formulario con el selector vacío.
      this.mostrar('Registre primero una ciudad para poder crear sucursales.');
      return;
    }

    this.dialogo
      .open(SucursalFormulario, { data: datos, width: '640px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar(
            datos.sucursal ? 'Sucursal actualizada.' : 'Sucursal registrada correctamente.',
          );
          this.cargar();
          // El recuento de sucursales por ciudad cambió.
          this.cargarCiudades();
        }
      });
  }

  /** Flujo alternativo 3c: el caso de uso pide confirmación explícita. */
  protected cambiarEstado(sucursal: Sucursal): void {
    const dandoDeBaja = sucursal.activa;
    const datos: DatosConfirmacion = {
      titulo: dandoDeBaja ? 'Dar de baja la sucursal' : 'Reactivar la sucursal',
      mensaje: dandoDeBaja
        ? `${sucursal.nombre} dejará de ofrecerse para reservas y compras. Sus datos se conservan para la trazabilidad histórica, y podrá reactivarla cuando quiera.`
        : `${sucursal.nombre} volverá a ofrecerse para reservas y compras.`,
      confirmar: dandoDeBaja ? 'Dar de baja' : 'Reactivar',
      peligrosa: dandoDeBaja,
    };

    this.confirmar(datos, () =>
      this.api.cambiarEstadoSucursal(sucursal.id, !sucursal.activa).subscribe({
        next: () => {
          this.mostrar(dandoDeBaja ? 'Sucursal dada de baja.' : 'Sucursal reactivada.');
          this.cargar();
          this.cargarCiudades();
        },
        error: (e: ErrorOrganizacion) => this.mostrar(e.mensaje),
      }),
    );
  }

  private confirmar(datos: DatosConfirmacion, accion: () => void): void {
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => si && accion());
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 5000 });
  }
}
