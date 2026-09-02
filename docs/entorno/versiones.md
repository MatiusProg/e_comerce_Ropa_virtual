# Entorno de desarrollo — versiones fijadas

Versiones verificadas el **02/09/2026** sobre Windows 11 Pro 25H2. Los dos
usamos exactamente estas: cuando una herramienta se desvía, los errores que
produce rara vez mencionan la versión, y se pierde media tarde buscando en el
lugar equivocado.

---

## Tabla de versiones

| Herramienta | Versión | Cómo se instaló |
|---|---|---|
| **Python** | **3.13.15** | `winget install --id Python.Python.3.13 -e` |
| **Node.js** | **24.19.0** | `winget install --id OpenJS.NodeJS -e` |
| **npm** | **11.17.0** | viene con Node |
| **Angular** | **22.1.0** (CLI 22.1.6) | `npm install` dentro de `frontend-web/` |
| **TypeScript** | **6.0.2** | dependencia de Angular |
| **Flutter** | **3.47.2** (canal stable) | ZIP oficial → `D:\dev\flutter` |
| **Dart** | **3.13.2** | viene con Flutter |
| **DevTools** | **2.60.0** | viene con Flutter |
| **Android Studio** | **2026.1.4.7** | `winget install --id Google.AndroidStudio -e` |
| **JDK** | **Temurin 17.0.20** | ya estaba instalado; es el que necesita Android |
| **Docker** | **29.7.2** | Docker Desktop |
| **PostgreSQL** | **16-alpine** (imagen Docker) | `docker pull postgres:16-alpine` |
| **Git** | **2.55.0** | Git for Windows |

---

## Qué instalar y en qué orden

### 1. Python 3.13 — **no 3.14**

```powershell
winget install --id Python.Python.3.13 -e
```

No es preferencia, es una restricción. `passlib` 1.7.4 —la biblioteca que
hashea las contraseñas de todo el sistema— no recibe mantenimiento desde 2020 y
no declara soporte para 3.14. Por lo mismo, **`bcrypt` está fijado en 4.3.0 y
no debe subir a 5.x**: passlib lee un atributo interno de bcrypt que la
versión 5 eliminó, y el error que tira no menciona ni a passlib ni a bcrypt.

Si ya tenés 3.14 instalado no hace falta desinstalarlo: conviven. El entorno
virtual fija cuál se usa.

```powershell
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Verificación: `python --version` dentro del venv debe decir **3.13.x**.

### 2. Node 20+ y las dependencias de Angular

```powershell
winget install --id OpenJS.NodeJS -e
cd frontend-web
npm install
```

No hace falta instalar el Angular CLI globalmente: está en las
`devDependencies` del proyecto y se usa con `npm start` / `npm run build`.

npm 11 avisa sobre *scripts* de instalación pendientes (`allow-scripts`). Es
una advertencia, no un error; no hay que hacer nada.

### 3. Docker Desktop y la imagen de PostgreSQL

```powershell
docker pull postgres:16-alpine
docker compose up -d          # desde la raíz del repositorio
```

La base local es solo para desarrollo. La de verdad vive en Railway.

### 4. Flutter 3.47.2 — **no está en winget**

Flutter no se distribuye por winget: hay que bajar el ZIP oficial.

- Página: <https://docs.flutter.dev/get-started/install/windows>
- ZIP directo de esta versión:
  <https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.47.2-stable.zip>

Pesa **1.8 GB**. Descomprimir en una ruta **sin espacios y sin permisos de
administrador** — `C:\` a secas da *permission denied*. En esta máquina quedó
en `D:\dev\flutter`; poné la que te sirva, pero evitá `C:\Program Files` y
cualquier carpeta con espacios en el nombre.

Después hay que agregar `<ruta>\flutter\bin` al **PATH del usuario**:

```powershell
$bin = 'D:\dev\flutter\bin'
$p = [Environment]::GetEnvironmentVariable('Path','User')
[Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';' + $bin), 'User')
```

Hay que **abrir una terminal nueva** para que tome el PATH.

### 5. Android Studio 2026.1.4.7

```powershell
winget install --id Google.AndroidStudio -e
```

O el instalador desde <https://developer.android.com/studio> (~1.4 GB).

Instalar Android Studio es solo el primero de **cuatro** pasos. Los otros tres
no son obvios y cada uno produce un mensaje distinto en `flutter doctor` que
parece decir otra cosa. Está todo verificado sobre esta máquina.

#### 5.1 Aceptar el UAC durante la instalación

Se instala a nivel de máquina y pide elevación. Si el prompt aparece y no se
acepta, winget falla al final, después de haber bajado 1.4 GB.

#### 5.2 Abrir Android Studio una vez

Instalar Android Studio **no alcanza**: `flutter doctor` sigue diciendo
*Unable to locate Android SDK* hasta que lo abrís, porque el SDK se descarga
recién en el asistente del primer arranque.

#### 5.3 Instalar `cmdline-tools` — **revisión 19.0, no la última**

El asistente de Android Studio instala el SDK pero **no instala
`cmdline-tools`**, que es el componente que Flutter necesita para hablar con
el SDK. El diagnóstico pasa de `[X]` a `[!]` —o sea avanza— pero sigue trabado
en *cmdline-tools component is missing*.

Y acá está la trampa: **no sirve la última revisión.** `cmdline-tools` viene en
dos generaciones incompatibles para este uso:

| Revisión | Qué trae | Con Flutter 3.47.2 |
|---|---|---|
| **23.0** (la última) | Reemplaza `sdkmanager` por el CLI `android`. El `sdkmanager.bat` que queda es un stub que avisa que está obsoleto y **rechaza `--licenses`** | ❌ Flutter no puede leer el estado → *license status unknown* |
| **19.0** | `sdkmanager` real y funcional | ✔ |

Con la 23.0, `flutter doctor --android-licenses` responde *"Warning: The
--licenses option is no longer needed"*. Ese mensaje es engañoso: **no
significa que las licencias estén aceptadas**, significa que esa herramienta ya
no las maneja así — y Flutter todavía las necesita aceptadas por la vía vieja.

Instalar la 19.0 (137 MB):

```powershell
# descargar y descomprimir
curl.exe -L -o cmdline-tools.zip `
  https://dl.google.com/android/repository/commandlinetools-win-13114758_latest.zip
Expand-Archive cmdline-tools.zip -DestinationPath .\cmdt

# mover a <SDK>\cmdline-tools\latest
$sdk = "$env:LOCALAPPDATA\Android\Sdk"
New-Item -ItemType Directory -Force "$sdk\cmdline-tools" | Out-Null
Move-Item .\cmdt\cmdline-tools "$sdk\cmdline-tools\latest"
```

