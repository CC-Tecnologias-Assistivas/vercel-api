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
    "schema_version": "1.0",
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
                "pior DTC 32%; alerta para dual-task cost."
            ),
            "content": (
                "RELATORIO TESTE DE TUG\n"
                "Paciente: Jose Garcia\n"
                "Idade: 54 | Sexo: Masculino\n"
                "ID: 20251121100833\n"
                "Data: 21/11/2025 10:08"
            ),
            "tags": ["cvtug", "tug", "dual-task", "fall-risk-screening"],
            "patient": {
                "name": "Jose Garcia",
                "age_years": 54,
                "sex": "Masculino",
                "external_id": "20251121100833",
            },
            "assessment": {
                "performed_at": "2025-11-21T10:08:00-03:00",
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
                    }
                ],
                "flags": {
                    "tug_above_upper_limit": False,
                    "worst_dual_task_cost_percent": 32,
                    "dual_task_cost_status": "ALERTA >=20%",
                },
            },
        }
    ],
}
