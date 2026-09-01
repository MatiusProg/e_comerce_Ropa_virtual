"""Adaptador de la pasarela de pago (Stripe, modo sandbox).

Ciclo 3 - paquete P8.

Responsabilidades:
  - crear la sesion de pago y devolver la URL de redireccion
  - verificar la firma del webhook antes de creer en su contenido
  - traducir el evento de la pasarela a un estado de Venta

Regla (D5): el estado del pago lo determina UNICAMENTE el webhook
verificado, nunca la redireccion del navegador del cliente.
"""
