"""
P3 - Catalogo / CU-08 Gestionar categorias, tallas y colores

Ciclo de desarrollo: 1

Subpaquete propio, con sus cuatro capas dentro, por lo decidido en la seccion
6.11.5 de docs/06-decisiones-tecnicas.md: el CU-08 y el CU-09 se desarrollan en
paralelo sobre el mismo paquete P3, y si los dos escribieran en los mismos
router.py, service.py, repository.py y schemas.py cada merge terminaria en
conflicto.

Los modelos NO se duplican: siguen en catalogo/models.py, que es de todo el
paquete. Lo unico compartido queda siendo la linea que registra el router en
app/main.py.
"""
