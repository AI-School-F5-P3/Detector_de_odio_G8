import pytest
from unittest.mock import AsyncMock, patch
from frontend.app import analyze_comment

API_URL = "http://127.0.0.1:8000/predict"  # URL de la API

@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)
@patch("frontend.app.st.error", new_callable=AsyncMock)
async def test_analyze_comment_success(mock_st_error, mock_fetch_analysis):
    # Simular un resultado exitoso de fetch_analysis
    mock_fetch_analysis.return_value = {
        "prediction": 0,
        "probability": 0.3248976199323941,
        "hate_level": "Sin mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.3248976199323941,
            "confidence": "32.49%"
        }
    }

    # Llamar a analyze_comment
    result = await analyze_comment("Este es un comentario de prueba")

    # Verificar que fetch_analysis fue llamado correctamente
    mock_fetch_analysis.assert_called_once_with(API_URL, "Este es un comentario de prueba")

    # Verificar que no se llamó a st.error
    mock_st_error.assert_not_called()

    # Verificar el resultado esperado
    assert result == {
        "prediction": 0,
        "probability": 0.3248976199323941,
        "hate_level": "Sin mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.3248976199323941,
            "confidence": "32.49%"
        }
    }

@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)
@patch("frontend.app.st.error", new_callable=AsyncMock)
async def test_analyze_comment_hate_detected(mock_st_error, mock_fetch_analysis):
    # Simular una respuesta de mensaje de odio
    mock_fetch_analysis.return_value = {
        "prediction": 1,
        "probability": 0.7042179894569823,
        "hate_level": "Mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.7042179894569823,
            "confidence": "70.42%"
        }
    }

    # Llamar a analyze_comment con el texto "fuck"
    result = await analyze_comment("fuck")

    # Verificar que fetch_analysis fue llamado correctamente
    mock_fetch_analysis.assert_called_once_with(API_URL, "fuck")

    # Verificar que no se llamó a st.error
    mock_st_error.assert_not_called()

    # Verificar el resultado esperado
    assert result == {
        "prediction": 1,
        "probability": 0.7042179894569823,
        "hate_level": "Mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.7042179894569823,
            "confidence": "70.42%"
        }
    }



@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)
@patch("frontend.app.st.error", new_callable=AsyncMock)
async def test_analyze_comment_no_result(mock_st_error, mock_fetch_analysis):
    # Simular que fetch_analysis devuelve None
    mock_fetch_analysis.return_value = None

    # Llamar a analyze_comment
    result = await analyze_comment("Este es un comentario de prueba")

    # Verificar que fetch_analysis fue llamado correctamente
    mock_fetch_analysis.assert_called_once_with(API_URL, "Este es un comentario de prueba")

    # Verificar que st.error fue llamado con el mensaje correcto
    mock_st_error.assert_called_once_with("Error: No se pudo obtener la respuesta de la API.")

    # Verificar que el resultado sea None
    assert result is None


@pytest.mark.anyio(backend="asyncio")
@patch("frontend.app.fetch_analysis", new_callable=AsyncMock)
@patch("frontend.app.st.error", new_callable=AsyncMock)
async def test_analyze_comment_exception(mock_st_error, mock_fetch_analysis):
    # Simular que fetch_analysis lanza una excepción
    mock_fetch_analysis.side_effect = Exception("Error inesperado")

    # Llamar a analyze_comment
    result = await analyze_comment("Este es un comentario de prueba")

    # Verificar que fetch_analysis fue llamado correctamente
    mock_fetch_analysis.assert_called_once_with(API_URL, "Este es un comentario de prueba")

    # Verificar que st.error fue llamado con el mensaje correcto
    mock_st_error.assert_called_once_with("Error analizando comentario: Error inesperado")

    # Verificar que el resultado sea None
    assert result is None
