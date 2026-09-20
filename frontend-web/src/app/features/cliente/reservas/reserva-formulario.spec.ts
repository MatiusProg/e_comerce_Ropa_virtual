import { Component, provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { appConfig } from '../../../app.config';

/**
 * CU-22 · Que el datepicker de la reserva **se pueda dibujar**.
 *
 * POR QUÉ ESTA PRUEBA EXISTE
 * --------------------------
 * `MatDatepickerModule` **no trae su propio `DateAdapter`**: hay que proveerlo
 * en la configuración de la aplicación. Sin él, el datepicker lanza
 *
 *     MatDatepicker: No provider found for DateAdapter
 *
 * en **tiempo de ejecución**, no al compilar. El proyecto entero compila,
 * arranca y se despliega sin que nada avise, y el fallo aparece recién cuando
 * alguien abre el formulario — que en una demostración es el peor momento.
 *
 * POR QUÉ NO SE MONTA `ReservaFormulario` DIRECTAMENTE
 * -----------------------------------------------------
 * Porque su datepicker vive dentro de `@if (lineas().length)`: sólo se dibuja
 * **después** de que el cliente agregó prendas. Un diálogo recién abierto no lo
 * instancia, así que montarlo y ver que no explota **no probaría nada** — es
 * exactamente el falso negativo que hizo que este defecto pasara inadvertido.
 *
 * Se monta entonces un anfitrión mínimo con un datepicker siempre visible y
 * **los proveedores reales de la aplicación**. Comprobar contra proveedores
 * inventados para la prueba diría que un datepicker *puede* funcionar, no que
 * funciona con lo que la aplicación de verdad le da.
 */
@Component({
  selector: 'app-anfitrion-datepicker',
  imports: [MatDatepickerModule, MatFormFieldModule, MatInputModule],
  template: `
    <mat-form-field>
      <input matInput [matDatepicker]="calendario" />
      <mat-datepicker-toggle matIconSuffix [for]="calendario" />
      <mat-datepicker #calendario />
    </mat-form-field>
  `,
})
class AnfitrionDatepicker {}

describe('El datepicker de la reserva (CU-22)', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AnfitrionDatepicker],
      providers: [
        // La configuración REAL de la aplicación: es lo que se está probando.
        ...appConfig.providers,
        provideZonelessChangeDetection(),
        provideHttpClient(),
      ],
    }).compileComponents();
  });

  it('se dibuja con los proveedores reales de la aplicación', async () => {
    const fixture = TestBed.createComponent(AnfitrionDatepicker);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;

    // Si faltara el `DateAdapter`, `whenStable` habría lanzado antes de llegar
    // acá: el datepicker lo pide en su constructor.
    expect(raiz.querySelector('mat-datepicker-toggle')).not.toBeNull();
  });
});
