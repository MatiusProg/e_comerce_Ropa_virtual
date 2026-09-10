import { Component, inject, signal } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  ProductosService,
  type ErrorProductos,
} from '../../../core/services/productos.service';
import type { Imagen, Producto, Variante } from '../../../core/models/productos.models';
import { Confirmacion, type DatosConfirmacion } from '../../../shared/confirmacion/confirmacion';

export interface DatosGaleria {
  producto: Producto;
}

/**
 * CU-11 · Gestionar imágenes de producto — «boundary» PantallaGalería.
 *
 * Dos ideas gobiernan esta pantalla:
 *
 * **La principal y el PNG del vestidor no son la misma cosa y no se confunden.**
 * La principal es la foto que representa al producto en el listado del catálogo
 * —una por producto—. El PNG transparente es el activo que el vestidor virtual
 * superpone sobre el torso, pertenece a una **variante** concreta y solo puede
 * haber uno por variante. Se marcan por separado y se muestran con distintivos
 * distintos, porque marcar una donde iba la otra rompe cosas diferentes.
 *
 * **El servidor decide si una imagen sirve para el vestidor, no el nombre del
 * archivo.** Un PNG guardado sobre fondo blanco es un PNG válido; el servidor
 * lo abre y mira el canal alfa. Si lo rechaza, el mensaje explica por qué y no
 * se maquilla como un error genérico: es el defecto que, sin este control,
 * aparecería recién en el prototipo de realidad aumentada.
 */
@Component({
  selector: 'app-galeria',
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatMenuModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './galeria.html',
  styleUrl: './galeria.scss',
})
export class Galeria {
  private readonly api = inject(ProductosService);
  private readonly dialogo = inject(MatDialog);
  private readonly aviso = inject(MatSnackBar);

  protected readonly ref = inject(MatDialogRef<Galeria, boolean>);
  protected readonly datos = inject<DatosGaleria>(MAT_DIALOG_DATA);

  protected readonly producto = this.datos.producto;
  protected readonly variantes: Variante[] = this.datos.producto.variantes;
  protected readonly imagenes = signal<Imagen[]>([]);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  private readonly hubocambios = signal(false);

  constructor() {
    this.cargar();
  }

  protected url(imagen: Imagen): string {
    return this.api.urlDeImagen(imagen);
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.listarImagenes(this.producto.id).subscribe({
      next: (imagenes) => {
        this.imagenes.set(imagenes);
        this.cargando.set(false);
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.error.set(e.mensaje);
      },
    });
  }

  // --- Pasos 3 y 4: subir ------------------------------------------------

  protected elegirArchivos(evento: Event): void {
    const entrada = evento.target as HTMLInputElement;
    const archivos = Array.from(entrada.files ?? []);
    // Se limpia el input antes de subir: sin esto, elegir el mismo archivo dos
    // veces seguidas no dispara el evento y parece que la pantalla se colgó.
    entrada.value = '';
    if (!archivos.length) return;
    this.subir(archivos, 0);
  }

  /**
   * Sube los archivos de a uno y en orden.
   *
   * En paralelo sería más rápido, pero la primera imagen de un producto queda
   * como principal: con varias peticiones a la vez, cuál gana esa carrera
   * depende de la red. En serie, la principal es siempre la primera que el
   * Administrador eligió, que es lo que espera.
   */
  private subir(archivos: File[], indice: number): void {
    if (indice >= archivos.length) {
      this.cargando.set(false);
      this.mostrar(
        archivos.length === 1 ? 'Imagen subida.' : `${archivos.length} imágenes subidas.`,
      );
      this.cargar();
      return;
    }
    this.cargando.set(true);
    this.error.set(null);
    this.api.subirImagen(this.producto.id, archivos[indice]).subscribe({
      next: () => {
        this.hubocambios.set(true);
        this.subir(archivos, indice + 1);
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.error.set(`${archivos[indice].name}: ${e.mensaje}`);
        // Se sigue con los demás: que una foto de 8 MB corte la carga de las
        // otras cuatro obligaría a repetir todo.
        if (indice + 1 < archivos.length) this.subir(archivos, indice + 1);
        else this.cargar();
      },
    });
  }

