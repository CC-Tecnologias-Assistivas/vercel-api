import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pdf_extractors.cvtug import build_payload_from_tabular_text
from services.pdf_extractors.equilibrio import build_payload_from_tabular_text as build_equilibrio


CVTUG_TEXT = """
RELATORIO TESTE DE TUG
Paciente: Garcia Sexo: masculino
Idade: 55 Data: 01/09/2026 13:51 ID: iwehgoijgj4
Protocolo: TUG com tres condicoes Resultados (TUG — segundos)
Normal 9,8 Levantar 1,6s | Marcha 7,0s | Sentar 1,3s esperado ~9,9 lim.sup ~14,5
Motora 13,5 Levantar 1,8s | Marcha 9,7s | Sentar 2,1s 38%
Cognitiva 13,8 Levantar 1,8s | Marcha 9,9s | Sentar 2,2s 40%
TUG acima do limite superior não
Triagem de quedas (>=12s Lusardi2017 / >=13.5s Shumway-Cook2000) OK
Dual-task cost (pior condição) ALERTA >=20%
Velocidade média (marcha — Normal) 0,58 m/s
Nota velocidade velocidade reduzida. Relatório gerado
"""


EQUILIBRIO_TEXT = """
RELATÓRIO DE AVALIAÇÃO DO EQUILÍBRIO
Paciente: Marina Morena Sexo: Feminino
Idade: 32 Data: 01/09/2026 10:16 ID exame: Marina00002
Protocolo: 3 tentativas, olhos abertos e fechados, até 30 s cada
Médias dos índices posturográficos
Comprimento de trajetória (SPL) 171,4 213,5 mm — — Dentro do esperado
Área da elipse de confiança 95% 424,4 268,4 mm2 — — Acima do esperado
Velocidade média de oscilação 5,71 7,11 mm/s — — Acima do esperado
Deslocamento radial médio (MDIST) 11,87 7,29 — — Dentro do esperado
RMS radial (RDIST) 13,28 8,99 — — Dentro do esperado
RMS ântero-posterior (AP) 12,9 8,83 mm — — Dentro do esperado
RMS médio-lateral (ML) 3,11 1,68 mm — — Dentro do esperado
Amplitude AP (pico-a-pico) 43,2 37,9 mm — — Dentro do esperado
Amplitude ML (pico-a-pico) 11,9 9,4 mm — — Dentro do esperado
Razão direcional AP/ML 4,26 5,33 — — Dentro do esperado
Frequência média 0,078 0,155 Hz — — Dentro do esperado
Oscilação vertical da cabeça (RMS) 0,81 1,41 mm — — Dentro do esperado
Oscilação angular — inclinação (pitch) 0,00 0,00 ° — — Dentro do esperado
Oscilação angular — lateral (roll) 0,00 0,00 ° — — Dentro do esperado
Oscilação angular — rotação (yaw) 0,00 0,00 ° — — Dentro do esperado
Área 0,63 < 2,0 Dentro do esperado
Trajetória 1,25 < 2,0 Dentro do esperado
Velocidade 1,25 < 2,0 Dentro do esperado
"""


class TabularExtractorTest(unittest.TestCase):
    def test_cvtug_table_layout(self):
        record = build_payload_from_tabular_text(CVTUG_TEXT)["records"][0]
        assessment = record["assessment"]
        self.assertEqual(record["patient"]["external_id"], "iwehgoijgj4")
        self.assertEqual([condition["total_seconds"] for condition in assessment["conditions"]], [9.8, 13.5, 13.8])
        self.assertEqual(assessment["derived_metrics"]["worst_dual_task_cost_percent"], 40.0)
        self.assertEqual(assessment["automated_flags"]["fall_screening"]["status"], "OK")

    def test_equilibrio_table_layout_preserves_both_eye_conditions(self):
        record = build_equilibrio(EQUILIBRIO_TEXT)["records"][0]
        assessment = record["assessment"]
        self.assertEqual(len(assessment["posturographic_indices"]), 15)
        spl = assessment["posturographic_indices"][0]
        self.assertEqual(spl["value"], 171.4)
        self.assertEqual(spl["eyes_open_value"], 171.4)
        self.assertEqual(spl["eyes_closed_value"], 213.5)
        self.assertEqual(assessment["romberg_quotients"][0]["value"], 0.63)
        self.assertIn("predominio AP", record["summary"])


if __name__ == "__main__":
    unittest.main()
