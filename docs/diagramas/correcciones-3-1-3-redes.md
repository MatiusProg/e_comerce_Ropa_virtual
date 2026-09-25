# Correcciones al 3.1.3 · Diagrama de Redes

> **Escrito el 24/09/2026.** Revisión del diagrama contra **la infraestructura
> real del repositorio** y contra la notación UML 2.5. Es una lista para
> aplicar a mano en EA: cada punto dice qué está dibujado, qué debería decir y
> **de dónde sale el dato**.
>
> El diagrama está en `Diseño de Arquitectura/3.1.3 Diagrama de Redes.jpg`.

---

## Lo que ya está bien, y conviene no tocar

1. **Cada conector lleva protocolo y puerto.** Es lo que distingue un diagrama
   de redes de uno de despliegue, y es lo primero que se suele omitir.
2. **El puerto 5432 es correcto.** `backend/.env` apunta a
   `aws-0-us-east-1.pooler.supabase.com:5432`.
3. **No duplica el 3.1.2.** Aquél dice qué artefacto vive en qué nodo; éste,
   por dónde viaja el tráfico.

---

## A. Errores de hecho — los que hay que corregir sí o sí

### A1. El módulo de IA NO está dentro de Railway, y no habla gRPC

**Es el error más caro: una sola pregunta lo desarma.**

| Dibujado | Real |
|---|---|
| «Módulo de Servicios de IA» dentro del círculo de Railway, unido al contenedor por `gRPC / Local HTTP` | **Google Gemini**, servicio de un tercero, alcanzado por **HTTPS 443** saliendo a internet |

```python
# backend/app/integrations/recomendador/gemini.py:44
# (idéntico en asistente/, interprete/ y probador_ia/)
_URL = "https://generativelanguage.googleapis.com/v1beta/..."
```

**Qué hacer:** sacar el nodo de adentro de Railway, ponerlo del lado de los
terceros —junto a Supabase, o en una zona «Servicios externos»— y rotular el
enlace `HTTPS / TLS (443) · generativelanguage.googleapis.com`.

### A2. Falta de dónde sale la aplicación web

El navegador aparece sin que nadie le sirva el bundle. El Angular lo sirve un
contenedor **`nginx:alpine` en Railway**, que es un **segundo servicio** con su
propia URL.

**Qué hacer:** dentro de Railway, dos nodos hermanos en vez de uno:

```
«executionEnvironment» nginx:alpine      → violetboutique-web · bundle Angular
«executionEnvironment» Python 3.13 + Uvicorn → violetboutique-api
```

Y una flecha del navegador al primero, rotulada `HTTPS (443) · descarga del bundle`.

### A3. Faltan Stripe y el webhook entrante

**Todas las flechas del diagrama entran hacia la base.** El webhook de pago es
**el único tráfico entrante de un tercero hacia la API**, y CU-28 entero cuelga
de él.

Importa además porque **la ing ya preguntó por la pasarela** (pregunta 8 de la
defensa del 22/09): ese conector es la respuesta dibujada.

**Qué hacer:** agregar `Stripe` como nodo externo, con **dos** enlaces:

```
API  →  Stripe    HTTPS (443)   crear sesión de cobro     {CU-27}
API  ←  Stripe    HTTPS (443)   POST /pagos/webhook firmado  {CU-28}
```

### A4. El «Firewall de red» es un equipo que no existe

Railway y Supabase son plataformas gestionadas: **nadie del equipo administra
un firewall**. Dibujar un aparato que no se opera es una afirmación que no se
puede defender —«¿quién lo configura?» no tiene respuesta—.

**Qué hacer:** borrarlo. Si se quiere dejar la idea de filtrado, va como
propiedad del borde de Railway, no como nodo propio.

### A5. «API Gateway» no es lo que hay

Railway tiene un **proxy inverso de borde** que termina TLS y enruta por
nombre. Un API Gateway agrega servicios, autentica y limita tasa: nada de eso
ocurre ahí.

**Qué hacer:** renombrarlo **«Railway Edge — proxy inverso, termina TLS»**. Es
correcto, y además da algo que contar en la defensa.

### A6. Falta nombrar el pooler

La conexión no va a PostgreSQL directo, sino al **PgBouncer / session pooler**
de Supabase. El 3.1.2 ya lo modela; acá desaparece.

**Qué hacer:** dentro del nodo Supabase, dos nodos anidados:
`«executionEnvironment» PgBouncer · session pooler` y
`«executionEnvironment» PostgreSQL 17`.

---

## B. Notación UML

### B1. Los caminos de comunicación NO llevan punta de flecha

En UML un `CommunicationPath` **es una asociación: línea sólida, sin punta**, y
el intercambio va en cualquier dirección.

Acá son todas flechas dirigidas, y encima engañan: el enlace a la base es
petición **y** respuesta, no un sentido único.

