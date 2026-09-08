/// Pantalla de arranque.
///
/// Se muestra mientras se comprueba el token guardado. Es breve, pero sin ella
/// la app mostraria el login por un instante antes de saltar al inicio, que es
/// justamente lo que uno no espera de una sesion recordada.
library;

import 'package:flutter/material.dart';

import '../../core/tema.dart';

class PantallaCarga extends StatelessWidget {
  const PantallaCarga({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: degradadoVB),
        child: const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Violet Boutique',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 30,
                  fontWeight: FontWeight.w300,
                  letterSpacing: 3,
                ),
              ),
              SizedBox(height: 32),
              SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(
                  color: Colors.white,
                  strokeWidth: 2.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