  // --- 3a Asociar a una variante -----------------------------------------

  protected asociar(imagen: Imagen, varianteId: number | null): void {
    this.cargando.set(true);
    this.api.editarImagen(imagen.id, { variante_id: varianteId }).subscribe({
      next: () => {
        this.hubocambios.set(true);
        this.mostrar(varianteId === null ? 'Imagen del producto.' : 'Imagen asociada.');
        this.cargar();
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  protected etiquetaDeVariante(variante: Variante): string {
    return [variante.talla_codigo, variante.color_nombre].filter(Boolean).join(' · ');
  }

  // --- 3b La principal ---------------------------------------------------

  protected marcarPrincipal(imagen: Imagen): void {
    if (imagen.es_principal) return;
    this.cargando.set(true);
    this.api.marcarPrincipal(imagen.id, true).subscribe({
      next: (galeria) => {
        this.hubocambios.set(true);
        this.imagenes.set(galeria);
        this.cargando.set(false);
        this.mostrar('Imagen principal actualizada.');
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  // --- 3c El PNG del vestidor virtual ------------------------------------

  protected alternarVestidor(imagen: Imagen): void {
    const marcando = !imagen.es_transparente;
    this.cargando.set(true);
    this.error.set(null);
    this.api.marcarTransparente(imagen.id, marcando).subscribe({
      next: (galeria) => {
        this.hubocambios.set(true);
        this.imagenes.set(galeria);
        this.cargando.set(false);
        this.mostrar(
          marcando ? 'Imagen marcada para el vestidor virtual.' : 'Marca quitada.',
        );
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        // El motivo importa y no se resume en «no se pudo»: o falta asociarla a
        // una variante, o el archivo no tiene fondo transparente. Son dos
        // arreglos distintos.
        this.error.set(e.mensaje);
      },
    });
  }

  // --- 3d Reordenar ------------------------------------------------------

  protected mover(imagen: Imagen, direccion: -1 | 1): void {
    const actual = this.imagenes();
    const desde = actual.findIndex((i) => i.id === imagen.id);
    const hasta = desde + direccion;
    if (desde < 0 || hasta < 0 || hasta >= actual.length) return;

    const orden = actual.map((i) => i.id);
    [orden[desde], orden[hasta]] = [orden[hasta], orden[desde]];

    this.cargando.set(true);
    this.api.reordenarImagenes(this.producto.id, { imagenes: orden }).subscribe({
      next: (galeria) => {
        this.hubocambios.set(true);
        this.imagenes.set(galeria);
        this.cargando.set(false);
      },
      error: (e: ErrorProductos) => {
        this.cargando.set(false);
        this.mostrar(e.mensaje);
      },
    });
  }

  // --- 3e Eliminar -------------------------------------------------------

  protected eliminar(imagen: Imagen): void {
    const aviso = imagen.es_principal
      ? ' Es la imagen principal: otra tomará su lugar.'
      : '';
    this.dialogo
      .open(Confirmacion, {
        data: {
          titulo: 'Eliminar imagen',
          mensaje: `La imagen se borrará del catálogo y del servidor.${aviso}`,
          confirmar: 'Eliminar',
          peligrosa: true,
        } satisfies DatosConfirmacion,
      })
      .afterClosed()
      .subscribe((confirmado) => {
        if (!confirmado) return;
        this.cargando.set(true);
        this.api.eliminarImagen(imagen.id).subscribe({
          next: () => {
            this.hubocambios.set(true);
            this.mostrar('Imagen eliminada.');
            this.cargar();
          },
          error: (e: ErrorProductos) => {
            this.cargando.set(false);
            this.mostrar(e.mensaje);
          },
        });
      });
  }

  protected cerrar(): void {
    this.ref.close(this.hubocambios());
  }

  private mostrar(mensaje: string): void {
    this.aviso.open(mensaje, 'Cerrar', { duration: 4000 });
  }
}
