import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import {
  MAT_DIALOG_DATA,
  MatDialog,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  PlataformaService,
  type ErrorPlataforma,
} from '../../../core/services/plataforma.service';
import type { Empresa, EmpresaCreada, PlanOferta } from '../../../core/models/plataforma.models';
import type { Ciudad } from '../../../core/models/organizacion.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';
import { EmpresaFormulario, type DatosEmpresa } from './empresa-formulario';

/**
 * El acceso del administrador nuevo, mostrado UNA vez. El correo ya salió;
 * esto es para cuando no llega (paso 6 del CU-01).
 */
@Component({
  selector: 'app-empresa-creada',
  imports: [MatButtonModule, MatDialogModule, MatIconModule],
  template: `
    <h2 mat-dialog-title class="vb-titulo">Empresa registrada</h2>
    <mat-dialog-content>
      <p>
        <strong>{{ datos.nombre }}</strong> quedó registrada con el plan
        {{ datos.suscripcion?.plan_nombre }}.
        {{
          datos.correo_enviado
            ? 'Se envió el acceso por correo al administrador.'
            : 'No se pudo enviar el correo: entréguele estos datos.'
        }}
      </p>
      <ul class="acceso">
        <li>Empresa (slug): <strong>{{ datos.slug }}</strong></li>
        <li>Correo: <strong>{{ datos.administrador_correo }}</strong></li>
        <li>Contraseña temporal: <strong>{{ datos.contrasena_temporal }}</strong></li>
      </ul>
      <p class="pista">Esta contraseña no se vuelve a mostrar.</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button matButton="filled" class="vb-boton-marca" type="button" (click)="ref.close()">
        Entendido
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    .acceso { line-height: 1.8; }
    .pista { color: var(--vb-texto-suave, #666); font-size: 0.85rem; }
  `,
})
export class EmpresaCreadaDialogo {
  protected readonly ref = inject(MatDialogRef<EmpresaCreadaDialogo>);
  protected readonly datos = inject<EmpresaCreada>(MAT_DIALOG_DATA);
}

/**
 * CU-01 · Gestionar empresas — «boundary» PantallaEmpresas (2do parcial).
 *
 * Paso 2: la lista de empresas con su slug, su plan y su estado. Desde acá se
 * registra una empresa (flujo principal), se edita (3a) y se da de baja o se
 * reactiva (3b). Solo la ve el administrador de la plataforma. Cada empresa
 * abre su ficha con la suscripción (CU-03).
 */
@Component({
  selector: 'app-empresas',
  imports: [
    DatePipe,
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
    MatTableModule,
  ],
  templateUrl: './empresas.html',
  styleUrl: './empresas.scss',
})
export class Empresas implements OnInit {
  private readonly api = inject(PlataformaService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly columnas = ['empresa', 'plan', 'uso', 'estado', 'acciones'];

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly empresas = signal<Empresa[]>([]);
  private planes: PlanOferta[] = [];
  private ciudades: Ciudad[] = [];

  protected readonly busqueda = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    this.api.planes().subscribe({ next: (p) => (this.planes = p) });
    this.api.ciudades().subscribe({ next: (c) => (this.ciudades = c) });
    this.busqueda.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.cargar());
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.listarEmpresas(this.busqueda.value || undefined).subscribe({
      next: (e) => {
        this.empresas.set(e);
        this.cargando.set(false);
      },
      error: (e: ErrorPlataforma) => {
        this.cargando.set(false);
        this.error.set(e.mensaje);
      },
    });
  }

  /** Flujo principal, pasos 3 a 6. */
  protected nueva(): void {
    if (!this.planes.length || !this.ciudades.length) {
      this.mostrar('Todavía se están cargando los planes y las ciudades. Intente de nuevo.');
      return;
    }
    this.abrir({ planes: this.planes, ciudades: this.ciudades, empresa: null });
  }

  /** Alternativo 3a. */
  protected editar(empresa: Empresa): void {
    this.abrir({ planes: this.planes, ciudades: this.ciudades, empresa });
  }

  private abrir(datos: DatosEmpresa): void {
    this.dialogo
      .open(EmpresaFormulario, { data: datos, width: '680px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((resultado: Empresa | EmpresaCreada | null) => {
        if (!resultado) return;
        if ('contrasena_temporal' in resultado) {
          this.dialogo.open(EmpresaCreadaDialogo, {
            data: resultado,
            width: '520px',
            maxWidth: '95vw',
            disableClose: true,
          });
        } else {
          this.mostrar('Empresa actualizada.');
        }
        this.cargar();
      });
  }

  /** Alternativo 3b: la baja no borra nada, pero corta el acceso de todos sus usuarios. */
  protected cambiarEstado(empresa: Empresa): void {
    const dandoDeBaja = empresa.estado === 'ACTIVA';
    const datos: DatosConfirmacion = {
      titulo: dandoDeBaja ? 'Dar de baja la empresa' : 'Reactivar la empresa',
      mensaje: dandoDeBaja
        ? `Ningún usuario de ${empresa.nombre} podrá iniciar sesión, y se cierran las sesiones abiertas. No se borra ningún dato: puede reactivarla cuando quiera.`
        : `Los usuarios de ${empresa.nombre} vuelven a poder iniciar sesión.`,
      confirmar: dandoDeBaja ? 'Dar de baja' : 'Reactivar',
      peligrosa: dandoDeBaja,
    };
    this.dialogo
      .open(Confirmacion, { data: datos, width: '460px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((si) => {
        if (!si) return;
        this.api.cambiarEstado(empresa.id, !dandoDeBaja).subscribe({
          next: () => {
            this.mostrar(dandoDeBaja ? 'Empresa dada de baja.' : 'Empresa reactivada.');
            this.cargar();
          },
          error: (e: ErrorPlataforma) => this.mostrar(e.mensaje),
        });
      });
  }

  /** CU-03 E1: marca como vencidas las suscripciones cuya fecha pasó. */
  protected marcarVencidas(): void {
    this.api.marcarVencidas().subscribe({
      next: (r) => {
        this.mostrar(
          r.vencidas
            ? `Se marcaron ${r.vencidas} vencidas: ${r.empresas.join(', ')}.`
            : 'No hay suscripciones nuevas por vencer.',
        );
        if (r.vencidas) this.cargar();
      },
      error: (e: ErrorPlataforma) => this.mostrar(e.mensaje),
    });
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 5000 });
  }
}
