import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged, of, startWith, switchMap, catchError } from 'rxjs';

import { rechazoDelPlan } from '../../../core/models/plan.models';
import type { Sucursal } from '../../../core/models/organizacion.models';
import type {
  AccionTraspaso,
  Bandeja,
  EstadoTraspaso,
  OrigenPosible,
  PrendaPedible,
  Sugerencias,
  Traspaso,
  TraspasoSugerido,
} from '../../../core/models/traspasos.models';
import { AuthService } from '../../../core/services/auth.service';
import { OrganizacionService } from '../../../core/services/organizacion.service';
import { TraspasosService } from '../../../core/services/traspasos.service';

/**
 * 3ra presentación · CU-33 Solicitar traspaso, CU-34 Atender traspaso y
 * CU-35 Consultar traspasos sugeridos. «boundary» PantallaTraspasos.
 *
 * La misma pantalla cuelga de /sucursal/traspasos y de /admin/traspasos. El
 * alcance no lo decide la ruta sino el token: el Encargado ve y atiende lo de
 * su sucursal y pide PARA ella; el Administrador ve todo, ORDENA entre dos
 * sucursales cualesquiera (nace aprobado, RF-40) y es el único que ve los
 * sugeridos, si su plan los incluye (CU-05).
 *
 * Qué botones tiene cada traspaso no se calcula acá: llega en `acciones`,
 * resuelto por el servidor según el estado y quién consulta.
 */
@Component({
  selector: 'app-traspasos',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTabsModule,
  ],
  templateUrl: './traspasos.html',
  styleUrl: './traspasos.scss',
})
export class Traspasos implements OnInit {
  private readonly api = inject(TraspasosService);
  private readonly organizacion = inject(OrganizacionService);
  private readonly auth = inject(AuthService);
  private readonly aviso = inject(MatSnackBar);
  private readonly destruir = inject(DestroyRef);

  protected readonly esAdmin = computed(() => this.auth.usuario()?.rol === 'ADMINISTRADOR');
  protected readonly pestana = signal(0);

  protected readonly etiquetaEstado: Record<EstadoTraspaso, string> = {
    SOLICITADO: 'Solicitado',
    APROBADO: 'Aprobado',
    ENVIADO: 'En camino',
    RECIBIDO: 'Recibido',
    RECHAZADO: 'Rechazado',
  };

  // ---------------------------------------------------------------------
  //  CU-34 · Seguimiento y atención
  // ---------------------------------------------------------------------
  protected readonly cargando = signal(true);
  protected readonly filas = signal<Traspaso[]>([]);
  protected readonly total = signal(0);
  protected readonly pagina = signal(1);
  protected readonly tamano = 20;
  protected readonly bandeja = signal<Bandeja | 'TODAS'>('TODAS');
  protected readonly soloAbiertos = signal(true);
  protected readonly paginas = computed(() => Math.max(1, Math.ceil(this.total() / this.tamano)));

