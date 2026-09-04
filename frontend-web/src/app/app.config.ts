import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    // Sin esto ningun servicio puede llamar a la API. Cuando exista el
    // interceptor JWT (CU-02) se registra aca con withInterceptors(...).
    provideHttpClient(withFetch()),
    // No se registra provideAnimations*: Angular Material 22 resuelve sus
    // animaciones con CSS y no necesita el paquete @angular/animations.
  ],
};
