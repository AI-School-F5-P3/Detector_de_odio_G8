# Pruebas del proyecto

Este documento describe las pruebas implementadas para el proyecto y lo que validan.

## Módulo `test_app.py`

### `test_analyze_comment_success`
- **Propósito:** Verifica que `analyze_comment` funciona correctamente cuando el análisis no detecta odio en el comentario.
- **Simulación:** La función `fetch_analysis` devuelve un resultado con probabilidad baja.
- **Verifica:**
  - La llamada correcta a `fetch_analysis`.
  - Que `st.error` no se invoque.
  - Que la salida coincide con el resultado esperado.

### `test_analyze_comment_hate_detected`
- **Propósito:** Verifica que `analyze_comment` detecta correctamente los mensajes de odio.
- **Simulación:** La función `fetch_analysis` devuelve una probabilidad alta y nivel de odio.
- **Verifica:**
  - La llamada correcta a `fetch_analysis`.
  - Que `st.error` no se invoque.
  - Que la salida coincide con el resultado esperado.

### `test_analyze_comment_no_result`
- **Propósito:** Verifica que `analyze_comment` maneja correctamente un caso en el que no hay respuesta de la API.
- **Simulación:** `fetch_analysis` devuelve `None`.
- **Verifica:**
  - La llamada correcta a `fetch_analysis`.
  - Que `st.error` sea invocado con el mensaje adecuado.
  - Que la función devuelva `None`.

### `test_analyze_comment_exception`
- **Propósito:** Valida que `analyze_comment` maneja correctamente excepciones lanzadas por `fetch_analysis`.
- **Simulación:** `fetch_analysis` lanza una excepción.
- **Verifica:**
  - La llamada correcta a `fetch_analysis`.
  - Que `st.error` sea invocado con el mensaje de excepción.
  - Que la función devuelva `None`.
