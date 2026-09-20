import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, type PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  BitacoraService,
  type AsientoBitacora,
  type ConsultaBitacora,
} from '../../../core/services/bitacora.service';

/**
 * CU-42 · Consultar la bitácora del sistema — «boundary» PantallaBitacora.
 *
 * Realiza el **RNF14**.
 *
 * SOLO SE LEE
 * ------------
 * No hay botón de crear, de editar ni de borrar, porque el servidor tampoco
 * los expone: los asientos los escribe un middleware y una bitácora que se
 * puede corregir no prueba nada.
 *
 * LOS FILTROS SE ARMAN CON LO QUE HAY
 * ------------------------------------
 * Las acciones y las entidades se piden a `/bitacora/opciones`, que las lee
 * de la tabla. Con una lista escrita acá, el desplegable ofrecería acciones
 * que no dan ningún resultado y escondería las que sí — y se
 * desactualizaría en silencio cada vez que alguien agregue una ruta.
 *
 * LA HORA NO SE CONVIERTE ACÁ
 * ----------------------------
 * Viene ya en hora boliviana desde el servidor. Reconvertirla la pasaría a
 * la zona del navegador, y una computadora con la hora mal puesta mostraría
 * una bitácora distinta a la de al lado.
 */
@Component({
  selector: 'app-bitacora',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDatepickerModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './bitacora.html',
  styleUrl: './bitacora.scss',
})
export class Bitacora implements OnInit {
  private readonly api = inject(BitacoraService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(false);
  protected readonly asientos = signal<AsientoBitacora[]>([]);
  protected readonly total = signal(0);
  protected readonly acciones = signal<string[]>([]);
  protected readonly entidades = signal<string[]>([]);
  protected readonly roles = signal<string[]>([]);

  protected readonly pagina = signal(0);
  protected readonly tamano = signal(25);

  protected readonly filtros = new FormGroup({
    desde: new FormControl<Date | null>(null),
    hasta: new FormControl<Date | null>(null),
    rol: new FormControl<string | null>(null),
    accion: new FormControl<string | null>(null),
    entidad: new FormControl<string | null>(null),
    exito: new FormControl<string | null>(null),
    busqueda: new FormControl<string>(''),
  });

  /** Cuántos filtros hay puestos, para avisarlo sin abrir el panel. */
  protected readonly cuantosFiltros = computed(() => this.contarFiltros());

  protected readonly vacio = computed(
    () => !this.cargando() && this.asientos().length === 0,
  );

  ngOnInit(): void {
    this.api.opciones().subscribe({
      next: (o) => {
        this.acciones.set(o.acciones);
        this.entidades.set(o.entidades);
        this.roles.set(o.roles ?? []);
      },
      // Sin opciones la pantalla sigue sirviendo: se pierden dos
      // desplegables, no la consulta. Avisar de esto con un cartel rojo
      // sería alarmar por algo que no impide trabajar.
      error: () => undefined,
    });
    this.buscar();
  }

  protected buscar(): void {
    this.cargando.set(true);
    const v = this.filtros.value;

    const consulta: ConsultaBitacora = {
      desde: this.aIso(v.desde ?? null),
      hasta: this.aIso(v.hasta ?? null),
      rol: v.rol || null,
      accion: v.accion || null,
      entidad: v.entidad || null,
      // El desplegable maneja tres estados y por eso es texto: `null` es
      // «todas», y un booleano no puede representar esa tercera opción.
      exito: v.exito === null || v.exito === '' ? null : v.exito === 'si',
      busqueda: v.busqueda?.trim() || null,
      pagina: this.pagina() + 1,
      tamano: this.tamano(),
    };

    this.api.consultar(consulta).subscribe({
      next: (p) => {
        this.asientos.set(p.items);
        this.total.set(p.total);
        this.cargando.set(false);
      },
      error: () => {
        this.cargando.set(false);
        this.aviso.open('No se pudo leer la bitácora.', 'Cerrar', {
          duration: 4000,
        });
      },
    });
  }

  protected aplicar(): void {
    // Vuelve a la primera página: quedarse en la cuarta después de filtrar
    // muestra una pantalla vacía sobre un resultado que sí tiene filas.
    this.pagina.set(0);
    this.buscar();
  }

  protected limpiar(): void {
    this.filtros.reset({ busqueda: '' });
    this.aplicar();
  }

  protected paginar(evento: PageEvent): void {
    this.pagina.set(evento.pageIndex);
    this.tamano.set(evento.pageSize);
    this.buscar();
  }

  /** Quién lo hizo: el nombre si la cuenta existe, el correo si no. */
  protected quien(a: AsientoBitacora): string {
    return a.nombre?.trim() || a.actor || 'Sin identificar';
  }

  /** `CREAR_RECHAZADO` se lee «Crear rechazado». */
  protected comoSeLee(accion: string): string {
    const palabras = accion.toLowerCase().split('_').join(' ');
    return palabras.charAt(0).toUpperCase() + palabras.slice(1);
  }

  protected hayDetalle(a: AsientoBitacora): boolean {
    return !!a.detalle && Object.keys(a.detalle).length > 0;
  }

  protected detalleLegible(a: AsientoBitacora): string {
    return JSON.stringify(a.detalle, null, 2);
  }

  private contarFiltros(): number {
    const v = this.filtros.value;
    return [
      v.desde,
      v.hasta,
      v.rol,
      v.accion,
      v.entidad,
      v.exito,
      v.busqueda?.trim(),
    ].filter(
      (x) => x !== null && x !== undefined && x !== '',
    ).length;
  }

  private aIso(fecha: Date | null): string | null {
    if (!fecha) return null;
    // Se arma a mano y no con `toISOString()`: ese convierte a UTC y, con
    // Bolivia en -4, una fecha elegida en el calendario se manda como el
    // día anterior. Es el mismo defecto que este caso de uso vino a
    // arreglar en el backend.
    const mes = `${fecha.getMonth() + 1}`.padStart(2, '0');
    const dia = `${fecha.getDate()}`.padStart(2, '0');
    return `${fecha.getFullYear()}-${mes}-${dia}`;
  }
}
