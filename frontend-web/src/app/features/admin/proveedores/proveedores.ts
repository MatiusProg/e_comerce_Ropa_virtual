import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
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
  ProveedoresService,
  type ErrorProveedores,
} from '../../../core/services/proveedores.service';
import type { Proveedor } from '../../../core/models/proveedores.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { ProveedorFormulario } from './proveedor-formulario';
import { AccesoFormulario } from './acceso-formulario';

/**
 * CU-07 · Gestionar proveedores — «boundary» PantallaProveedores.
 *
 * Realiza el paso 2 (listado con razón social, identificación, contacto y
 * estado) y ofrece los tres flujos alternativos: 3a editar, 3b dar de baja y
 * 3c habilitar acceso al Proveedor.
 *
 * Sin paginación, igual que en sucursales: la cartera de proveedores de una
 * tienda de ropa es del orden de las decenas.
 */
@Component({
  selector: 'app-proveedores',
  imports: [
    ReactiveFormsModule,
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
  templateUrl: './proveedores.html',
  styleUrl: './proveedores.scss',
})
export class Proveedores implements OnInit {
  private readonly api = inject(ProveedoresService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = [
    'proveedor',
    'identificacion',
    'contacto',
    'acceso',
    'estado',
    'acciones',
  ];

  protected readonly cargando = signal(false);
  /** Mensaje del ultimo fallo al listar, o null. Distingue «no se pudo
   *  consultar» de «no hay nada», que en pantalla se confundian. */
  protected readonly error = signal<string | null>(null);
  protected readonly proveedores = signal<Proveedor[]>([]);

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly filtroEstado = new FormControl<string>('', { nonNullable: true });

  ngOnInit(): void {
    // El debounce evita disparar una consulta por cada tecla.
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.cargar());
    this.filtroEstado.valueChanges.subscribe(() => this.cargar());
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    const estado = this.filtroEstado.value;
    this.api
      .listar({
        busqueda: this.busqueda.value || undefined,
        activo: estado === '' ? undefined : estado === 'activos',
      })
      .subscribe({
        next: (p) => {
          this.proveedores.set(p);
          this.cargando.set(false);
        },
        error: (e: ErrorProveedores) => {
          this.cargando.set(false);
          this.error.set(e.mensaje);
          this.mostrar(e.mensaje);
        },
      });
  }

  protected limpiarFiltros(): void {
    this.busqueda.setValue('', { emitEvent: false });
    this.filtroEstado.setValue('', { emitEvent: false });
    this.cargar();
  }

  protected get hayFiltros(): boolean {
    return !!(this.busqueda.value || this.filtroEstado.value);
  }

  // --- Acciones ----------------------------------------------------------

  /** Pasos 3 a 7 del flujo principal. */
  protected nuevo(): void {
    this.abrirFormulario(null);
  }

  /** Flujo alternativo 3a. */
  protected editar(proveedor: Proveedor): void {
    this.abrirFormulario(proveedor);
  }

  private abrirFormulario(proveedor: Proveedor | null): void {
    this.dialogo
      .open(ProveedorFormulario, { data: proveedor, width: '640px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar(
            proveedor ? 'Proveedor actualizado.' : 'Proveedor registrado correctamente.',
          );
          this.cargar();
        }
      });
  }

  /** Flujo alternativo 3b: el caso de uso pide confirmación explícita. */
  protected cambiarEstado(proveedor: Proveedor): void {
    const dandoDeBaja = proveedor.activo;
    const datos: DatosConfirmacion = {
      titulo: dandoDeBaja ? 'Dar de baja el proveedor' : 'Reactivar el proveedor',
      mensaje: dandoDeBaja
        ? `${proveedor.razon_social} dejará de ofrecerse para asociar productos nuevos. Sus productos históricos se conservan, y podrá reactivarlo cuando quiera.`
        : `${proveedor.razon_social} volverá a estar disponible para asociar productos.`,
      confirmar: dandoDeBaja ? 'Dar de baja' : 'Reactivar',
      peligrosa: dandoDeBaja,
    };

    this.confirmar(datos, () =>
      this.api.cambiarEstado(proveedor.id, !proveedor.activo).subscribe({
        next: () => {
          this.mostrar(dandoDeBaja ? 'Proveedor dado de baja.' : 'Proveedor reactivado.');
          this.cargar();
        },
        error: (e: ErrorProveedores) => this.mostrar(e.mensaje),
      }),
    );
  }

  /** Flujo alternativo 3c. */
  protected habilitarAcceso(proveedor: Proveedor): void {
    if (proveedor.tiene_acceso) {
      // Quitar el acceso no es de este caso de uso: desactivar esa cuenta es
      // CU-03. Se dice, en vez de ofrecer una acción que no hace nada.
      this.mostrar(
        `${proveedor.razon_social} ya entra al sistema con ${proveedor.correo_acceso}. Para quitarle el acceso, desactive esa cuenta desde Usuarios.`,
      );
      return;
    }

    this.dialogo
      .open(AccesoFormulario, { data: proveedor, width: '560px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((guardado) => {
        if (guardado) {
          this.mostrar('Acceso habilitado. El proveedor ya puede iniciar sesión.');
          this.cargar();
        }
      });
  }

  private confirmar(datos: DatosConfirmacion, accion: () => void): void {
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => si && accion());
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 6000 });
  }
}
