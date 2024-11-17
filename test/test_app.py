from unittest.mock import patch, AsyncMock
import pytest
from frontend.app import fetch_analysis

@pytest.mark.anyio(backend="asyncio")  # Usar asyncio como backend para las pruebas
@patch("frontend.app.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_fetch_analysis_success(mock_post):
    # Crear un objeto de respuesta simulada
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "prediction": 0,
        "probability": 0.3248976199323941,
        "hate_level": "Sin mensaje de odio detectado",
        "details": {
            "threshold_used": 0.59,
            "raw_probability": 0.3248976199323941,
            "confidence": "32.49%"
        }
    }

    # Configurar el mock para que devuelva la respuesta simulada
    mock_post.return_value = mock_response

    # Llamar a la función bajo prueba
    result = await fetch_analysis("http://127.0.0.1:8000/predict", "Texto de prueba")

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
