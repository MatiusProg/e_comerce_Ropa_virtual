import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { firstValueFrom, isObservable, of } from 'rxjs';

import { destinoTrasLogin, inicioGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

/**
 * La puerta del sitio y la vuelta después de iniciar sesión.
 *
 * Se prueban las dos decisiones que el 25/09 cambiaron el recorrido del
 * visitante: la raíz lleva a la vitrina, y quien entra desde una prenda vuelve
 * a esa prenda. Y la excepción que evita que un empleado quede varado en la
 * tienda por haber entrado por el botón de todos.
 */

describe('A dónde ir después de iniciar sesión', () => {
  it('vuelve a la prenda que el cliente estaba mirando', () => {
    expect(destinoTrasLogin('/tienda/producto/12', 'CLIENTE', '/mi-cuenta')).toBe(
      '/tienda/producto/12',
    );
  });

  it('conserva los filtros del catálogo', () => {
    expect(destinoTrasLogin('/tienda?categoria=3&pagina=2', 'CLIENTE', '/mi-cuenta')).toBe(
      '/tienda?categoria=3&pagina=2',
    );
  });

  it('manda al empleado a su área aunque haya entrado desde la tienda', () => {
    expect(destinoTrasLogin('/tienda', 'CAJERO', '/caja')).toBe('/caja');
    expect(destinoTrasLogin('/tienda/producto/12', 'ADMINISTRADOR', '/admin')).toBe('/admin');
  });

  it('respeta la ruta protegida que el empleado quiso abrir', () => {
    // El flujo 6a de CU-02 de siempre: la guarda lo mandó al login.
    expect(destinoTrasLogin('/caja/vender', 'CAJERO', '/caja')).toBe('/caja/vender');
  });

  it('sin destino, va al área del rol', () => {
    expect(destinoTrasLogin(null, 'CLIENTE', '/mi-cuenta')).toBe('/mi-cuenta');
    expect(destinoTrasLogin('', 'ENCARGADO', '/sucursal')).toBe('/sucursal');
  });

  it('descarta un destino que saca del sitio', () => {
    // El parámetro viaja en la URL: cualquiera puede armar un enlace así.
    expect(destinoTrasLogin('https://otro.com', 'CLIENTE', '/mi-cuenta')).toBe('/mi-cuenta');
    expect(destinoTrasLogin('//otro.com/x', 'CLIENTE', '/mi-cuenta')).toBe('/mi-cuenta');
  });

  it('no vuelve al login ni al registro', () => {
    expect(destinoTrasLogin('/login', 'CLIENTE', '/mi-cuenta')).toBe('/mi-cuenta');
    expect(destinoTrasLogin('/registro', 'CLIENTE', '/mi-cuenta')).toBe('/mi-cuenta');
  });
});

describe('La raíz del sitio', () => {
  function configurar(auth: Partial<AuthService>) {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useValue: auth },
      ],
    });
  }

  async function aDonde(): Promise<string> {
    const r = TestBed.runInInjectionContext(() => inicioGuard({} as any, {} as any));
    const arbol = (isObservable(r) ? await firstValueFrom(r) : r) as UrlTree;
    return TestBed.inject(Router).serializeUrl(arbol);
  }

  it('lleva al visitante sin sesión a la vitrina', async () => {
    configurar({ autenticado: (() => false) as any, token: null });

    expect(await aDonde()).toBe('/tienda');
  });

  it('lleva a quien tiene sesión a su área', async () => {
    configurar({
      autenticado: (() => true) as any,
      token: 'x',
      inicioDelRol: () => '/caja',
    });

    expect(await aDonde()).toBe('/caja');
  });

  it('con un token guardado, pregunta antes de decidir', async () => {
    // El caso del F5: hay token pero todavía no se sabe de quién.
    configurar({
      autenticado: (() => false) as any,
      token: 'x',
      restaurarSesion: () => of({ rol: 'ADMINISTRADOR' } as any),
      inicioDelRol: () => '/admin',
    });

    expect(await aDonde()).toBe('/admin');
  });

  it('con un token vencido, a la vitrina', async () => {
    configurar({
      autenticado: (() => false) as any,
      token: 'viejo',
      restaurarSesion: () => of(null),
    });

    expect(await aDonde()).toBe('/tienda');
  });
});
