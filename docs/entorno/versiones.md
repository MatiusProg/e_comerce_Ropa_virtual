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

Dos pasos que son gráficos y hay que hacer a mano:

1. **Aceptar el UAC** si aparece durante la instalación. Se instala a nivel de
   máquina y pide elevación; sin eso winget falla al final, después de haber
   bajado todo.
2. **Abrir Android Studio una vez.** Instalar Android Studio **no alcanza**:
   `flutter doctor` sigue diciendo *Unable to locate Android SDK* hasta que lo
   abrís, porque el SDK se descarga recién en el asistente del primer arranque.
   Está verificado — con Android Studio ya instalado, el diagnóstico no cambia
   hasta hacer este paso.

Luego, aceptar las licencias del SDK (responder `y` a cada una):

```powershell
flutter doctor --android-licenses
```

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

### Estado actual de `flutter doctor`

```
[√] Flutter (Channel stable, 3.47.2, on Windows 11 25H2, locale es-BO)
[√] Windows Version (Windows 11 25H2)
[X] Android toolchain — Unable to locate Android SDK    ← se resuelve con el paso 5
[√] Chrome — develop for the web
[√] Visual Studio — Visual Studio Build Tools 2026 18.9.1
[√] Connected device (3 available)
[√] Network resources
```

La única cruz es la cadena de Android, y desaparece al terminar el paso 5. Las
demás no son necesarias para este proyecto (no compilamos para Windows ni para
web desde Flutter), pero no molestan.

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
