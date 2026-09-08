# Violet Boutique — aplicación móvil (Flutter)

Aplicación del **Cliente**: catálogo, disponibilidad por sucursal, **vestidor
virtual con realidad aumentada**, reservas, compra y asistente.

> **Estado:** el proyecto Android está generado y el *shell* funciona: registro
> (CU-01), inicio y cierre de sesión (CU-02) contra la API desplegada.

## Versiones — las mismas en las dos máquinas

| | Versión | Por qué está fijada |
|---|---|---|
| Flutter | **3.47.2** (`stable`), Dart **3.13.2** | El `pubspec.yaml` exige `sdk >=3.5.0`, y `go_router 18`, `flutter_riverpod 3.4` y `dio 5.11` son de la era Dart 3. Nada anterior a la serie 3.4x resuelve las dependencias. |
| `compileSdk` | **37** | `flutter_secure_storage` 11 lo exige: contra la 36 el build falla en `CheckAarMetadata`. Está fijado a mano en `android/app/build.gradle.kts`, no vía `flutter.compileSdkVersion`, que hoy resuelve a 36. |

Antes de escribir código, `flutter --version` en las dos máquinas. Si no
coinciden, se iguala primero: dos versiones producen dos `pubspec.lock`
distintos y el problema aparece recién cuando el otro no puede compilar. El
`pubspec.lock` se versiona.

## Cómo arrancar

```bash
cd mobile
flutter pub get
flutter run                     # contra la API de Railway, por defecto
```

Para apuntar al backend local, la IP de la PC en la red — para el teléfono
`localhost` es el teléfono:

```bash
flutter run --dart-define=API_URL=http://192.168.0.10:8000/api/v1
```

### Teléfonos Xiaomi / HyperOS

`adb install` falla con `INSTALL_FAILED_USER_RESTRICTED` hasta que se habilita
**Opciones de desarrollador › Instalar vía USB**. Es un ajuste del teléfono, no
del proyecto.

### Si el build falla con «Could not close incremental caches»

Ya está resuelto: `android/gradle.properties` desactiva la caché incremental de
Kotlin, que en Windows no libera sus archivos mapeados en memoria y rompe el
build en un plugin distinto cada vez.

## Estructura de `lib/`

```
lib/
├── core/                    Cliente HTTP (Dio) + interceptor de token, tema,
│                            enrutado (go_router), constantes
├── data/                    Modelos del contrato de la API y repositorios
└── features/
    ├── auth/                Registro e inicio de sesión           · hecho
    ├── catalogo/            Catálogo, ficha, disponibilidad        · ciclo 2
    ├── reservas/            Crear, consultar y cancelar reservas   · ciclo 2
    ├── vestidor_virtual/    P9 · cámara + pose + superposición     · ciclo 3
    ├── compra/              Carrito, pago e historial              · ciclo 3
    └── asistente/           Chat y recomendaciones                 · ciclo 3
```

## Vestidor virtual — cómo está pensado

El enfoque elegido es **superposición 2D guiada por detección de pose**, no
reconstrucción 3D. El razonamiento y las alternativas descartadas están en
[`docs/06-decisiones-tecnicas.md`](../docs/06-decisiones-tecnicas.md) §6.5.

1. `camera` entrega los fotogramas de la cámara frontal.
2. `google_mlkit_pose_detection` devuelve los puntos del cuerpo — todo el
   procesamiento ocurre **en el dispositivo**, sin costo por uso ni latencia
   de red.
3. A partir de los hombros y las caderas se calculan ancho, alto, centro e
   inclinación del torso.
4. La imagen PNG de la variante se dibuja transformada sobre esos valores en
   un `CustomPainter` encima de la vista de cámara.
5. El cliente cambia talla/color sin salir de la vista, captura el resultado y
   agrega la prenda a la reserva o al carrito.

**Dependencia crítica:** cada variante necesita un PNG frontal **con fondo
transparente** y proporciones consistentes (supuesto S5 del alcance). Sin eso
el vestidor virtual no funciona, por bien programado que esté. Esas imágenes
tienen que estar cargadas antes de empezar el ciclo 3.

## Permisos de Android

`INTERNET` ya está declarado en `android/app/src/main/AndroidManifest.xml`.
Hacía falta agregarlo a mano: Flutter solo lo pone en los manifiestos de
`debug` y `profile`, así que sin esa línea la versión de *release* compila pero
no puede hacer una sola petición.

`CAMERA` se agrega al construir el prototipo del vestidor virtual:

```xml
<uses-permission android:name="android.permission.CAMERA" />
```

## Distribución

La app no se publica en Google Play (fuera de alcance). Para la defensa se
genera un APK firmado y se sube a las *releases* del repositorio:

```bash
flutter build apk --release
```
