import { contenidoQr, crc16, nuevaReferencia } from './qr-emv';

/**
 * El contenido del QR de cobro.
 *
 * Lo que se prueba es que una aplicación bancaria lo pudiera leer: que cada
 * campo tenga el largo que dice tener y que el CRC cierre. Un QR con el CRC
 * mal calculado se ve perfecto en pantalla y ningún banco lo acepta.
 */

/** Separa la cadena EMVCo en sus campos, como lo haría el lector del banco. */
function campos(texto: string): Map<string, string> {
  const salida = new Map<string, string>();
  let i = 0;
  while (i < texto.length) {
    const id = texto.slice(i, i + 2);
    const largo = Number(texto.slice(i + 2, i + 4));
    salida.set(id, texto.slice(i + 4, i + 4 + largo));
    i += 4 + largo;
  }
  return salida;
}

const DATOS = {
  monto: '250.00',
  referencia: 'QR-ABCD2345',
  sucursal: 'Violet Ventura Mall',
  caja: 'Caja 1',
};

describe('Contenido del QR de cobro (EMVCo)', () => {
  it('calcula el CRC-16/CCITT-FALSE del valor de referencia', () => {
    // El vector de comprobación publicado para esta variante del CRC.
    expect(crc16('123456789')).toBe('29B1');
  });

  it('cierra con un CRC que coincide con el resto de la cadena', () => {
    const qr = contenidoQr(DATOS);
    const sinCrc = qr.slice(0, -4);

    expect(sinCrc.endsWith('6304')).toBe(true);
    expect(qr.slice(-4)).toBe(crc16(sinCrc));
  });

  it('lleva el monto, la moneda boliviana y el país', () => {
    const c = campos(contenidoQr(DATOS));

    expect(c.get('54')).toBe('250.00');
    expect(c.get('53')).toBe('068');
    expect(c.get('58')).toBe('BO');
    // 12 = dinámico: el código vale para este cobro y no para otro.
    expect(c.get('01')).toBe('12');
  });

  it('lleva la referencia y la caja en los datos adicionales', () => {
    const adicionales = campos(campos(contenidoQr(DATOS)).get('62')!);

    expect(adicionales.get('05')).toBe('QR-ABCD2345');
    expect(adicionales.get('07')).toBe('CAJA 1');
  });

  it('recorta la sucursal a los 15 caracteres que admite el campo y le quita los acentos', () => {
    const c = campos(contenidoQr({ ...DATOS, sucursal: 'Sucursal Equipetrol Norte' }));
    expect(c.get('60')).toBe('SUCURSAL EQUIPE');

    const conAcento = campos(contenidoQr({ ...DATOS, sucursal: 'Cochabamba Plaza Colón' }));
    expect(conAcento.get('60')).not.toMatch(/[^\x20-\x7E]/);
  });

  it('cambia el CRC si cambia un solo centavo', () => {
    const a = contenidoQr(DATOS);
    const b = contenidoQr({ ...DATOS, monto: '250.01' });

    expect(a.slice(-4)).not.toBe(b.slice(-4));
  });

  it('genera referencias distintas y con el formato esperado', () => {
    const vistas = new Set(Array.from({ length: 200 }, () => nuevaReferencia()));

    expect(vistas.size).toBe(200);
    for (const r of vistas) expect(r).toMatch(/^QR-[A-Z2-9]{8}$/);
  });
});