Verificación: `<SDK>\cmdline-tools\latest\source.properties` debe decir
`Pkg.Revision=19.0`, y en `bin\` **no** debe haber un `android.exe`.

Después hay que definir `ANDROID_HOME` y agregar dos rutas al PATH del usuario:

```powershell
$sdk = "$env:LOCALAPPDATA\Android\Sdk"
[Environment]::SetEnvironmentVariable('ANDROID_HOME', $sdk, 'User')
$p = [Environment]::GetEnvironmentVariable('Path','User')
[Environment]::SetEnvironmentVariable('Path',
  ($p.TrimEnd(';') + ";$sdk\platform-tools;$sdk\cmdline-tools\latest\bin"), 'User')
```

#### 5.4 Aceptar las licencias del SDK

En una **terminal nueva** (el PATH cambió):

```powershell
flutter doctor --android-licenses
```

Responder `y` + Enter a cada una — son 6 o 7. Ojo con tipear cualquier otra
tecla: cuenta como rechazo y hay que volver a correr el comando para esa
licencia. El comando cierra con *All SDK package licenses accepted*.

Ignorar estas advertencias, son ruido y no impiden nada:

- `This version only understands SDK XML versions up to 3 but ... version 4`
- `WARNING: A restricted method in java.lang.System has been called` (es JNA
  con Java 17)

---

## Verificación del entorno

```powershell
python --version                    # 3.13.x  (dentro del venv de backend)
node --version                      # v24.x
flutter --version                   # Flutter 3.47.2 · Dart 3.13.2
docker --version                    # 29.x
flutter doctor                      # ver abajo qué debe salir en verde
```

```powershell
cd backend; .venv\Scripts\activate; pytest
```

Debe cerrar con **1 passed**. Esa prueba levanta la app, monta los routers del
Ciclo 1 y golpea `/health`: si pasa, el backend está bien armado.

### Cómo debe quedar `flutter doctor`

```
[√] Flutter (Channel stable, 3.47.2, on Windows 11 25H2, locale es-BO)
[√] Windows Version (Windows 11 25H2)
[√] Android toolchain (Android SDK version 36.0.0)
[√] Chrome — develop for the web
[√] Visual Studio — Visual Studio Build Tools 2026 18.9.1
[√] Connected device (3 available)
[√] Network resources

• No issues found!
```

Verificado en la máquina de Mateo el 02/09/2026. Si el Android toolchain no
sale en verde, el mensaje dice en qué punto del paso 5 quedaste:

| Mensaje de `flutter doctor` | Qué falta |
|---|---|
| `[X] Unable to locate Android SDK` | Abrir Android Studio una vez (5.2) |
| `[!] cmdline-tools component is missing` | Instalar `cmdline-tools` 19.0 (5.3) |
| `[!] Android license status unknown` | Tenés la revisión 23.0; bajá a la 19.0 (5.3) |
| `[!] Some Android licenses not accepted` | Correr `flutter doctor --android-licenses` (5.4) |

Los últimos dos se parecen pero son distintos: *unknown* significa que Flutter
**no pudo consultar** el estado (herramienta incompatible); *not accepted*
significa que sí lo consultó y faltan aceptar.

---

## Notas por si algo falla

**`flutter` no se reconoce como comando.** El PATH del usuario solo lo toman
las terminales abiertas *después* de modificarlo. Cerrá y abrí la terminal.

**El backend no conecta a la base.** Revisá que `docker compose up -d` esté
corriendo y que `DATABASE_URL` en `backend/.env` apunte a `localhost:5432`. Si
tenés un PostgreSQL instalado en el sistema, puede estar ocupando el 5432 y la
conexión va a la base equivocada — se nota porque las tablas "no existen".

**Angular compila pero ninguna petición funciona.** Es CORS o la URL de la API.
Revisá `frontend-web/src/environments/environment.ts` y, en producción,
`CORS_ORIGINS` en las variables del servicio `api` de Railway.

**Las versiones de las dependencias de Python están fijadas** en
`backend/requirements.txt` y verificadas contra PyPI. No las subas sin motivo:
`bcrypt` y `passlib` en particular tienen la incompatibilidad descrita arriba.
