"""Adaptadores de servicios externos.

Regla: ninguna capa de negocio conoce los detalles de un servicio
externo. Toda llamada a la pasarela de pago o al servicio de IA pasa
por un adaptador de este paquete, de modo que sustituir el proveedor
no propague cambios al resto del sistema.
"""
