import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  ProveedorService,
  type ErrorMisProductos,
} from '../../../core/services/proveedor.service';
import type { ListasDelFormulario } from '../../../core/models/proveedor.models';
import type { PaginaProductos, ProductoResumen } from '../../../core/models/productos.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import {
  MiProductoFormulario,
  type DatosProductoFormulario,
} from './producto-formulario';
import { MisVariantes, type DatosVariantes } from './variantes';

/**
 * CU-38 · Registrar productos del proveedor — «boundary» PantallaMisProductos.
 *
 * Realiza el RF37. Es la primera pantalla que le pertenece al Proveedor: hasta
 * el Ciclo 2 era un actor principal que no iniciaba ningún caso de uso.
 *
 * **Todo lo que se ve acá es suyo, y no porque la pantalla filtre.** El ámbito
 * lo resuelve el servidor con el token: no hay ningún parámetro `proveedor_id`
 * que mandar ni que se pueda cambiar. Si esta pantalla se equivocara, seguiría
 * sin poder ver lo de otro.
 *
 * **La columna «Estado» dice «Sin publicar», no «Inactivo».** Es la misma
 * columna del Administrador con otro nombre a propósito: para el Proveedor, que
 * su prenda no esté activa no es un estado técnico sino una espera —la tienda
 * todavía no la puso en el catálogo—, y llamarla «inactiva» haría pensar que se
 * rompió algo.
 *
 * Las listas de maestros se piden una vez al entrar y se le pasan a los dos
 * diálogos: volver a pedirlas en cada alta serían cinco consultas por producto.
 */
@Component({
  selector: 'app-mis-productos',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './mis-productos.html',
  styleUrl: './mis-productos.scss',
})
export class MisProductos implements OnInit {
  private readonly proveedor = inject(ProveedorService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(false);
  protected readonly error = signal<ErrorMisProductos | null>(null);
  protected readonly pagina = signal<PaginaProductos | null>(null);
  protected readonly listas = signal<ListasDelFormulario | null>(null);

  protected readonly columnas = [
    'codigo',
    'nombre',
    'categoria',
    'variantes',
    'estado',
    'acciones',
  ] as const;

  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly estado = new FormControl<'' | 'publicados' | 'pendientes'>('', {
    nonNullable: true,
  });

  private indice = 0;
  private tamano = 20;

  ngOnInit(): void {
    this.proveedor.listas().subscribe({
      next: (l) => this.listas.set(l),
      error: (e: ErrorMisProductos) => this.error.set(e),
    });

    this.busqueda.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe(() => {
        // Volver a la primera página: si estaba en la tercera y la búsqueda
        // deja dos, quedaría mirando una página vacía y pareciría que no hay
        // resultados.
        this.indice = 0;
        this.cargar();
      });

    this.estado.valueChanges.subscribe(() => {
      this.indice = 0;
      this.cargar();
    });

    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    const estado = this.estado.value;
    this.proveedor
      .listar({
        pagina: this.indice + 1,
        tamano: this.tamano,
        busqueda: this.busqueda.value.trim() || null,
        activo: estado === '' ? null : estado === 'publicados',
      })
      .subscribe({
        next: (p) => {
          this.cargando.set(false);
          this.pagina.set(p);
        },
        error: (e: ErrorMisProductos) => {
          this.cargando.set(false);
          this.error.set(e);
        },
      });
  }

  protected paginar(evento: PageEvent): void {
    this.indice = evento.pageIndex;
    this.tamano = evento.pageSize;
    this.cargar();
  }

  protected registrar(): void {
    const listas = this.listas();
    if (!listas) return;

    this.dialogo
      .open(MiProductoFormulario, {
        width: '42rem',
        maxWidth: '95vw',
        data: { listas } satisfies DatosProductoFormulario,
      })
      .afterClosed()
      .subscribe((producto) => {
        if (!producto) return;
        this.aviso.open(
          `«${producto.nombre}» quedó registrado, a la espera de que la tienda lo publique.`,
          'Entendido',
          { duration: 6000 },
        );
        this.cargar();
        // Se encadena el panel de variantes: un producto sin variantes no tiene
        // SKU, y sin SKU la tienda no puede pedirlo. Dejarlo para después es
        // dejarlo a medias sin que nada lo señale.
        this.abrirVariantes(producto.id);
      });
  }

  protected corregir(fila: ProductoResumen): void {
    const listas = this.listas();
    if (!listas) return;

    this.proveedor.obtener(fila.id).subscribe({
      next: (producto) => {
        this.dialogo
          .open(MiProductoFormulario, {
            width: '42rem',
            maxWidth: '95vw',
            data: { listas, producto } satisfies DatosProductoFormulario,
          })
          .afterClosed()
          .subscribe((guardado) => {
            if (guardado) this.cargar();
          });
      },
      error: (e: ErrorMisProductos) => this.avisarError(e),
    });
  }

  protected abrirVariantes(productoId: number): void {
    const listas = this.listas();
    if (!listas) return;

    this.proveedor.obtener(productoId).subscribe({
      next: (producto) => {
        this.dialogo
          .open(MisVariantes, {
            width: '40rem',
            maxWidth: '95vw',
            data: { producto, listas } satisfies DatosVariantes,
          })
          .afterClosed()
          .subscribe((cambio) => {
            if (cambio) this.cargar();
          });
      },
      error: (e: ErrorMisProductos) => this.avisarError(e),
    });
  }

  protected retirar(fila: ProductoResumen): void {
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'Retirar del abastecimiento',
          mensaje:
            `¿Retirar «${fila.nombre}»? Deja de ofrecerse y sus combinaciones ` +
            'quedan desactivadas. No se borra: el historial de la tienda lo conserva, ' +
            'y para volver a ofrecerlo hay que pedírselo a la tienda.',
          confirmar: 'Retirar',
          peligrosa: true,
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.proveedor.retirar(fila.id).subscribe({
          next: () => {
            this.aviso.open(`«${fila.nombre}» quedó retirado.`, 'Cerrar', {
              duration: 4000,
            });
            this.cargar();
          },
          error: (e: ErrorMisProductos) => this.avisarError(e),
        });
      });
  }

  private avisarError(e: ErrorMisProductos): void {
    this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 });
    // Un 404 acá casi siempre significa que la lista está vieja: alguien borró
    // o movió el producto. Recargar deja la pantalla diciendo la verdad.
    if (e.tipo === 'no-encontrado') this.cargar();
  }
}
