import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';

import { Turno } from './turno';
import { CajaService } from '../../../core/services/caja.service';
import type { Turno as TurnoModelo } from '../../../core/models/caja.models';

/**
 * CU-30 · La diferencia del arqueo, calculada mientras se escribe.
 *
 * POR QUÉ ESTA PRUEBA EXISTE
 * --------------------------
 * Porque el defecto ya pasó. `diferencia` era un `computed` que leía
 * `montoCierre.value`, y **el valor de un `FormControl` no es una señal**: el
 * `computed` no registraba dependencia, no se invalidaba nunca y devolvía para
 * siempre lo que calculó la primera vez —nulo—.
 *
 * La consecuencia era que **la diferencia antes de confirmar no aparecía
 * nunca**, que es justamente lo que esta pantalla existe para mostrar: quien
 * cierra tiene que ver lo que está por declarar, no enterarse después. Y nada
 * avisaba: la pantalla se dibuja igual, solo que sin ese párrafo.
 *
 * Lo encontró la prueba equivalente de CU-31 sobre el vuelto, que tiene la
 * misma forma. Esta es para que no vuelva a pasar del lado del cierre.
 */

const TURNO: TurnoModelo = {
  id: 1,
  caja_id: 1,
  caja_nombre: 'Caja 1',
  sucursal_nombre: 'Centro',
  abierto_en: '2026-09-20T12:00:00Z',
  cerrado_en: null,
  monto_apertura: '100.00',
  efectivo_cobrado: '500.00',
  devoluciones: '0.00',
  monto_esperado: '600.00',
  monto_cierre: null,
  diferencia: null,
  por_metodo: [],
};

describe('El arqueo del turno (CU-30)', () => {
  let componente: any;

  beforeEach(async () => {
    const turno = signal<TurnoModelo | null>(TURNO);
    const caja = {
      turno: turno.asReadonly(),
      miTurno: () => of(TURNO),
      cajas: () => of([]),
      abrir: () => of(TURNO),
      cerrar: () => of(TURNO),
    };

    await TestBed.configureTestingModule({
      imports: [Turno],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        { provide: CajaService, useValue: caja },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(Turno);
    componente = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('la diferencia se recalcula al escribir el monto contado', () => {
    // Antes de escribir no hay nada que declarar.
    expect(componente.diferencia()).toBeNull();

    // El sistema esperaba 600. Se contaron 620: sobran 20.
    componente.montoCierre.setValue('620.00');
    expect(componente.diferencia()).toBe(20);
  });

  it('un faltante da negativo', () => {
    componente.montoCierre.setValue('550.00');
    expect(componente.diferencia()).toBe(-50);
  });

  it('cuando cuadra da cero, y cero no es nulo', () => {
    // La pantalla distingue «cuadra» de «todavía no escribió nada», y son dos
    // mensajes distintos: uno tranquiliza y el otro no dice nada.
    componente.montoCierre.setValue('600.00');
    expect(componente.diferencia()).toBe(0);
  });

  it('acepta coma además de punto', () => {
    componente.montoCierre.setValue('620,50');
    expect(componente.diferencia()).toBeCloseTo(20.5);
  });

  it('un monto a medio escribir no alarma con un número enorme', () => {
    // Mostrar «−Bs 594,00» porque la persona tecleó el primer dígito sería
    // asustarla por nada.
    componente.montoCierre.setValue('6');
    expect(componente.diferencia()).toBe(-594);

    componente.montoCierre.setValue('600.');
    expect(componente.diferencia()).toBeNull();
  });
});
