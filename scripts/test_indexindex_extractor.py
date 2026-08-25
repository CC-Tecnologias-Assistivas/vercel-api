import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pdf_extractors.indexindex import build_payload_from_text


SAMPLE_TEXT = """
RELATORIO TESTE INDEX-INDEX
Coordenacao motora fina - aproximacao das pontas dos dedos indicadores (VR)
Paciente: teste Sexo: Masculino
Idade: 95 Data: 29/07/2026 19:19
Avaliador: — ID exame: R97o807t870
Criterio de encerramento: Toque efetivo entre as pontas dos dedos
Distancia entre as pontas ao final: 3,2 mm
Duracao do movimento avaliado: 15,32 s
Comprimento da reta-guia: 426,6 mm
Oscilacao - mao esquerda (DP): 1,9 mm
Oscilacao - mao direita (DP): 29,9 mm
Oscilacao - geral (DP): 28,8 mm
Limiar de toque (15,0 mm)
Interpretacao
Toque dentro do limiar; assimetria com maior oscilacao na mao direita.
Observacao metodologica: a reta-guia permanece fixa no espaco durante o teste.
Referencias
"""


class IndexIndexExtractorTest(unittest.TestCase):
    def test_builds_payload_with_clinical_metrics(self):
        payload = build_payload_from_text(SAMPLE_TEXT)
        record = payload["records"][0]
        assessment = record["assessment"]

        self.assertEqual(payload["report_type"], "INDEX_INDEX")
        self.assertEqual(record["id"], "indexindex-R97o807t870-20260729T191900")
        self.assertEqual(record["patient"]["external_id"], "R97o807t870")
        self.assertEqual(assessment["metrics"]["final_fingertip_distance_mm"], 3.2)
        self.assertEqual(assessment["metrics"]["movement_duration_seconds"], 15.32)
        self.assertEqual(assessment["derived_metrics"]["asymmetry_ratio"], 15.74)
        self.assertEqual(assessment["derived_metrics"]["dominant_oscillation_side"], "right")
        self.assertTrue(assessment["automated_flags"]["touch_within_threshold"])
        self.assertEqual(assessment["automated_flags"]["hand_asymmetry"]["status"], "ALERTA")


if __name__ == "__main__":
    unittest.main()
