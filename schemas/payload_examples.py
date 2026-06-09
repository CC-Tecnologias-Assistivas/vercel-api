GENERIC_PAYLOAD_EXAMPLE = {
    "source": "sistema-origem",
    "schema_version": "1.0",
    "entity": "clinical_report",
    "records": [
        {
            "id": "relatorio-001",
            "title": "Relatorio de atendimento 001",
            "sender": "Sistema Origem",
            "recipient": "RehabEasy",
            "created_at": "2026-06-09T12:00:00Z",
            "summary": "Resumo curto do registro enviado para importacao.",
            "content": "Conteudo completo do registro em texto plano.",
            "tags": ["triagem", "api", "rehabeasy"],
        }
    ],
}

CVTUG_PAYLOAD_EXAMPLE = {
    "source": "cvtug",
    "schema_version": "1.1",
    "report_type": "TUG",
    "records": [
        {
            "id": "cvtug-20251121100833-20251121T100800",
            "title": "CvTUG - Jose Garcia - 21/11/2025 10:08",
            "sender": "CvTUG",
            "recipient": "RehabEasy",
            "created_at": "2025-11-21T10:08:00-03:00",
            "summary": (
                "TUG normal 10.4s; motora 13.5s; cognitiva 13.7s; "
                "pior DTC 32%; triagem de quedas OK; velocidade 0.94 m/s."
            ),
            "content": (
                "Teste TUG com tres condicoes avaliadas. Resultado normal dentro "
                "do limite superior de referencia, com aumento importante de custo "
                "em dupla tarefa, especialmente na condicao cognitiva, e "
                "velocidade de marcha discretamente baixa."
            ),
            "tags": ["cvtug", "tug", "dual-task", "fall-risk-screening"],
            "source_document": {
                "file_name": "CvTUG_Report_20251104_175720-1.pdf",
                "pages": 1,
                "document_type": "pdf",
                "report_timestamp_text": "21/11/2025 10:08",
                "file_name_timestamp_text": "20251104_175720",
                "notes": [
                    "O timestamp exibido no relatorio e diferente do timestamp presente no nome do arquivo PDF."
                ],
            },
            "raw_report_text": (
                "RELATORIO TESTE DE TUG Paciente: Jose Garcia Idade: 54 | Sexo: Masculino "
                "ID: 20251121100833 Data: 21/11/2025 10:08 Resultados (TUG - segundos): "
                "Normal 10.4 [esperado~9.9; lim.sup~14.5 | Kear2017]; Motora 13.5 DTC 30%; "
                "Cognitiva 13.7 DTC 32%. Macro-fases: Normal levantar 2.1, marcha 6.1, "
                "sentar 2.2; Motora levantar 4.2, marcha 6.6, sentar 2.8; Cognitiva levantar "
                "2.9, marcha 7.5, sentar 3.3. Sinalizadores automaticos: TUG acima do limite "
                "superior: nao; Triagem de quedas: OK; Dual-task cost: ALERTA >=20%; "
                "Velocidade media normal: 0.94 m/s; Nota velocidade: Velocidade discretamente "
                "baixa (0.8-1.0 m/s)."
            ),
            "patient": {
                "name": "Jose Garcia",
                "age_years": 54,
                "sex": "Masculino",
                "external_id": "20251121100833",
            },
            "assessment": {
                "performed_at": "2025-11-21T10:08:00-03:00",
                "measure_unit": "seconds",
                "conditions": [
                    {
                        "code": "normal",
                        "label": "Normal",
                        "total_seconds": 10.4,
                        "dual_task_cost_percent": None,
                        "reference": {
                            "expected_seconds": 9.9,
                            "upper_limit_seconds": 14.5,
                            "source": "Kear2017",
                        },
                        "phases": {
                            "stand_seconds": 2.1,
                            "walk_seconds": 6.1,
                            "sit_seconds": 2.2,
                        },
                    },
                    {
                        "code": "motor",
                        "label": "Motora",
                        "total_seconds": 13.5,
                        "dual_task_cost_percent": 30,
                        "reference": None,
                        "phases": {
                            "stand_seconds": 4.2,
                            "walk_seconds": 6.6,
                            "sit_seconds": 2.8,
                        },
                    },
                    {
                        "code": "cognitive",
                        "label": "Cognitiva",
                        "total_seconds": 13.7,
                        "dual_task_cost_percent": 32,
                        "reference": None,
                        "phases": {
                            "stand_seconds": 2.9,
                            "walk_seconds": 7.5,
                            "sit_seconds": 3.3,
                        },
                    },
                ],
                "derived_metrics": {
                    "worst_dual_task_cost_percent": 32,
                    "normal_walk_speed_mps": 0.94,
                },
                "automated_flags": {
                    "tug_above_upper_limit": False,
                    "fall_screening": {
                        "status": "OK",
                        "thresholds": [
                            {"seconds": 12, "source": "Lusardi2017"},
                            {"seconds": 13.5, "source": "Shumway-Cook2000"},
                        ],
                    },
                    "dual_task_cost": {
                        "status": "ALERTA",
                        "alert_threshold_percent": 20,
                        "worst_condition_code": "cognitive",
                        "worst_percent": 32,
                    },
                    "gait_speed": {
                        "normal_condition_mps": 0.94,
                        "note": "Velocidade discretamente baixa (0.8-1.0 m/s).",
                    },
                },
                "methodology_notes": [
                    "DTC (dual-task cost) 'Atencao' (>=10%) e 'Alerta' (>=20%) e heuristico; interpretar no contexto clinico.",
                    "Normas: <60a Kear 2017 (media/DP); >=60a Tromso 2021 (mediana e ~P95 por sexo; interpolacao linear).",
                ],
            },
        }
    ],
}
