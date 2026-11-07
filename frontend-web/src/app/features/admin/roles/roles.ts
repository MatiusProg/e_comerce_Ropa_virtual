import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin } from 'rxjs';

import { rechazoDelPlan } from '../../../core/models/plan.models';
import type {
  PermisoDelCatalogo,
  Persona,
  RolBase,
  RolEmpresa,
} from '../../../core/models/roles.models';
import { RolesService } from '../../../core/services/roles.service';

/**
 * 3ra presentación · CU-41 Gestionar roles y permisos de la empresa.
 * «boundary» PantallaRoles.
 *
 * Un rol propio parte de un rol base (administrador, encargado o cajero) y
 * conserva solo los permisos que se le marquen: nunca da más que su rol base.
 * Los permisos que son funciones del plan que la empresa no tiene aparecen
 * deshabilitados (RN-22). Quien no tiene rol propio sigue con todo lo de su
 * rol, como siempre.
 */
@Component({
  selector: 'app-roles',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './roles.html',
  styleUrl: './roles.scss',
})
export class Roles implements OnInit {
  private readonly api = inject(RolesService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly cargando = signal(true);
  protected readonly catalogo = signal<PermisoDelCatalogo[]>([]);
  protected readonly roles = signal<RolEmpresa[]>([]);
  protected readonly personal = signal<Persona[]>([]);

  protected readonly etiquetaBase: Record<RolBase, string> = {
    ADMINISTRADOR: 'Administrador',
    ENCARGADO: 'Encargado',
    CAJERO: 'Cajero',
  };
  protected readonly bases: RolBase[] = ['CAJERO', 'ENCARGADO', 'ADMINISTRADOR'];

  // --- Formulario -------------------------------------------------------
  /** El rol que se edita; nulo cuando el formulario es de alta. */
  protected readonly editando = signal<RolEmpresa | null>(null);
  protected readonly abierto = signal(false);
  protected readonly guardando = signal(false);
  protected readonly formulario = new FormGroup({
    nombre: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.minLength(3), Validators.maxLength(40)],
    }),
    descripcion: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(150)] }),
  });
  protected readonly base = signal<RolBase>('CAJERO');
  protected readonly marcados = signal<Set<string>>(new Set());

  /** Los permisos del rol base elegido, agrupados por área. */
  protected readonly areas = computed(() => {
    const grupos = new Map<string, PermisoDelCatalogo[]>();
    for (const p of this.catalogo()) {
      if (!p.roles_base.includes(this.base())) continue;
      grupos.set(p.area, [...(grupos.get(p.area) ?? []), p]);
    }
    return [...grupos.entries()].map(([area, permisos]) => ({ area, permisos }));
  });

  protected readonly nombreDe = computed(() => {
    const nombres = new Map(this.catalogo().map((p) => [p.codigo, p.nombre]));
    return (codigo: string) => nombres.get(codigo) ?? codigo;
  });

  ngOnInit(): void {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    forkJoin({
      catalogo: this.api.permisos(),
      roles: this.api.listar(),
      personal: this.api.personal(),
    }).subscribe({
      next: ({ catalogo, roles, personal }) => {
        this.catalogo.set(catalogo);
        this.roles.set(roles);
        this.personal.set(personal);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.cargando.set(false);
        this.mostrar(e, 'No se pudieron leer los roles.');
      },
    });
  }

  protected nuevo(): void {
    this.editando.set(null);
    this.formulario.reset({ nombre: '', descripcion: '' });
    this.base.set('CAJERO');
    this.marcados.set(new Set());
    this.abierto.set(true);
  }

  protected editar(rol: RolEmpresa): void {
    this.editando.set(rol);
    this.formulario.setValue({ nombre: rol.nombre, descripcion: rol.descripcion ?? '' });
    this.base.set(rol.rol_base);
    this.marcados.set(new Set(rol.permisos));
    this.abierto.set(true);
  }

  protected cambiarBase(base: RolBase): void {
    this.base.set(base);
    // Lo marcado que no es de la nueva base se descarta.
    const validos = new Set(
      this.catalogo().filter((p) => p.roles_base.includes(base)).map((p) => p.codigo),
    );
    this.marcados.set(new Set([...this.marcados()].filter((c) => validos.has(c))));
  }

  protected alternar(codigo: string, marcado: boolean): void {
    const nuevos = new Set(this.marcados());
    if (marcado) nuevos.add(codigo);
    else nuevos.delete(codigo);
    this.marcados.set(nuevos);
  }

  protected guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const v = this.formulario.getRawValue();
    const datos = {
      nombre: v.nombre.trim(),
      descripcion: v.descripcion.trim() || null,
      permisos: [...this.marcados()],
    };
    const editando = this.editando();
    this.guardando.set(true);
    const peticion = editando
      ? this.api.editar(editando.id, datos)
      : this.api.crear({ ...datos, rol_base: this.base() });
    peticion.subscribe({
      next: (rol) => {
        this.guardando.set(false);
        this.abierto.set(false);
        this.aviso.open(`Rol «${rol.nombre}» guardado.`, 'Entendido', { duration: 4000 });
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.guardando.set(false);
        const plan = rechazoDelPlan(e);
        this.mostrar(e, plan ? plan.detail : 'No se pudo guardar el rol.');
      },
    });
  }

  /**
   * Si el servidor lo rechaza, el interruptor vuelve a como estaba. Recargar
   * no alcanza: el dato no cambió, así que Angular no vuelve a escribir
   * `[checked]` y el control quedaba mostrando lo que el usuario tocó.
   */
  protected cambiarEstado(rol: RolEmpresa, activo: boolean, control?: { checked: boolean }): void {
    this.api.estado(rol.id, activo).subscribe({
      next: () => this.cargar(),
      error: (e: HttpErrorResponse) => {
        this.mostrar(e, 'No se pudo cambiar el estado.');
        if (control) control.checked = !activo;
        this.cargar();
      },
    });
  }

  // --- Asignación -------------------------------------------------------
  protected rolesPara(persona: Persona): RolEmpresa[] {
    return this.roles().filter(
      (r) => r.rol_base === persona.rol_base && (r.activo || r.id === persona.rol_empresa_id),
    );
  }

  /** Igual que el interruptor: si falla, el desplegable vuelve al rol que tenía. */
  protected asignar(persona: Persona, rolId: number | null, control?: { value: unknown }): void {
    const anterior = persona.rol_empresa_id;
    this.api.asignar(persona.usuario_id, rolId).subscribe({
      next: (p) => {
        this.aviso.open(
          p.rol_empresa
            ? `${p.nombre} ahora es «${p.rol_empresa}».`
            : `${p.nombre} vuelve a tener todo lo de su rol.`,
          'Entendido',
          { duration: 5000 },
        );
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.mostrar(e, 'No se pudo asignar el rol.');
        if (control) control.value = anterior;
        this.cargar();
      },
    });
  }

  private mostrar(e: HttpErrorResponse, porOmision: string): void {
    const texto = typeof e.error?.detail === 'string' ? e.error.detail : porOmision;
    this.aviso.open(texto, 'Entendido', { duration: 7000 });
  }
}