**Qué hacer:** cambiar los conectores a línea simple. Las dos únicas flechas
que se justifican son las de Stripe (A3), porque ahí sí importa quién inicia.

> Referencia: [uml-diagrams.org — Deployment diagrams](https://www.uml-diagrams.org/deployment-diagrams.html)
> · [Sparx Systems — Deployment Diagram](https://sparxsystems.com/resources/tutorials/uml2/deployment-diagram.html)

### B2. Los íconos decorativos no son nodos UML

La nube, el ladrillo y el gateway son **imágenes**, no nodos. Un nodo es una
caja 3D con su estereotipo.

**El marco del diagrama dice `deployment`, así que ya está elegido UML.**
Mezclar íconos de topología con notación UML es lo que lo hace ver improvisado.

**Qué hacer:** todo nodo pasa a caja con `«device»` o
`«executionEnvironment»`. Los íconos, si se quieren conservar, van **dentro**
de la caja como imagen de fondo del elemento, no en lugar de él.

### B3. Estereotipos truncados

Sale `«exec...` en vez de `«executionEnvironment»`. EA los corta al ancho de la
caja.

**Qué hacer:** ensanchar los nodos hasta que el estereotipo entre entero.

### B4. El logo de Railway usado como fondo

Tapa el rótulo del contenedor —«Contenedor Docker (FastAPI)» queda ilegible
sobre el negro— y el nodo de Docker queda flotando encima de una imagen.

**Qué hacer:** Railway es un **nodo que CONTIENE** a los otros dos, dibujado
como caja. El logo, si va, chico y en una esquina.

### B5. Rótulos

| Dice | Debe decir |
|---|---|
| `CLiente Web - Angular` | `Cliente Web — Angular` (L de más) |
| `Cliente movil - Flutter` | `Cliente móvil — Flutter` (tilde) |
| `«exec... Android/ios os` | `«device» Smartphone` + `«executionEnvironment» Android / iOS` |

---

## C. Lo que le falta para ser una topología de verdad

Un diagrama de redes se define por sus **zonas**, y hoy no hay ninguna. Es la
mejora grande, y la que lo separa definitivamente del 3.1.2.

```
┌─ ZONA PÚBLICA ──────────────────────────────────────────┐
│  «device» PC/Laptop  *      «device» Smartphone  *      │
│    «execEnv» Navegador        «execEnv» Android/iOS     │
└───────────────┬─────────────────────┬───────────────────┘
                │  HTTPS / TLS 1.3 (443)
┌─ BORDE ───────┴─────────────────────┴───────────────────┐
│  «device» Railway Edge — proxy inverso, termina TLS      │
└───────────────┬─────────────────────────────────────────┘
                │  HTTP interno
┌─ APLICACIÓN ──┴─────────────────────────────────────────┐
│  «device» Railway                                        │
│    «execEnv» nginx:alpine   → bundle Angular             │
│    «execEnv» Python 3.13 + Uvicorn → violetboutique-api  │
└──────┬──────────────────────────────┬───────────────────┘
       │ PostgreSQL/SSL (5432)        │ HTTPS (443)
┌──────┴─────────────┐   ┌────────────┴────────────────────┐
│ ZONA DE DATOS      │   │ SERVICIOS EXTERNOS              │
│ «device» Supabase  │   │ «device» Stripe   ⇄ webhook     │
│   PgBouncer        │   │ «device» Google Gemini  →       │
│   PostgreSQL 17    │   │                                 │
└────────────────────┘   └─────────────────────────────────┘
```

**Y agregarle los nombres DNS de los dos servicios de Railway.** Que la URL de
la web **no se deduzca** de la de la API —lleva el sufijo `-b192`— es
exactamente el tipo de dato que un diagrama de redes existe para documentar, y
ya costó tiempo una vez.

---

## D. Si hay poco tiempo, este es el orden

| # | Corrección | Por qué primero |
|---|---|---|
| 1 | **A1** — sacar la IA de Railway | Es falso y se desarma con una pregunta |
| 2 | **A3** — agregar Stripe y el webhook | Responde dibujada la pregunta 8 de la ing |
| 3 | **A4** — quitar el firewall | No se puede defender quién lo opera |
| 4 | **B1** — flechas → líneas | Es *la* regla de notación de este diagrama |
| 5 | **A2** — el nginx que sirve la web | Completa el circuito del cliente |

Con esos cinco el diagrama pasa de discutible a defendible. Las zonas (C) son
la mejora grande, pero implican rehacer la disposición.

---

## Nota sobre EA

**EA instalado es la edición Trial** (`C:\Program Files (x86)\Sparx Systems\EA
Trial\EA.exe`, versión 1514, 32 bits). Conviene verificar cuántos días le
quedan **antes** del martes: que expire el día de la defensa dejaría los
diagramas sin poder abrirse ni exportarse.
