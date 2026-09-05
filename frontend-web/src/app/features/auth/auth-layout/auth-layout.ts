import { Component, input } from '@angular/core';

/**
 * Cáscara visual compartida por las pantallas sin sesión (CU-01 y CU-02).
 *
 * Dos columnas: a la izquierda el panel de marca con el degradado malva, a la
 * derecha el formulario. En pantallas angostas el panel se vuelve un
 * encabezado delgado y el formulario ocupa todo el ancho (RNF05).
 *
 * Existe como componente y no como estilos repetidos para que login y registro
 * no puedan divergir: si la marca cambia, cambia en un solo archivo.
 */
@Component({
  selector: 'app-auth-layout',
  template: `
    <div class="marco">
      <aside class="marca">
        <div class="marca-contenido">
          <p class="logotipo">Violet Boutique</p>
          <p class="lema">Tu estilo, a tu medida.</p>
          <p class="detalle">
            Reservá para probar en sucursal, probate las prendas con el vestidor
            virtual y comprá desde donde estés.
          </p>
        </div>
        <div class="brillo brillo-a"></div>
        <div class="brillo brillo-b"></div>
      </aside>

      <section class="panel">
        <div class="tarjeta-envoltorio">
          <p class="encabezado">
            <span class="titulo vb-titulo">{{ titulo() }}</span>
            @if (subtitulo()) {
              <span class="subtitulo">{{ subtitulo() }}</span>
            }
          </p>
          <ng-content />
        </div>
      </section>
    </div>
  `,
  styleUrl: './auth-layout.scss',
})
export class AuthLayout {
  readonly titulo = input.required<string>();
  readonly subtitulo = input<string>('');
}
