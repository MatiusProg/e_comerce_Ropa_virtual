import { Pipe, PipeTransform } from '@angular/core';

import { environment } from '../../environments/environment';

/**
 * Convierte una ruta de `/media/...` del backend en una URL absoluta.
 *
 * La API devuelve las imágenes como ruta relativa a SU origen. Usada tal cual
 * en un `<img>`, el navegador la pide al origen de la WEB, que es otro (otro
 * puerto en local, otro dominio en Railway), y la imagen sale rota. Así pasaba
 * en el carrito, en «Mis compras», en el checkout y en el retorno del pago.
 * Es la misma cuenta que `TiendaService.urlDeImagen`.
 */
@Pipe({ name: 'urlMedia' })
export class UrlMediaPipe implements PipeTransform {
  transform(ruta: string | null | undefined): string | null {
    if (!ruta) return null;
    if (/^https?:\/\//.test(ruta)) return ruta;
    return `${new URL(environment.apiUrl).origin}${ruta}`;
  }
}
