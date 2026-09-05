"""
P2 - Organizacion / CU-06 Gestionar empleados

Ciclo de desarrollo: 1

Por que es un subpaquete y no mas codigo en organizacion/router.py
------------------------------------------------------------------
El CU-06 y el CU-07 se desarrollan en paralelo y viven los dos en P2. Si ambos
agregaran su bloque a los mismos router.py, service.py, repository.py y
schemas.py, cada merge terminaria en conflicto -- y agregar al final del archivo
no ayuda: es justamente donde los dos escribirian.

Separandolos por caso de uso, cada uno trabaja en archivos propios y lo unico
compartido es la linea que registra el router en app/main.py. Las cuatro capas
de la seccion 6.1 se respetan igual, solo que dentro del subpaquete:

    empleados/router.py -> service.py -> repository.py -> ../models.py

Los modelos NO se duplican: siguen en organizacion/models.py, que es de todo el
paquete. Ver la seccion 6.11.5 de docs/06-decisiones-tecnicas.md.
"""
