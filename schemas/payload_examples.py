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

EQUILIBRIO_PAYLOAD_EXAMPLE = {
    "source": "posturografia-vr",
    "schema_version": "1.0",
    "report_type": "EQUILIBRIO",
    "records": [
        {
            "id": "equilibrio-20260610141907-20260610T141907",
            "title": "Equilibrio - Gaga - 10/06/2026 14:19",
            "sender": "Posturografia VR",
            "recipient": "RehabEasy",
            "created_at": "2026-06-10T14:19:07-03:00",
            "summary": (
                "SPL 273,1 mm; area 400,3 mm2; velocidade 23,55 mm/s; "
                "Romberg area 2,39; 2 parametros acima do esperado; "
                "predominio ML (AP/ML 0,67)."
            ),
            "content": (
                "Avaliacao posturografica por trajetoria de headset VR com olhos "
                "abertos e fechados. Dois parametros acima do esperado, com "
                "quociente de Romberg pela area elevado (2,39), sugerindo maior "
                "dependencia visual para o controle postural e predominio de "
                "oscilacao medio-lateral."
            ),
            "tags": ["posturografia", "equilibrio", "vr", "romberg", "meta-quest"],
            "patient": {
                "name": "Gaga",
                "age_years": 45,
                "sex": "Masculino",
                "external_id": "20260610141907",
            },
            "assessment": {
                "performed_at": "2026-06-10T14:19:07-03:00",
                "exam_id": "20260610141907",
                "evaluator": None,
                "protocol": {
                    "description": "Olhos abertos e olhos fechados, base normal, ~30 s",
                    "eyes_conditions": ["open", "closed"],
                    "stance": "normal",
                    "target_duration_seconds": 30,
                    "actual_duration_seconds": 25,
                },
                "device": {
                    "type": "vr_headset",
                    "model": "Meta Quest 3",
                },
                "posturographic_indices": [
                    {
                        "code": "spl",
                        "label": "Comprimento de trajetoria (SPL)",
                        "value": 273.1,
                        "unit": "mm",
                        "reference": {"mean": 250, "sd": 116},
                        "classification": "within_expected",
                    },
                    {
                        "code": "confidence_ellipse_95_area",
                        "label": "Area da elipse de confianca 95%",
                        "value": 400.3,
                        "unit": "mm2",
                        "reference": {"mean": 125, "sd": 82},
                        "classification": "above_expected",
                    },
                    {
                        "code": "mean_oscillation_velocity",
                        "label": "Velocidade media de oscilacao",
                        "value": 23.55,
                        "unit": "mm/s",
                        "reference": {"mean": 9.2, "sd": 1.6},
                        "classification": "above_expected",
                    },
                ],
                "romberg_quotients": [
                    {
                        "code": "area",
                        "label": "Quociente de Romberg — area (OF/OA)",
                        "value": 2.39,
                        "upper_limit": 2.0,
                        "classification": "above_expected",
                    },
                    {
                        "code": "trajectory",
                        "label": "Quociente de Romberg — trajetoria (OF/OA)",
                        "value": 0.9,
                        "upper_limit": 2.0,
                        "classification": "within_expected",
                    },
                    {
                        "code": "velocity",
                        "label": "Quociente de Romberg — velocidade (OF/OA)",
                        "value": 0.47,
                        "upper_limit": 2.0,
                        "classification": "within_expected",
                    },
                ],
                "derived_metrics": {
                    "ap_ml_ratio": 0.67,
                    "parameters_above_expected_count": 2,
                    "parameters_borderline_count": 0,
                    "spl_mm": 273.1,
                    "confidence_ellipse_95_area_mm2": 400.3,
                    "mean_oscillation_velocity_mm_s": 23.55,
                    "romberg_area_quotient": 2.39,
                },
                "automated_flags": {
                    "increased_postural_sway": True,
                    "visual_dependency": {
                        "status": "ALERTA",
                        "romberg_area_quotient": 2.39,
                        "threshold": 2.0,
                    },
                    "lateral_predominance": True,
                    "acquisition_warnings": [
                        "Duracao abaixo do recomendado (25 s)."
                    ],
                },
                "interpretation": (
                    "2 parametro(s) acima do esperado; Romberg area 2,39; "
                    "predominio medio-lateral (AP/ML 0,67)."
                ),
                "methodology_notes": [
                    "A aquisicao foi feita a partir da trajetoria da cabeca (headset VR).",
                    "Priorizar indices relativos (Romberg, razao AP/ML).",
                ],
            },
        }
    ],
}
