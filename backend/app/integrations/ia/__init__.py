"""Adaptador del servicio de inteligencia artificial (API de Claude).

Ciclo 3 - paquete P10.

Responsabilidades:
  - ordenar las candidatas del recomendador (CU-33)
  - sostener la conversacion del asistente mediante uso de herramientas (CU-34)
  - redactar el reporte solicitado por voz (CU-35)

Reglas (D6):
  - la IA nunca es fuente de verdad: los datos salen siempre de la BD
  - el modelo NO genera SQL; solo invoca funciones declaradas y validadas
  - el cliente_id se inyecta desde el token, jamas desde la conversacion
  - si el servicio falla, se degrada a recomendacion por reglas
"""