  /** El traspaso con el formulario de aprobar o rechazar abierto; uno a la vez. */
  protected readonly abierto = signal<{ id: number; accion: 'APROBAR' | 'RECHAZAR' } | null>(null);
  protected readonly atendiendo = signal<number | null>(null);
  protected readonly cantidadAprobada = new FormControl<number | null>(null, [Validators.min(1)]);
  protected readonly motivoRechazo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(3), Validators.maxLength(200)],
  });

  // ---------------------------------------------------------------------
  //  CU-33 · Pedir (Encargado) u ordenar (Administrador)
  // ---------------------------------------------------------------------
  protected readonly busqueda = new FormControl('', { nonNullable: true });
  protected readonly buscando = signal(false);
  protected readonly prendas = signal<PrendaPedible[]>([]);
  protected readonly prenda = signal<PrendaPedible | null>(null);
  protected readonly origenes = signal<OrigenPosible[]>([]);
  protected readonly origen = signal<OrigenPosible | null>(null);
  protected readonly sucursales = signal<Sucursal[]>([]);
  protected readonly destinoId = new FormControl<number | null>(null);
  protected readonly cantidad = new FormControl<number | null>(1, [
    Validators.required,
    Validators.min(1),
  ]);
  protected readonly motivo = new FormControl('', { nonNullable: true });
  protected readonly enviandoPedido = signal(false);
  /** Para el administrador: todas menos la de origen. */
  protected readonly destinos = computed(() =>
    this.sucursales().filter((s) => s.id !== this.origen()?.sucursal_id),
  );

  // ---------------------------------------------------------------------
  //  CU-35 · Sugeridos (solo Administrador)
  // ---------------------------------------------------------------------
  protected readonly dias = signal(30);
  protected readonly cargandoSugeridos = signal(false);
  protected readonly sugerencias = signal<Sugerencias | null>(null);
  /** Si el plan no incluye la función, el mensaje del CU-05 en vez de la lista. */
  protected readonly bloqueoDelPlan = signal<string | null>(null);
  protected readonly ordenando = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar();

    this.busqueda.valueChanges
      .pipe(
        startWith(''),
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((texto) => {
          this.buscando.set(true);
          return this.api.prendas(texto).pipe(
            catchError((e: HttpErrorResponse) => {
              this.mostrar(e, 'No se pudieron buscar las prendas.');
              return of([] as PrendaPedible[]);
            }),
          );
        }),
        takeUntilDestroyed(this.destruir),
      )
      .subscribe((prendas) => {
        this.buscando.set(false);
        this.prendas.set(prendas);
      });

    if (this.esAdmin()) {
      this.organizacion.listarSucursales({ activa: true }).subscribe({
        next: (s) => this.sucursales.set(s),
        error: () => this.sucursales.set([]),
      });
    }
  }

  protected cambiarPestana(indice: number): void {
    this.pestana.set(indice);
    // Los sugeridos se calculan sobre las ventas: se piden recién al abrirlos.
    if (indice === 2 && this.sugerencias() === null && this.bloqueoDelPlan() === null) {
      this.cargarSugeridos();
    }
  }

  // --- Seguimiento ------------------------------------------------------
  protected cargar(): void {
    this.cargando.set(true);
    const bandeja = this.bandeja();
    this.api
      .listar({
        bandeja: bandeja === 'TODAS' ? null : bandeja,
        abiertos: this.soloAbiertos(),
        pagina: this.pagina(),
        tamano: this.tamano,
      })
      .subscribe({
        next: (p) => {
          this.filas.set(p.items);
          this.total.set(p.total);
          this.cargando.set(false);
        },
        error: (e: HttpErrorResponse) => {
          this.cargando.set(false);
          this.mostrar(e, 'No se pudieron leer los traspasos.');
        },
      });
  }

  protected cambiarBandeja(valor: Bandeja | 'TODAS'): void {
    this.bandeja.set(valor);
    this.pagina.set(1);
    this.cargar();
  }

  protected cambiarAbiertos(valor: boolean): void {
    this.soloAbiertos.set(valor);
    this.pagina.set(1);
    this.cargar();
  }

  protected irAPagina(pagina: number): void {
    this.pagina.set(pagina);
    this.cargar();
  }

  protected accionar(t: Traspaso, accion: AccionTraspaso): void {
    if (accion === 'APROBAR') {
      this.cantidadAprobada.setValue(t.cantidad);
      this.abierto.set({ id: t.id, accion });
      return;
    }
    if (accion === 'RECHAZAR') {
      this.motivoRechazo.reset('');
      this.abierto.set({ id: t.id, accion });
      return;
    }
    this.ejecutar(t, accion, {});
  }

  protected confirmar(t: Traspaso): void {
    const abierto = this.abierto();
    if (!abierto) return;
    if (abierto.accion === 'APROBAR') {
      const cantidad = this.cantidadAprobada.value;
      if (!cantidad || cantidad < 1 || cantidad > t.cantidad) {
        this.aviso.open(`La cantidad va de 1 a ${t.cantidad}.`, 'Entendido', { duration: 5000 });
        return;
      }
      // Si no se bajó, no se manda: el servidor deja la pedida.
      this.ejecutar(t, 'APROBAR', cantidad === t.cantidad ? {} : { cantidad });
    } else {
      if (this.motivoRechazo.invalid) {
        this.motivoRechazo.markAsTouched();
        return;
      }
      this.ejecutar(t, 'RECHAZAR', { motivo: this.motivoRechazo.value.trim() });
    }
  }

  private ejecutar(t: Traspaso, accion: AccionTraspaso, cuerpo: object): void {
    this.atendiendo.set(t.id);
    this.api.atender(t.id, accion, cuerpo).subscribe({
      next: (nuevo) => {
        this.atendiendo.set(null);
        this.abierto.set(null);
        this.aviso.open(this.textoHecho(accion, nuevo), 'Entendido', { duration: 5000 });
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.atendiendo.set(null);
        this.mostrar(e, 'No se pudo atender el traspaso.');
        // Otro pudo haberlo movido mientras tanto: se relee.
        this.cargar();
      },
    });
  }

  private textoHecho(accion: AccionTraspaso, t: Traspaso): string {
    switch (accion) {
      case 'APROBAR':
        return `Traspaso #${t.id} aprobado por ${t.cantidad} u.`;
      case 'RECHAZAR':
        return `Traspaso #${t.id} rechazado.`;
      case 'ENVIAR':
        return `Enviadas ${t.cantidad} u. a ${t.destino.nombre}; ya se descontaron de ${t.origen.nombre}.`;
      case 'RECIBIR':
        return `Recibidas ${t.cantidad} u. en ${t.destino.nombre}.`;
      case 'DEVOLVER':
        return `Devueltas ${t.cantidad} u. a ${t.origen.nombre}.`;
    }
  }

  protected etiquetaAccion(accion: AccionTraspaso): string {
    return {
      APROBAR: 'Aprobar',
      RECHAZAR: 'Rechazar',
      ENVIAR: 'Enviar',
      RECIBIR: 'Recibir',
      DEVOLVER: 'Recibir de vuelta',
    }[accion];
  }

  protected iconoAccion(accion: AccionTraspaso): string {
    return {
      APROBAR: 'thumb_up',
      RECHAZAR: 'block',
      ENVIAR: 'local_shipping',
      RECIBIR: 'inventory',
      DEVOLVER: 'undo',
    }[accion];
  }

  // --- Pedir / ordenar --------------------------------------------------
  protected elegirPrenda(p: PrendaPedible): void {
    this.prenda.set(p);
    this.origen.set(null);
    this.origenes.set([]);
    this.api.origenes(p.variante_id).subscribe({
      next: (o) => {
        this.origenes.set(o);
        if (o.length === 1) this.elegirOrigen(o[0]);
      },
      error: (e: HttpErrorResponse) => this.mostrar(e, 'No se pudo saber quién la tiene.'),
    });
  }

  protected elegirOrigen(o: OrigenPosible): void {
    this.origen.set(o);
    this.cantidad.setValue(1);
    if (this.destinoId.value === o.sucursal_id) this.destinoId.setValue(null);
  }

  protected volverABuscar(): void {
    this.prenda.set(null);
    this.origen.set(null);
    this.origenes.set([]);
  }

  protected pedir(): void {
    const prenda = this.prenda();
    const origen = this.origen();
    const cantidad = this.cantidad.value;
    if (!prenda || !origen) return;
    if (!cantidad || cantidad < 1 || cantidad > origen.disponible) {
      this.aviso.open(`${origen.sucursal} tiene ${origen.disponible} disponibles.`, 'Entendido', {
        duration: 5000,
      });
      return;
    }
    if (this.esAdmin() && !this.destinoId.value) {
      this.aviso.open('Elija a qué sucursal va.', 'Entendido', { duration: 5000 });
      return;
    }
    this.enviandoPedido.set(true);
    this.api
      .solicitar({
        variante_id: prenda.variante_id,
        sucursal_origen_id: origen.sucursal_id,
        sucursal_destino_id: this.esAdmin() ? this.destinoId.value : null,
        cantidad,
        motivo: this.motivo.value.trim() || null,
      })
      .subscribe({
        next: (t) => {
          this.enviandoPedido.set(false);
          this.aviso.open(
            this.esAdmin()
              ? `Traspaso #${t.id} ordenado: ${t.origen.nombre} ya puede enviarlo.`
              : `Traspaso #${t.id} pedido a ${t.origen.nombre}. Le avisamos cuando lo atienda.`,
            'Entendido',
            { duration: 6000 },
          );
          this.volverABuscar();
          this.motivo.setValue('');
          this.destinoId.setValue(null);
          this.irAlSeguimiento();
        },
        error: (e: HttpErrorResponse) => {
          this.enviandoPedido.set(false);
          this.mostrar(e, 'No se pudo registrar el traspaso.');
        },
      });
  }

  private irAlSeguimiento(): void {
    this.pestana.set(0);
    this.bandeja.set('TODAS');
    this.soloAbiertos.set(true);
    this.pagina.set(1);
    this.cargar();
  }

  // --- Sugeridos --------------------------------------------------------
  protected cambiarDias(dias: number): void {
    this.dias.set(dias);
    this.cargarSugeridos();
  }

  protected cargarSugeridos(): void {
    this.cargandoSugeridos.set(true);
    this.api.sugeridos(this.dias()).subscribe({
      next: (s) => {
        this.sugerencias.set(s);
        this.bloqueoDelPlan.set(null);
        this.cargandoSugeridos.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.cargandoSugeridos.set(false);
        const plan = rechazoDelPlan(e);
        if (plan) {
          this.bloqueoDelPlan.set(plan.detail);
          return;
        }
        this.mostrar(e, 'No se pudieron calcular los sugeridos.');
      },
    });
  }

  protected claveSugerido(s: TraspasoSugerido): string {
    return `${s.variante_id}-${s.origen.sucursal_id}-${s.destino.sucursal_id}`;
  }

  protected ordenarSugerido(s: TraspasoSugerido): void {
    const clave = this.claveSugerido(s);
    this.ordenando.set(clave);
    this.api
      .solicitar({
        variante_id: s.variante_id,
        sucursal_origen_id: s.origen.sucursal_id,
        sucursal_destino_id: s.destino.sucursal_id,
        cantidad: s.cantidad_sugerida,
        motivo: s.razon,
        desde_sugerencia: true,
      })
      .subscribe({
        next: (t) => {
          this.ordenando.set(null);
          this.aviso.open(
            `Traspaso #${t.id} ordenado de ${t.origen.nombre} a ${t.destino.nombre}.`,
            'Entendido',
            { duration: 5000 },
          );
          // Ya no es sugerencia: queda como traspaso abierto.
          this.cargarSugeridos();
          this.cargar();
        },
        error: (e: HttpErrorResponse) => {
          this.ordenando.set(null);
          this.mostrar(e, 'No se pudo ordenar el traspaso.');
          this.cargarSugeridos();
        },
      });
  }

  private mostrar(e: HttpErrorResponse, porOmision: string): void {
    const texto = typeof e.error?.detail === 'string' ? e.error.detail : porOmision;
    this.aviso.open(texto, 'Entendido', { duration: 7000 });
  }
}
