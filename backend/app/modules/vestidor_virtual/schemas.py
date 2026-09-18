"""
P9 - Vestidor Virtual (RA)  |  capa: esquemas (Pydantic)

Ciclo de desarrollo: 3
Caso de uso: CU-21 Utilizar vestidor virtual, la parte OPCIONAL de «amoldar»

Regla: NUNCA se expone un modelo SQLAlchemy directamente.
"""
from pydantic import BaseModel


class EstadoDelProbador(BaseModel):
    """Si el probado por IA se puede ofrecer.

    Existe para que **la pantalla esconda el botón** en vez de mostrarlo y
    fallar al tocarlo. Un botón que siempre da error es peor que no tenerlo: el
    cliente lo prueba tres veces antes de creer que no funciona.

    Lo consulta la app al abrir el vestidor, una sola vez.
    """

    #: Si hay proveedor configurado y con clave.
    disponible: bool

    #: Qué mostrar cuando no lo está. Nulo si lo está.
    motivo: str | None = None

    #: Cuánto suele tardar, en segundos, para poder avisarlo antes de empezar.
    #: Es una estimación gruesa y a propósito: componer una imagen tarda lo que
    #: tarde el servicio, y prometer un número exacto sería mentir.
    demora_estimada_segundos: int = 15
