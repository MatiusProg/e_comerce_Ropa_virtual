import {
  ApplicationConfig,
  LOCALE_ID,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { registerLocaleData } from '@angular/common';
import localeEsBo from '@angular/common/locales/es-BO';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { MatPaginatorIntl } from '@angular/material/paginator';
import { provideNativeDateAdapter } from '@angular/material/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { authInterceptor } from './core/interceptors/auth.interceptor';
import { paginadorEnEspanol } from './core/paginador-es';
import { routes } from './app.routes';

// Sin esto, `date` y `number` formatean en inglés (12/25/2026 en vez de
// 25/12/2026), aunque el resto de la interfaz esté en español.
registerLocaleData(localeEsBo);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    // El interceptor adjunta el token a cada petición y reacciona al 401
    // descartando la sesión (CU-02).
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    { provide: LOCALE_ID, useValue: 'es-BO' },
    { provide: MatPaginatorIntl, useFactory: paginadorEnEspanol },
    // EL DATEPICKER NO TRAE SU PROPIO `DateAdapter` --- y sin él LANZA.
    //
    // `MatDatepickerModule` no lo incluye: hay que proveerlo acá. Sin esta
    // línea, todo compila, arranca y se despliega sin que nada avise, y el
    // formulario de reserva (CU-22) revienta en tiempo de ejecución en cuanto
    // el cliente agrega una prenda y aparece el calendario:
    //
    //     MatDatepicker: No provider found for DateAdapter
    //
    // Estuvo faltando desde que se escribió CU-22. No se notó porque el
    // datepicker vive dentro de un `@if`: abrir el diálogo vacío no lo
    // instancia, así que probarlo a mano «sin agregar nada» daba bien.
    //
    // El nativo alcanza: las fechas viajan como cadena ISO y el `LOCALE_ID` de
    // arriba ya las formatea en es-BO. Los otros adaptadores existen para
    // trabajar con Luxon, date-fns o Moment, que este proyecto no usa.
    provideNativeDateAdapter(),
    // Chart.js NO se provee acá: ver la nota de la ruta 'admin/tablero' en
    // app.routes.ts. Ponerlo en esta lista sumaba 211 kB al arranque de TODAS
    // las pantallas, incluida la vitrina pública en un teléfono.
    // No se registra provideAnimations*: Angular Material 22 resuelve sus
    // animaciones con CSS y el paquete @angular/animations no está instalado.
  ],
};
