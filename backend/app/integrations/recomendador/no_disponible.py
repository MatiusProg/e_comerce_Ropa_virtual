"""El proveedor por defecto: no ordena y lo dice.

A DIFERENCIA DEL PROBADOR, ESTO NO APAGA NADA
----------------------------------------------
En CU-21 el probado por IA es un boton, y sin proveedor la pantalla lo
esconde. Aca no: **CU-33 funciona igual sin modelo**, mostrando las candidatas
ordenadas por popularidad. Lo unico que se pierde es la personalizacion y la
frase que explica el porque.

Por eso este proveedor levanta, y el servicio lo atrapa y degrada. Es el punto
3 de la decision tecnica.
"""

from app.integrations.recomendador.base import (
    Candidata,
    PerfilDelCliente,
    RecomendadorNoConfigurado,
    Sugerencia,
)


class RecomendadorNoDisponible:
    """No hay modelo. El servicio ordena por popularidad."""

    nombre = "no_disponible"
    disponible = False

    def ordenar(
        self,
        perfil: PerfilDelCliente,
        candidatas: list[Candidata],
        cuantas: int,
    ) -> list[Sugerencia]:
        raise RecomendadorNoConfigurado(
            "No hay proveedor de recomendación configurado. Se habilita con "
            "IA_PROVEEDOR y IA_API_KEY."
        )
