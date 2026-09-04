import {
  ApplicationConfig,
  LOCALE_ID,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { registerLocaleData } from '@angular/common';
import localeEsBo from '@angular/common/locales/es-BO';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { MatPaginatorIntl } from '@angular/material/paginator';
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
    // No se registra provideAnimations*: Angular Material 22 resuelve sus
    // animaciones con CSS y el paquete @angular/animations no está instalado.
  ],
};
