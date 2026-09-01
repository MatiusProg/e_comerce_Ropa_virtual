"""Carga de datos de prueba (supuesto S3 del alcance).

Genera un escenario representativo para desarrollo y para la defensa:
  3 ciudades - 5 sucursales - 4 proveedores - ~60 productos con sus
  variantes, imagenes y stock distribuido entre sucursales, mas un
  usuario por cada rol con credenciales conocidas.

Uso:  python -m app.db.seed
"""


def main() -> None:
    # TODO: implementar la carga en el ciclo 1 (usuarios, ciudades,
    # sucursales) y ampliarla en el ciclo 2 (catalogo e inventario).
    raise NotImplementedError("Seed pendiente - ciclo 1")


if __name__ == "__main__":
    main()
