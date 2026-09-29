# Evaluación de Círculos de Bienestar MHA

Aplicación Streamlit para comparar las mediciones de entrada y salida de los Círculos de Bienestar por persona.

## Funcionamiento

1. Carga y valida el Excel de entrada.
2. Carga y valida el Excel de salida.
3. Localiza las hojas `RESPUESTAS` y `SET UP` sin depender de mayúsculas, espacios o tildes.
4. Cruza las personas por número de cédula; el nombre se usa solamente como filtro visible.
5. Clasifica cada respuesta con las reglas del archivo: rojo = 1, amarillo = 2 y verde = 3.
6. Muestra todos los indicadores con un círculo pequeño para entrada y uno grande para salida.
7. Calcula cuatro métricas para la persona seleccionada: mejoran, empeoran, siguen igual y resultado neto.
8. Oculta los controles de carga después de validar ambos archivos y permite reemplazarlos con `Cambiar archivos`.
9. Descarga la vista individual en PDF carta horizontal.
10. Descarga un Excel con nombre, cédula y las cuatro métricas de todas las personas comparables.

El resultado neto es `indicadores que mejoran - indicadores que empeoran`.

## Validaciones

La visualización solo se habilita cuando ambos archivos cumplen las condiciones necesarias:

- existe una única hoja `RESPUESTAS` y una única hoja `SET UP`;
- están presentes la cédula, el nombre y todas las preguntas configuradas;
- hay una fila por persona y momento;
- todas las respuestas corresponden a rojo, amarillo o verde;
- los dos archivos usan los mismos indicadores y clasificaciones;
- existe al menos una persona en ambos momentos.

Las filas completamente vacías se ignoran. Las personas presentes en un solo momento se informan y no aparecen en el selector.

## Ejecución local

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

La aplicación procesa los archivos en memoria. No los guarda en disco ni los incluye en el repositorio.

## Pruebas

```powershell
python -m pip install pytest
python -m pytest
```

Las pruebas crean libros sintéticos; no utilizan información personal ni archivos de producción.
