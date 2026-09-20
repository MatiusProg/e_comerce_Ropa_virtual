import { Component, OnInit, ViewChild, ElementRef, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import {
  AsistenteService,
  type Turno,
} from '../../../core/services/asistente.service';

/**
 * CU-34 · Conversar con el asistente virtual — «boundary» PantallaAsistente.
 *
 * Realiza el **RF25** junto con CU-33 y CU-35.
 *
 * SI NO HAY MODELO, NO SE OFRECE
 * --------------------------------
 * Se pregunta antes de dibujar nada. **Sin modelo no hay degradación
 * posible**: el recomendador de CU-33 puede caer a popularidad —una lista
 * ordenada por ventas sigue sirviendo— y acá no hay equivalente. Un
 * asistente que contesta con frases armadas daría respuestas que parecen del
 * sistema y no salen de sus datos.
 *
 * LOS CÓDIGOS DE PRENDA SE SACAN DEL TEXTO
 * ------------------------------------------
 * El modelo escribe `[#12]` y la pantalla lo convierte en un botón. Se quita
 * del párrafo porque leerlo entre corchetes no aporta nada, y los productos
 * vienen aparte **ya validados contra el catálogo**: uno inventado no llega.
 */
@Component({
  selector: 'app-asistente',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './asistente.html',
  styleUrl: './asistente.scss',
})
export class Asistente implements OnInit {
  private readonly api = inject(AsistenteService);
  private readonly router = inject(Router);

  @ViewChild('conversacion') private conversacion?: ElementRef<HTMLElement>;

  protected readonly cargando = signal(true);
  protected readonly disponible = signal(false);
  protected readonly ejemplos = signal<string[]>([]);
  protected readonly turnos = signal<Turno[]>([]);
  protected readonly pensando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly pregunta = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    this.api.disponible().subscribe((e) => {
      this.disponible.set(e.disponible);
      this.ejemplos.set(e.ejemplos);
      this.cargando.set(false);
    });
  }

  protected enviar(texto?: string): void {
    const consulta = (texto ?? this.pregunta.value).trim();
    if (consulta.length < 2 || this.pensando()) return;

    this.pensando.set(true);
    this.error.set(null);
    this.pregunta.setValue('');
    this.alFinal();

    this.api.preguntar(consulta, this.turnos()).subscribe({
      next: (r) => {
        this.turnos.update((t) => [
          ...t,
          { pregunta: consulta, respuesta: r.texto, productos: r.productos },
        ]);
        this.pensando.set(false);
        this.alFinal();
      },
      error: (e) => {
        this.pensando.set(false);
        this.error.set(
          e?.error?.detail ?? 'No pude responder ahora. Probá de nuevo.',
        );
      },
    });
  }

  protected verPrenda(id: number): void {
    this.router.navigate(['/tienda/producto', id]);
  }

  /** Saca los `[#12]` del párrafo: en la pantalla son botones. */
  protected sinCodigos(texto: string): string {
    return texto.replace(/\[[^\]]*?#\d+[^\]]*?\]/g, '').replace(/ {2,}/g, ' ');
  }

  private alFinal(): void {
    // En el siguiente ciclo, cuando el mensaje nuevo ya está en el DOM.
    setTimeout(() => {
      const caja = this.conversacion?.nativeElement;
      if (caja) caja.scrollTop = caja.scrollHeight;
    });
  }
}
