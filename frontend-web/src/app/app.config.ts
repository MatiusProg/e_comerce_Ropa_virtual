import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { authInterceptor } from './core/interceptors/auth.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    // El interceptor adjunta el token a cada petición y reacciona al 401
    // descartando la sesión (CU-02).
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    // No se registra provideAnimations*: Angular Material 22 resuelve sus
    // animaciones con CSS y el paquete @angular/animations no está instalado.
  ],
};
