// Sin `provideNoopAnimations`: `@angular/animations` no está instalado en el
// proyecto —la aplicación tampoco lo usa— y pedirlo acá haría que la prueba
// dependiera de algo que la aplicación de verdad no tiene.
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';

import { Venta } from './venta';
import { PosService } from '../../../core/services/pos.service';
import { CajaService } from '../../../core/services/caja.service';
import type { PrendaEnMostrador, ReservaPorCobrar } from '../../../core/models/pos.models';

/**
 * CU-31 · Las cuentas del mostrador.
 *
 * POR QUÉ SE PRUEBA EL DINERO Y NO EL DIBUJO
 * -------------------------------------------
 * Un botón que no se ve se descubre abriendo la pantalla. Un centavo mal
 * sumado **no se ve nunca**: el ticket sale, el cliente se va, y el descuadre
 * aparece cuatro horas después en el arqueo de CU-30 sin ninguna pista de de
 * dónde salió. Por eso lo que se prueba acá es la aritmética y las dos reglas
 * que la pantalla impone antes de llegar al servidor.
 *
 * `250.10 + 250.20` en coma flotante da `500.30000000000007`. Sumar en centavos
 * enteros es lo que evita que ese número llegue al cajón.
 */

function prenda(id: number, precio: string, disponible = 10): PrendaEnMostrador {
  return {
    variante_id: id,
    sku: `SKU-${id}`,
    producto: `Prenda ${id}`,
    talla: 'M',
    color: 'Negro',
    precio,
    disponible,
  };
}

const RESERVA: ReservaPorCobrar = {
  reserva_id: 7,
  cliente: 'Luz Vargas',
  atendida_en: '2026-09-20T14:00:00Z',
  lineas: [],
  total: '480.00',
};

describe('Venta presencial (CU-31)', () => {
  let componente: any;

  beforeEach(async () => {
    const pos = {
      prendas: () => of({ total: 0, pagina: 1, tamano: 40, items: [] }),
      reservasPorCobrar: () => of([]),
      cobrar: () => of(null),
      comprobante: () => of(new Blob()),
    };
    // Hay turno abierto: si devolviera `null`, la pantalla entraría por la cara
    // de «abra su caja» y no habría ticket que armar.
    const caja = {
      miTurno: () => of({ id: 1, caja_nombre: 'Caja 1', sucursal_nombre: 'Centro' }),
      turno: () => null,
    };

    await TestBed.configureTestingModule({
      imports: [Venta],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        { provide: PosService, useValue: pos },
        { provide: CajaService, useValue: caja },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(Venta);
    componente = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('suma el total en centavos, sin arrastrar coma flotante', () => {
    componente.agregar(prenda(1, '250.10'));
    componente.agregar(prenda(2, '250.20'));

    // En coma flotante esto daría «500.30000000000007».
    expect(componente.total()).toBe('500.30');
  });

  it('multiplica por la cantidad sin perder centavos', () => {
    componente.agregar(prenda(1, '33.33'));
    componente.cambiarCantidad(componente.lineas()[0], 3);

    expect(componente.total()).toBe('99.99');
  });

  it('volver a pulsar una prenda sube la cantidad y no la duplica', () => {
    // `detalle_venta` tiene UNIQUE (venta_id, variante_id): dos líneas de la
    // misma prenda reventarían en la base con un error de integridad que el
    // cajero leería como «error del sistema».
    const p = prenda(1, '100.00');
    componente.agregar(p);
    componente.agregar(p);
    componente.agregar(p);

    expect(componente.lineas().length).toBe(1);
    expect(componente.lineas()[0].cantidad).toBe(3);
    expect(componente.total()).toBe('300.00');
  });

  it('no deja pasar de las unidades que hay', () => {
    componente.agregar(prenda(1, '100.00', 2));
    componente.cambiarCantidad(componente.lineas()[0], 5);

    expect(componente.lineas()[0].cantidad).toBe(1);
  });

  it('bajar la cantidad a cero quita la línea', () => {
    componente.agregar(prenda(1, '100.00'));
    componente.cambiarCantidad(componente.lineas()[0], 0);

    expect(componente.lineas().length).toBe(0);
    expect(componente.total()).toBe('0.00');
  });

  it('calcula el vuelto solo con efectivo', () => {
    componente.agregar(prenda(1, '250.00'));
    componente.recibido.setValue('300.00');

    expect(componente.vuelto()).toBe(5000); // centavos

    componente.elegirMetodo('TARJETA');
    // Con tarjeta se cobra el importe exacto: dar vuelto ahí sería sacar plata
    // del cajón por un cobro que no entró.
    expect(componente.vuelto()).toBeNull();
  });

  it('avisa cuando lo recibido no alcanza', () => {
    componente.agregar(prenda(1, '250.00'));
    componente.recibido.setValue('100.00');

    expect(componente.vuelto()).toBeLessThan(0);
  });

  it('acepta coma además de punto al escribir el monto', () => {
    componente.agregar(prenda(1, '250.00'));
    componente.recibido.setValue('300,50');

    expect(componente.vuelto()).toBe(5050);
  });

  it('cargar una reserva reemplaza el total, y soltarla lo devuelve', () => {
    componente.cargarReserva(RESERVA);
    expect(componente.total()).toBe('480.00');
    expect(componente.hayQueCobrar()).toBe(true);

    componente.soltarReserva();
    expect(componente.total()).toBe('0.00');
    expect(componente.hayQueCobrar()).toBe(false);
  });

  it('los dos caminos son excluyentes', () => {
    // El servidor rechaza líneas y reserva juntas, y tiene razón. La pantalla
    // avisa en vez de dejar armar algo que va a fallar.
    componente.cargarReserva(RESERVA);
    componente.agregar(prenda(1, '100.00'));

    expect(componente.lineas().length).toBe(0);
    expect(componente.total()).toBe('480.00');
  });
});
