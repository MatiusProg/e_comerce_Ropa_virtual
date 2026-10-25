import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

/**
 * El componente raíz de la aplicación.
 *
 * `App` no pinta nada propio: es la cáscara que hospeda el `<router-outlet>`,
 * y toda la interfaz entra por ahí. Desde el CU-12 además pide la marca de la
 * tienda al arrancar: por eso lleva un `HttpClient` de pruebas. Por eso lo único que vale comprobar acá es
 * que el outlet esté — si alguien lo saca, la aplicación compila, arranca y
 * queda en blanco, sin un error que lo delate.
 *
 * > **Esta prueba reemplazó a la del andamiaje del Angular CLI**, que exigía un
 * > `<h1>` con «Hello, frontend-web». Ese encabezado era la plantilla de
 * > arranque y se borró al construir la aplicación de verdad, así que la prueba
 * > llevaba desde el primer commit afirmando algo que el proyecto había
 * > decidido no tener.
 */
describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
  });

  it('se crea', () => {
    const fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('hospeda el router-outlet, que es lo único que hace', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;

    expect(raiz.querySelector('router-outlet')).not.toBeNull();
  });
});
