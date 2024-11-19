import pytest  # Importa pytest para escribir y ejecutar pruebas.
from unittest.mock import Mock, AsyncMock, patch  # Importa herramientas para simular funciones y objetos en pruebas.
from frontend.app import analyze_comment  # Importa la función que será probada.

API_URL = "http://127.0.0.1:8000/predict"  # Define la URL de la API que se utilizará para los tests.

@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)  # Simula la función fetch_analysis como un AsyncMock.
@patch("frontend.app.st.error", new_callable=Mock)  # Simula la función st.error como un Mock.
async def test_analyze_comment_success(mock_st_error, mock_fetch_analysis):
    """
    Verifica el caso exitoso de analyze_comment.

    En esta prueba, se simula un caso donde no se detecta mensaje de odio en el comentario.
    La función `fetch_analysis` devuelve un resultado exitoso con baja probabilidad de odio.

    Verificaciones:
    - Se asegura que `fetch_analysis` es llamado con los argumentos correctos.
    - Valida que `st.error` no sea invocado.
    - Comprueba que el resultado devuelto coincide exactamente con lo esperado.
    """
    # Simular un resultado exitoso de fetch_analysis.
    mock_fetch_analysis.return_value = {
        "prediction": 0,
        "probability": 0.3248976199323941,
        "hate_level": "Sin mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.3248976199323941,
            "confidence": "32.49%",
            "model_used": "traditional"
        }
    }

    # Llamar a analyze_comment con un comentario de prueba y el modelo "traditional".
    result = await analyze_comment("Este es un comentario de prueba", "traditional")

    # Verificar que fetch_analysis fue llamado con los parámetros correctos.
    mock_fetch_analysis.assert_called_once_with(API_URL, "Este es un comentario de prueba", "traditional")

    # Verificar que no se llamó a st.error.
    mock_st_error.assert_not_called()

    # Verificar que el resultado sea el esperado.
    assert result == {
        "prediction": 0,
        "probability": 0.3248976199323941,
        "hate_level": "Sin mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.3248976199323941,
            "confidence": "32.49%",
            "model_used": "traditional"
        }
    }


@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)  # Simula la función fetch_analysis como un AsyncMock.
@patch("frontend.app.st.error", new_callable=Mock)  # Simula la función st.error como un Mock.
async def test_analyze_comment_hate_detected(mock_st_error, mock_fetch_analysis):
    """
    Verifica el caso donde se detecta un mensaje de odio.

    En esta prueba, se simula un caso donde el comentario contiene un mensaje de odio.
    La función `fetch_analysis` devuelve una probabilidad alta de odio y un nivel detectado de odio.

    Verificaciones:
    - Se asegura que `fetch_analysis` es llamado con los argumentos correctos.
    - Valida que `st.error` no sea invocado.
    - Comprueba que el resultado devuelto coincide exactamente con lo esperado.
    """
    # Simular una respuesta que indica detección de mensaje de odio.
    mock_fetch_analysis.return_value = {
        "prediction": 1,
        "probability": 0.7042179894569823,
        "hate_level": "Mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.7042179894569823,
            "confidence": "70.42%",
            "model_used": "traditional"
        }
    }

    # Llamar a analyze_comment con el comentario ofensivo "fuck" y el modelo "traditional".
    result = await analyze_comment("fuck", "traditional")

    # Verificar que fetch_analysis fue llamado con los parámetros correctos.
    mock_fetch_analysis.assert_called_once_with(API_URL, "fuck", "traditional")

    # Verificar que no se llamó a st.error.
    mock_st_error.assert_not_called()

    # Verificar que el resultado sea el esperado.
    assert result == {
        "prediction": 1,
        "probability": 0.7042179894569823,
        "hate_level": "Mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.7042179894569823,
            "confidence": "70.42%",
            "model_used": "traditional"
        }
    }


@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)  # Simula la función fetch_analysis como un AsyncMock.
@patch("frontend.app.st.error", new_callable=Mock)  # Simula la función st.error como un Mock.
async def test_analyze_comment_no_result(mock_st_error, mock_fetch_analysis):
    """
    Verifica el comportamiento cuando la API no devuelve un resultado.

    En esta prueba, se simula un caso donde `fetch_analysis` devuelve `None`.

    Verificaciones:
    - Se asegura que `fetch_analysis` es llamado con los argumentos correctos.
    - Valida que `st.error` sea invocado con el mensaje adecuado.
    - Comprueba que el resultado devuelto es `None`.
    """
    # Simular que fetch_analysis no devuelve ningún resultado (None).
    mock_fetch_analysis.return_value = None

    # Llamar a analyze_comment con un comentario de prueba y el modelo "traditional".
    result = await analyze_comment("Este es un comentario de prueba", "traditional")

    # Verificar que fetch_analysis fue llamado con los parámetros correctos.
    mock_fetch_analysis.assert_called_once_with(API_URL, "Este es un comentario de prueba", "traditional")

    # Verificar que st.error fue llamado con el mensaje de error adecuado.
    mock_st_error.assert_called_once_with("Error: No se pudo obtener la respuesta de la API.")

    # Verificar que el resultado devuelto sea None.
    assert result is None


@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)  # Simula la función fetch_analysis como un AsyncMock.
@patch("frontend.app.st.error", new_callable=Mock)  # Simula la función st.error como un Mock.
async def test_analyze_comment_exception(mock_st_error, mock_fetch_analysis):
    """
    Verifica el manejo de excepciones inesperadas.

    En esta prueba, se simula que `fetch_analysis` lanza una excepción durante su ejecución.

    Verificaciones:
    - Se asegura que `fetch_analysis` es llamado con los argumentos correctos.
    - Valida que `st.error` sea invocado con el mensaje de excepción.
    - Comprueba que el resultado devuelto es `None`.
    """
    # Simular que fetch_analysis lanza una excepción.
    mock_fetch_analysis.side_effect = Exception("Error inesperado")

    # Llamar a analyze_comment con un comentario de prueba y el modelo "traditional".
    result = await analyze_comment("Este es un comentario de prueba", "traditional")

    # Verificar que fetch_analysis fue llamado con los parámetros correctos.
    mock_fetch_analysis.assert_called_once_with(API_URL, "Este es un comentario de prueba", "traditional")

    # Verificar que st.error fue llamado con el mensaje de error adecuado.
    mock_st_error.assert_called_once_with("Error analizando comentario: Error inesperado")

    # Verificar que el resultado devuelto sea None.
    assert result is None
