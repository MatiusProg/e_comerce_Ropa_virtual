import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { CobroQr, VIGENCIA_QR_S } from './cobro-qr';

/**
 * CU-31 · La simulación del cobro con QR.
 *
 * Lo que importa probar es qué devuelve el diálogo en cada desenlace, porque
 * de eso depende que se registre o no una venta: la referencia SOLO cuando el
 * banco aprobó, y `null` en todo lo demás.
 */
describe('Cobro con QR (CU-31, simulación)', () => {
  let componente: any;
  let ref: { close: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    vi.useFakeTimers();
    ref = { close: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [CobroQr],
      providers: [
        provideZonelessChangeDetection(),
        { provide: MatDialogRef, useValue: ref },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { total: '250.00', sucursal: 'Violet Ventura Mall', caja: 'Caja 1' },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(CobroQr);
    componente = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    TestBed.resetTestingModule(); // destruye el diálogo: corta sus relojes
    vi.useRealTimers();
  });

  it('arranca esperando, con un QR dibujado', () => {
    expect(componente.estado()).toBe('esperando');
    expect(componente.qr().size).toBeGreaterThan(20);
    expect(componente.qr().d.length).toBeGreaterThan(0);
  });

  it('si el cliente paga, devuelve la referencia del cobro', () => {
    const referencia = componente.referencia();

    componente.simularPago();
    expect(componente.estado()).toBe('confirmando');
    expect(ref.close).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5000);

    expect(componente.estado()).toBe('aprobado');
    expect(ref.close).toHaveBeenCalledWith(referencia);
  });

  it('si el banco rechaza, no cierra con referencia y dice por qué', () => {
    componente.simularRechazo();
    vi.advanceTimersByTime(5000);

    expect(componente.estado()).toBe('rechazado');
    expect(componente.motivo()).not.toBe('');
    expect(ref.close).not.toHaveBeenCalled();
  });

  it('vence cuando se acaba el tiempo, y un vencido ya no se puede pagar', () => {
    vi.advanceTimersByTime(VIGENCIA_QR_S * 1000);

    expect(componente.estado()).toBe('vencido');

    componente.simularPago();
    vi.advanceTimersByTime(5000);
    expect(ref.close).not.toHaveBeenCalled();
  });

  it('otro intento genera un QR nuevo, con otra referencia y el reloj entero', () => {
    const antes = componente.referencia();
    const contenidoAntes = componente.contenido();
    vi.advanceTimersByTime(VIGENCIA_QR_S * 1000);

    componente.reintentar();

    expect(componente.estado()).toBe('esperando');
    expect(componente.referencia()).not.toBe(antes);
    expect(componente.contenido()).not.toBe(contenidoAntes);
    expect(componente.restante()).toBe(VIGENCIA_QR_S);
  });

  it('desistir cierra sin referencia', () => {
    componente.desistir();

    expect(ref.close).toHaveBeenCalledWith(null);
  });
});
