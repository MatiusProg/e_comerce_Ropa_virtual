# Violet Boutique — aplicación móvil (Flutter)

Aplicación del **Cliente**: catálogo, disponibilidad por sucursal, **vestidor
virtual con realidad aumentada**, reservas, compra y asistente.

> **Estado: compila y corre en un teléfono real.** Están la carpeta `android/`,
> el cliente HTTP con interceptor de token, el enrutado con guarda de sesión y
> las pantallas de **registro (CU-01)** e **inicio de sesión (CU-02)** contra la
> API desplegada. Falta todo el Ciclo 2: catálogo (CU-17 a CU-19) y reservas
> (CU-22, CU-23).
>
> **Verificado:** `flutter analyze` sin observaciones, `flutter test` pasa, el
> contrato de `/auth` contrastado campo por campo contra el `openapi.json` de la
> API desplegada, y el APK instalado y corriendo en un Xiaomi con Android 16.

## Versión de Flutter

**`3.47.2` (canal `stable`), Dart `3.13.2`** — la misma en las dos máquinas.

No es una preferencia: el `pubspec.yaml` declara `sdk: ">=3.5.0 <4.0.0"`, y
`go_router`, `flutter_riverpod` y `dio` en las versiones fijadas son de la era
Dart 3. Un Flutter anterior a la serie 3.4x no resuelve las dependencias: falla
en `flutter pub get`. El `pubspec.lock` se versiona y no se regenera por gusto,
porque dos versiones distintas producen dos *lock* distintos y el conflicto
aparece recién cuando el otro no puede compilar.

## Cómo ejecutarla

```bash
cd mobile
flutter pub get
flutter run             # con un emulador o un teléfono conectado
```

Por omisión la app consume la **API desplegada en Railway**, así que arranca sin
necesidad de levantar el backend. Para apuntar a un backend local:

```bash
flutter run --dart-define=API_URL=http://10.0.2.2:8000/api/v1
```

En el emulador de Android `localhost` es el propio emulador; la máquina
anfitriona es `10.0.2.2`.

En un **teléfono físico** `10.0.2.2` tampoco sirve: hay que usar la IP de la PC
en la red local, y el backend tiene que escuchar en `0.0.0.0`, no en
`127.0.0.1`.

Verificación sin dispositivo:

```bash
flutter analyze         # sin errores
flutter test            # prueba de arranque y redirección al login
```

## Tres cosas que hacen fallar el build, y ya están resueltas

Las tres se encontraron al compilar el APK por primera vez. Quedan documentadas
porque ninguna se deduce leyendo el código.

**1 · `compileSdk` tiene que ser 37, fijado a mano.** `flutter_secure_storage`
11 exige compilar contra la API 37; `flutter.compileSdkVersion` hoy resuelve a
36 y el build muere en `CheckAarMetadata` antes de compilar una sola clase. No
es un problema de memoria: con 8 GB o con 64 el resultado es el mismo. Está
fijado en `android/app/build.gradle.kts` con el motivo comentado.

**2 · Sin caché incremental de Kotlin.** Recortar la memoria de la JVM (que sí
hace falta en máquinas de 8 GB) era necesario pero no suficiente: con esos
límites puestos, el build sigue fallando con *«Could not close incremental
caches»* en un plugin distinto cada vez. Windows no libera los archivos que el
compilador de Kotlin mapea en memoria. `kotlin.incremental=false` en
`android/gradle.properties` lo resuelve: compila entero cada vez, más lento pero
determinista.

**3 · Teléfonos Xiaomi / HyperOS rechazan `adb install`** con
`INSTALL_FAILED_USER_RESTRICTED` hasta que se habilita **Opciones de
desarrollador › Instalar vía USB**, y hay que aceptar una ventana flotante que
aparece en el teléfono durante unos segundos. Es un ajuste del dispositivo, no
del proyecto. HyperOS además bloquea `adb shell input`, así que las pruebas de
interfaz se hacen a mano: no se pueden guionar desde la PC.

## Estructura de `lib/`

```
lib/
├── main.dart                Punto de entrada (ProviderScope)
├── app.dart                 MaterialApp.router, tema y localización
├── core/
│   ├── constantes.dart      API_URL (--dart-define), tiempos, claves
│   ├── tema.dart            Paleta malva y oro rosa, igual que la web
│   ├── red/                 Dio + interceptor de token, traducción de errores
│   ├── almacenamiento/      Token JWT en almacenamiento cifrado
│   └── enrutado/            go_router + guarda de sesión
├── data/
│   ├── modelos/             Espejo de los esquemas de la API
│   └── repositorios/        Un repositorio por paquete de análisis
└── features/
    ├── auth/                Registro e inicio de sesión           · ciclo 1
    ├── inicio/              Pantalla de carga y de inicio         · ciclo 1
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

Ya declarados en `android/app/src/main/AndroidManifest.xml`: `INTERNET` (la API)
y `CAMERA` (vestidor virtual). La cámara se declara además como
`uses-feature ... required="false"` para no excluir dispositivos sin cámara del
listado de instalación.

El identificador de la aplicación es **`bo.edu.uagrm.violetboutique`**. El
comando de generación producía `bo.edu.uagrm.violetboutique.violetboutique`,
porque el `--org` ya terminaba en el nombre del proyecto; se corrigió a mano en
`android/app/build.gradle.kts` y en `MainActivity.kt`.

## Distribución

La app no se publica en Google Play (fuera de alcance). Para la defensa se
genera un APK firmado y se sube a las *releases* del repositorio:

```bash
flutter build apk --release
```
