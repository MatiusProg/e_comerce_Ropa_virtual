import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';

import { COLORES_VIOLET, type MarcaEmpresa } from '../../../core/models/mi-tienda.models';
import { MarcaService, mezclar } from '../../../core/services/marca.service';
import { MiTiendaService, type ErrorMiTienda } from '../../../core/services/mi-tienda.service';
import { UrlMediaPipe } from '../../../shared/url-media.pipe';

const HEX = /^#[0-9a-f]{6}$/;

/**
 * CU-12 · Personalizar la tienda de la empresa — «boundary» PantallaMiTienda.
 *
 * El administrador sube el logo y elige el color principal y el secundario,
 * con una vista previa que cambia mientras elige (1.6). Al guardar, la tienda
 * en línea los aplica (1.11, `MarcaService`).
 *
 * 1a: sin `marca_propia` en el plan la pantalla se ve, pero no guarda, y dice
 * por qué con el enlace a «Mi plan». El backend es el que lo impide (CU-05).
 * 4a: el logo que no es una imagen lo rechaza el backend y se muestra su
 * mensaje.
 */
@Component({
  selector: 'app-mi-tienda',
  imports: [RouterLink, MatButtonModule, MatIconModule, MatProgressBarModule, UrlMediaPipe],
  templateUrl: './mi-tienda.html',
  styleUrl: './mi-tienda.scss',
})
export class MiTienda implements OnInit {
  private readonly servicio = inject(MiTiendaService);
  private readonly marcaDeLaTienda = inject(MarcaService);
  private readonly aviso = inject(MatSnackBar);

  protected readonly violet = COLORES_VIOLET;

  protected readonly marca = signal<MarcaEmpresa | null>(null);
  protected readonly cargando = signal(true);
  protected readonly guardando = signal(false);
  protected readonly error = signal<ErrorMiTienda | null>(null);
  /** El error del logo va aparte: no tiene que tapar la pantalla (4a). */
  protected readonly errorLogo = signal<string | null>(null);

  /** Lo que se está eligiendo; la vista previa lo muestra antes de guardar. */
  protected readonly principal = signal(COLORES_VIOLET.principal);
  protected readonly secundario = signal(COLORES_VIOLET.secundario);

  protected readonly incluida = computed(() => this.marca()?.incluida ?? false);

  /** Si lo elegido difiere de lo guardado: habilita «Guardar». */
  protected readonly hayCambios = computed(() => {
    const m = this.marca();
    if (!m) return false;
    return (
      this.principal() !== (m.color_principal ?? COLORES_VIOLET.principal) ||
      this.secundario() !== (m.color_secundario ?? COLORES_VIOLET.secundario)
    );
  });

  /** Los tonos de la vista previa, sacados igual que en la tienda. */
  protected readonly oscuro = computed(() => mezclar(this.principal(), '#000000', 0.25));
  protected readonly palido = computed(() => mezclar(this.principal(), '#ffffff', 0.85));

  ngOnInit(): void {
    this.servicio.obtener().subscribe({
      next: (m) => {
        this.mostrar(m);
        this.cargando.set(false);
      },
      error: (e: ErrorMiTienda) => {
        this.error.set(e);
        this.cargando.set(false);
      },
    });
  }

  protected elegirPrincipal(evento: Event): void {
    this.principal.set(this.color(evento, this.principal()));
  }

  protected elegirSecundario(evento: Event): void {
    this.secundario.set(this.color(evento, this.secundario()));
  }

  /** 1.7 y 1.8: los colores. Los de Violet se guardan como `null`. */
  protected guardarColores(): void {
    const p = this.principal();
    const s = this.secundario();
    this.guardar(
      this.servicio.guardarColores({
        color_principal: p === COLORES_VIOLET.principal ? null : p,
        color_secundario: s === COLORES_VIOLET.secundario ? null : s,
      }),
      'Colores guardados. La tienda ya los muestra.',
    );
  }

  protected restablecerColores(): void {
    this.principal.set(COLORES_VIOLET.principal);
    this.secundario.set(COLORES_VIOLET.secundario);
    this.guardar(
      this.servicio.guardarColores({ color_principal: null, color_secundario: null }),
      'La tienda volvió a los colores de Violet.',
    );
  }

  /** 1.7: el logo se sube apenas se elige. */
  protected elegirLogo(evento: Event): void {
    const entrada = evento.target as HTMLInputElement;
    const archivo = entrada.files?.[0];
    entrada.value = ''; // para poder volver a elegir el mismo archivo
    if (!archivo) return;
    this.errorLogo.set(null);
    this.guardar(this.servicio.subirLogo(archivo), 'Logo actualizado.');
  }

  protected quitarLogo(): void {
    this.guardar(this.servicio.quitarLogo(), 'La tienda volvió al logo de Violet.');
  }

  private guardar(peticion: ReturnType<MiTiendaService['obtener']>, mensaje: string): void {
    this.guardando.set(true);
    peticion.subscribe({
      next: (m) => {
        this.guardando.set(false);
        this.mostrar(m);
        // 1.11: la tienda en línea toma la marca nueva sin recargar.
        this.marcaDeLaTienda.cargar();
        this.aviso.open(mensaje, 'Cerrar', { duration: 3500 });
      },
      error: (e: ErrorMiTienda) => {
        this.guardando.set(false);
        if (e.tipo === 'imagen') {
          this.errorLogo.set(e.mensaje);
        } else {
          this.aviso.open(e.mensaje, 'Cerrar', { duration: 6000 });
        }
      },
    });
  }

  private mostrar(m: MarcaEmpresa): void {
    this.marca.set(m);
    this.principal.set(m.color_principal ?? COLORES_VIOLET.principal);
    this.secundario.set(m.color_secundario ?? COLORES_VIOLET.secundario);
  }

  /** El valor del selector, o el anterior si no es un `#rrggbb`. */
  private color(evento: Event, anterior: string): string {
    const valor = (evento.target as HTMLInputElement).value.trim().toLowerCase();
    return HEX.test(valor) ? valor : anterior;
  }
}
