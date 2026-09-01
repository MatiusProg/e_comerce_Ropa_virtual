# FashionStore — aplicación móvil (Flutter)

Aplicación del **Cliente**: catálogo, disponibilidad por sucursal, **vestidor
virtual con realidad aumentada**, reservas, compra y asistente.

> **Estado:** solo está el esqueleto de `lib/` y el `pubspec.yaml`. Las carpetas
> de plataforma (`android/`, `ios/`, `web/`) todavía no existen porque Flutter
> no está instalado en la máquina donde se generó la estructura.

## Cómo completar el proyecto

Flutter no estaba instalado al crear esta carpeta. Una vez instalado, este
comando **completa** el proyecto respetando lo que ya existe (`pubspec.yaml` y
`lib/` no se sobrescriben):

```bash
cd mobile
flutter create . --org bo.edu.uagrm.fashionstore --platforms android --project-name fashionstore
flutter pub get
```

Verificación:

```bash
flutter doctor          # todo en verde para Android
flutter run             # con un emulador o un teléfono conectado
```

## Estructura de `lib/`

```
lib/
├── core/                    Cliente HTTP (Dio) + interceptor de token, tema,
│                            enrutado (go_router), constantes
├── data/                    Modelos del contrato de la API y repositorios
└── features/
    ├── auth/                Registro e inicio de sesión           · ciclo 1
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

Agregar en `android/app/src/main/AndroidManifest.xml` una vez generado:

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
```

## Distribución

La app no se publica en Google Play (fuera de alcance). Para la defensa se
genera un APK firmado y se sube a las *releases* del repositorio:

```bash
flutter build apk --release
```
