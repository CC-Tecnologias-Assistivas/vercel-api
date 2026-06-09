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
            "id": "spook-cvtug-001",
            "title": "Spook CvTUG Teste 001",
            "sender": "CvTUG",
            "recipient": "RehabEasy",
            "created_at": "2026-06-09T14:30:00Z",
            "summary": (
                "SPOOK teste CvTUG: normal 10.4s; motora 13.5s; "
                "cognitiva 13.7s; pior DTC 32%; velocidade 0.94 m/s."
            ),
            "content": (
                "SPOOK payload de teste do CvTUG sem documento de origem e "
                "sem citacoes estruturadas."
            ),
            "tags": ["spook", "cvtug", "teste-api"],
            "patient": {
                "name": "Jose GArcia",
                "age_years": 54,
                "sex": "Masculino",
                "external_id": "20251121100833",
            },
            "assessment": {
                "performed_at": "2026-06-09T14:30:00Z",
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
                            {"seconds": 12},
                            {"seconds": 13.5},
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
                    "SPOOK teste: interpretar os indicadores no contexto clinico.",
                    "SPOOK teste: payload sanitizado para validacao do RehabEasy.",
                ],
            },
        }
    ],
}
