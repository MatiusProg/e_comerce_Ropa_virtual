"""CU-04 · Gestionar perfil del cliente.

Cubre el flujo principal, los tres flujos alternativos y las dos excepciones de
la ficha del caso de uso (docs/entregas/ciclo-1/cap-1-captura-requisitos.md).

Las categorias preferidas del paso 2 no se prueban porque no se implementan en
el Ciclo 1: ver la seccion 6.11.3 de docs/06-decisiones-tecnicas.md.
"""

from fastapi.testclient import TestClient

PERFIL = "/api/v1/perfil"
DIRECCIONES = f"{PERFIL}/direcciones"


def _id_ciudad(api: TestClient, cabeceras: dict[str, str], nombre: str = "Santa Cruz") -> int:
    respuesta = api.get("/api/v1/organizacion/ciudades", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return next(c["id"] for c in respuesta.json() if c["nombre"] == nombre)


def _agregar(
    api: TestClient,
    cabeceras: dict[str, str],
    *,
    alias: str,
    predeterminada: bool = False,
    ciudad: str = "Santa Cruz",
) -> list[dict]:
    respuesta = api.post(
        DIRECCIONES,
        headers=cabeceras,
        json={
            "ciudad_id": _id_ciudad(api, cabeceras, ciudad),
            "alias": alias,
            "direccion": f"Avenida Siempre Viva {alias}",
            "referencia": None,
            "predeterminada": predeterminada,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_puede_ver_el_perfil(api: TestClient) -> None:
    """La precondicion del caso de uso es tener sesion iniciada."""
    assert api.get(PERFIL).status_code == 401


def test_un_administrador_no_entra_al_perfil_de_cliente(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El actor de CU-04 es el Cliente. El rol se verifica en el router."""
    assert api.get(PERFIL, headers=cabeceras_admin).status_code == 403


# --- Flujo principal, pasos 1 y 2 ----------------------------------------

def test_el_perfil_muestra_los_datos_del_cliente(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    respuesta = api.get(PERFIL, headers=cabeceras_cliente)
    assert respuesta.status_code == 200

    perfil = respuesta.json()
    assert perfil["nombres"] == "Ana"
    assert perfil["apellidos"] == "Quiroga"
    assert perfil["correo"] == "ana.cliente@fashionstore.bo"
    assert perfil["documento"] == "9876543"
    assert perfil["telefono"] == "70011223"
    # Todavia no cargo ninguna talla ni ninguna direccion.
    assert perfil["talla_superior"] is None
    assert perfil["direcciones"] == []


# --- Flujo principal, pasos 3 a 5 ----------------------------------------

def test_editar_solo_toca_los_campos_enviados(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Enviar el telefono no debe borrar el documento ni el nombre."""
    respuesta = api.patch(
        PERFIL, headers=cabeceras_cliente, json={"telefono": "76543210"}
    )
    assert respuesta.status_code == 200

    perfil = respuesta.json()
    assert perfil["telefono"] == "76543210"
    assert perfil["documento"] == "9876543"
    assert perfil["nombres"] == "Ana"


def test_guardar_las_tallas_habituales(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Las tallas alimentan al recomendador del Ciclo 3 (postcondicion)."""
    respuesta = api.patch(
        PERFIL,
        headers=cabeceras_cliente,
        json={"talla_superior": "M", "talla_inferior": "32", "talla_calzado": "38"},
    )
    assert respuesta.status_code == 200

    perfil = respuesta.json()
    assert perfil["talla_superior"] == "M"
    assert perfil["talla_inferior"] == "32"
    assert perfil["talla_calzado"] == "38"


def test_enviar_un_campo_vacio_borra_el_dato(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """La ausencia y el vaciado son cosas distintas.

    No enviar `telefono` lo deja como esta; enviarlo vacio lo borra. Es la
    unica forma que tiene el cliente de quitar un dato opcional.
    """
    respuesta = api.patch(PERFIL, headers=cabeceras_cliente, json={"telefono": ""})
    assert respuesta.status_code == 200
    assert respuesta.json()["telefono"] is None


def test_los_nombres_no_pueden_quedar_vacios(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """`nombres` es NOT NULL: vaciarlo dejaria la fila invalida."""
    respuesta = api.patch(PERFIL, headers=cabeceras_cliente, json={"nombres": ""})
    assert respuesta.status_code == 422


def test_excepcion_e2_el_correo_ya_esta_en_uso(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """E2: no se puede tomar el correo de otra cuenta."""
    otro = api.post(
        "/api/v1/auth/registro",
        json={
            "nombres": "Luis",
            "apellidos": "Vaca",
            "documento": None,
            "telefono": None,
            "correo": "luis.vaca@fashionstore.bo",
            "contrasena": "Otra12345",
        },
    )
    assert otro.status_code == 201

    respuesta = api.patch(
        PERFIL, headers=cabeceras_cliente, json={"correo": "luis.vaca@fashionstore.bo"}
    )
    assert respuesta.status_code == 409


def test_el_correo_se_normaliza_a_minusculas(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Sin normalizar, 'Ana@x.com' y 'ana@x.com' serian dos cuentas distintas."""
    respuesta = api.patch(
        PERFIL, headers=cabeceras_cliente, json={"correo": "ANA.NUEVA@Fashionstore.BO"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == "ana.nueva@fashionstore.bo"


# --- Flujo alternativo 3a: agregar direccion -----------------------------

def test_la_primera_direccion_queda_como_predeterminada(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Aunque el cliente no la marque: tener direcciones y ninguna preferida
    no le sirve a nadie."""
    lista = _agregar(api, cabeceras_cliente, alias="Casa", predeterminada=False)

    assert len(lista) == 1
    assert lista[0]["alias"] == "Casa"
    assert lista[0]["predeterminada"] is True
    assert lista[0]["ciudad"] == "Santa Cruz"


def test_marcar_una_nueva_como_predeterminada_desmarca_la_anterior(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El indice parcial de la base admite una sola por cliente.

    Si el servicio no desmarcara la anterior en la misma transaccion, esta
    insercion fallaria con una violacion de unicidad.
    """
    _agregar(api, cabeceras_cliente, alias="Casa")
    lista = _agregar(api, cabeceras_cliente, alias="Trabajo", predeterminada=True)

    predeterminadas = [d for d in lista if d["predeterminada"]]
    assert len(predeterminadas) == 1
    assert predeterminadas[0]["alias"] == "Trabajo"
    # Y la predeterminada va primero en el listado.
    assert lista[0]["alias"] == "Trabajo"


def test_una_ciudad_inexistente_se_rechaza(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    respuesta = api.post(
        DIRECCIONES,
        headers=cabeceras_cliente,
        json={
            "ciudad_id": 999999,
            "alias": "Fantasma",
            "direccion": "Calle inexistente",
            "referencia": None,
            "predeterminada": False,
        },
    )
    assert respuesta.status_code == 422


def test_cambiar_la_predeterminada_entre_dos_existentes(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    _agregar(api, cabeceras_cliente, alias="Casa")
    lista = _agregar(api, cabeceras_cliente, alias="Trabajo")
    trabajo = next(d for d in lista if d["alias"] == "Trabajo")

    respuesta = api.patch(
        f"{DIRECCIONES}/{trabajo['id']}/predeterminada", headers=cabeceras_cliente
    )
    assert respuesta.status_code == 200

    predeterminadas = [d for d in respuesta.json() if d["predeterminada"]]
    assert len(predeterminadas) == 1
    assert predeterminadas[0]["alias"] == "Trabajo"


# --- Flujo alternativo 3b: eliminar direccion ----------------------------

def test_al_eliminar_la_predeterminada_el_cliente_queda_sin_ninguna(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El caso de uso no pide promover otra en su lugar."""
    _agregar(api, cabeceras_cliente, alias="Casa")
    lista = _agregar(api, cabeceras_cliente, alias="Trabajo", predeterminada=True)
    trabajo = next(d for d in lista if d["alias"] == "Trabajo")

    respuesta = api.delete(f"{DIRECCIONES}/{trabajo['id']}", headers=cabeceras_cliente)
    assert respuesta.status_code == 200

    restantes = respuesta.json()
    assert len(restantes) == 1
    assert restantes[0]["alias"] == "Casa"
    assert restantes[0]["predeterminada"] is False


def test_no_se_puede_borrar_la_direccion_de_otro_cliente(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El repositorio filtra por cliente_id ademas de por id.

    Sin ese filtro, cualquiera podria borrar la direccion de otro adivinando
    un identificador.
    """
    lista = _agregar(api, cabeceras_cliente, alias="Casa")
    ajena = lista[0]["id"]

    api.post(
        "/api/v1/auth/registro",
        json={
            "nombres": "Luis",
            "apellidos": "Vaca",
            "documento": None,
            "telefono": None,
            "correo": "luis.vaca@fashionstore.bo",
            "contrasena": "Otra12345",
        },
    )
    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "luis.vaca@fashionstore.bo", "contrasena": "Otra12345"},
    )
    intruso = {"Authorization": f"Bearer {entrada.json()['access_token']}"}

    assert api.delete(f"{DIRECCIONES}/{ajena}", headers=intruso).status_code == 404
    # Y la direccion sigue estando donde estaba.
    assert len(api.get(PERFIL, headers=cabeceras_cliente).json()["direcciones"]) == 1


# --- Flujo alternativo 3c: cambiar contrasena ----------------------------

def test_excepcion_e1_la_contrasena_actual_es_incorrecta(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """E1: el sistema rechaza el cambio y devuelve el control al paso 3c."""
    respuesta = api.put(
        f"{PERFIL}/contrasena",
        headers=cabeceras_cliente,
        json={
            "contrasena_actual": "NoEsLaMia9",
            "contrasena_nueva": "NuevaClave1",
            "contrasena_repetida": "NuevaClave1",
        },
    )
    assert respuesta.status_code == 422
    assert "actual" in respuesta.json()["detail"].lower()


def test_las_dos_contrasenas_nuevas_deben_coincidir(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El flujo pide la contrasena nueva dos veces; se valida en el servidor."""
    respuesta = api.put(
        f"{PERFIL}/contrasena",
        headers=cabeceras_cliente,
        json={
            "contrasena_actual": "Secreta123",
            "contrasena_nueva": "NuevaClave1",
            "contrasena_repetida": "OtraDistinta2",
        },
    )
    assert respuesta.status_code == 422


def test_cambiar_la_contrasena_revoca_las_sesiones_abiertas(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Si se cambio porque la cuenta estaba comprometida, dejar vivos los
    tokens anteriores no serviria de nada."""
    respuesta = api.put(
        f"{PERFIL}/contrasena",
        headers=cabeceras_cliente,
        json={
            "contrasena_actual": "Secreta123",
            "contrasena_nueva": "NuevaClave1",
            "contrasena_repetida": "NuevaClave1",
        },
    )
    assert respuesta.status_code == 204

    # El token que hizo el cambio ya no sirve.
    assert api.get(PERFIL, headers=cabeceras_cliente).status_code == 401

    # Y la contrasena nueva si permite entrar.
    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "ana.cliente@fashionstore.bo", "contrasena": "NuevaClave1"},
    )
    assert entrada.status_code == 200


# --- Selector de ciudades (CU-05 en modo lectura) ------------------------

def test_el_cliente_puede_listar_las_ciudades(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El formulario de direcciones necesita poblar su selector."""
    respuesta = api.get("/api/v1/organizacion/ciudades", headers=cabeceras_cliente)
    assert respuesta.status_code == 200

    nombres = [c["nombre"] for c in respuesta.json()]
    assert "Santa Cruz" in nombres
    assert "La Paz" in nombres


def test_el_listado_de_ciudades_exige_sesion(api: TestClient) -> None:
    assert api.get("/api/v1/organizacion/ciudades").status_code == 401
