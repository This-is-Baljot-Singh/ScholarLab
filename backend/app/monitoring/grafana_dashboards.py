"""
Grafana Dashboard Configuration for ScholarLab Monitoring

Generates JSON configuration for Grafana dashboards showing:
- API latency by endpoint
- Spoof rejection rate
- False rejection rate (false positives)
- Model inference time
- Risk prediction distribution
- System health indicators
"""

import json
from typing import Dict, List, Any


def create_latency_dashboard() -> Dict[str, Any]:
    """Create dashboard for API latency monitoring."""
    return {
        "dashboard": {
            "title": "ScholarLab API Latency",
            "tags": ["production", "latency", "api"],
            "timezone": "browser",
            "refresh": "10s",
            "panels": [
                {
                    "id": 1,
                    "title": "API Request Latency (p50/p95/p99)",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.50, rate(scholarlab_api_request_duration_ms_bucket[5m]))",
                            "legendFormat": "p50",
                        },
                        {
                            "expr": "histogram_quantile(0.95, rate(scholarlab_api_request_duration_ms_bucket[5m]))",
                            "legendFormat": "p95",
                        },
                        {
                            "expr": "histogram_quantile(0.99, rate(scholarlab_api_request_duration_ms_bucket[5m]))",
                            "legendFormat": "p99",
                        },
                    ],
                    "yaxes": [
                        {
                            "label": "Latency (ms)",
                            "format": "ms",
                        }
                    ],
                },
                {
                    "id": 2,
                    "title": "Attendance Verification Latency",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(scholarlab_attendance_verification_duration_ms_bucket[5m]))",
                            "legendFormat": "p95 - {{verification_type}}",
                        }
                    ],
                    "yaxes": [
                        {
                            "label": "Latency (ms)",
                            "format": "ms",
                        }
                    ],
                },
                {
                    "id": 3,
                    "title": "Endpoint Performance",
                    "type": "table",
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "topk(10, rate(scholarlab_api_request_duration_ms_bucket[5m]))",
                            "format": "table",
                            "instant": True,
                        }
                    ],
                },
            ],
        }
    }


def create_security_dashboard() -> Dict[str, Any]:
    """Create dashboard for security metrics."""
    return {
        "dashboard": {
            "title": "ScholarLab Security Metrics",
            "tags": ["production", "security", "spoofing"],
            "timezone": "browser",
            "refresh": "30s",
            "panels": [
                {
                    "id": 1,
                    "title": "Spoof Rejection Rate",
                    "type": "gauge",
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(scholarlab_spoof_rejections_total[1h])",
                            "legendFormat": "{{spoof_type}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "max": 100,
                        }
                    },
                },
                {
                    "id": 2,
                    "title": "False Rejection Rate (FRR)",
                    "type": "gauge",
                    "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(scholarlab_false_rejections_total[1h])",
                            "legendFormat": "{{rejection_reason}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "max": 0.05,  # Target <5% FRR
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 0.02},
                                    {"color": "red", "value": 0.05},
                                ]
                            },
                        }
                    },
                },
                {
                    "id": 3,
                    "title": "Biometric Verification Results",
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "scholarlab_biometric_verifications_total",
                            "legendFormat": "{{result}}",
                        }
                    ],
                },
                {
                    "id": 4,
                    "title": "Device Clone Detections (24h)",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                    "targets": [
                        {
                            "expr": "increase(scholarlab_device_clone_detections_total[24h])",
                        }
                    ],
                },
                {
                    "id": 5,
                    "title": "Token Revocations",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "rate(scholarlab_token_revocations_total[5m])",
                            "legendFormat": "{{reason}}",
                        }
                    ],
                },
                {
                    "id": 6,
                    "title": "RBAC Denials",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "rate(scholarlab_rbac_denials_total[5m])",
                            "legendFormat": "{{role}} - {{permission}}",
                        }
                    ],
                },
            ],
        }
    }


def create_analytics_dashboard() -> Dict[str, Any]:
    """Create dashboard for ML analytics metrics."""
    return {
        "dashboard": {
            "title": "ScholarLab Analytics & ML",
            "tags": ["production", "analytics", "ml"],
            "timezone": "browser",
            "refresh": "30s",
            "panels": [
                {
                    "id": 1,
                    "title": "Model Inference Time (ms)",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(scholarlab_model_inference_duration_ms_bucket[5m]))",
                            "legendFormat": "{{model_name}} - {{inference_type}}",
                        }
                    ],
                    "yaxes": [
                        {
                            "label": "Latency (ms)",
                            "format": "ms",
                        }
                    ],
                    "alert": {
                        "name": "High Inference Latency",
                        "conditions": [
                            {
                                "evaluator": {"type": "gt", "params": [500]},
                                "query": {"query": "A"},
                            }
                        ],
                    },
                },
                {
                    "id": 2,
                    "title": "Risk Prediction Distribution",
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "scholarlab_risk_predictions_total",
                            "legendFormat": "{{risk_level}}",
                        }
                    ],
                },
                {
                    "id": 3,
                    "title": "Active Students by Risk Level",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "scholarship_risk_predictions_total{risk_level='critical'}",
                        }
                    ],
                    "colorMode": "background",
                    "graphMode": "none",
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 5},
                                    {"color": "red", "value": 10},
                                ]
                            },
                        }
                    },
                },
                {
                    "id": 4,
                    "title": "Collusion Detections",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 8},
                    "targets": [
                        {
                            "expr": "increase(scholarlab_collusion_detections_total[24h])",
                        }
                    ],
                },
                {
                    "id": 5,
                    "title": "Active Anomaly Alerts",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "scholarlab_active_anomaly_alerts",
                        }
                    ],
                    "colorMode": "background",
                    "fieldConfig": {
                        "defaults": {
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 1},
                                    {"color": "red", "value": 5},
                                ]
                            },
                        }
                    },
                },
                {
                    "id": 6,
                    "title": "Curriculum Sync Performance",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 12},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(scholarlab_curriculum_sync_duration_ms_bucket[5m]))",
                            "legendFormat": "{{operation}}",
                        }
                    ],
                },
            ],
        }
    }


def create_system_health_dashboard() -> Dict[str, Any]:
    """Create dashboard for system health indicators."""
    return {
        "dashboard": {
            "title": "ScholarLab System Health",
            "tags": ["production", "health", "system"],
            "timezone": "browser",
            "refresh": "30s",
            "panels": [
                {
                    "id": 1,
                    "title": "Database Operation Latency",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(scholarlab_database_operation_duration_ms_bucket[5m]))",
                            "legendFormat": "{{operation}} on {{collection}}",
                        }
                    ],
                    "yaxes": [
                        {
                            "label": "Latency (ms)",
                            "format": "ms",
                        }
                    ],
                },
                {
                    "id": 2,
                    "title": "Active WebSocket Connections",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "scholarlab_active_websocket_connections",
                            "legendFormat": "{{connection_type}}",
                        }
                    ],
                    "yaxes": [
                        {
                            "label": "Connections",
                        }
                    ],
                },
                {
                    "id": 3,
                    "title": "Background Job Performance",
                    "type": "graph",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(scholarlab_background_job_duration_ms_bucket[5m]))",
                            "legendFormat": "{{job_name}} - {{status}}",
                        }
                    ],
                    "yaxes": [
                        {
                            "label": "Latency (ms)",
                            "format": "ms",
                        }
                    ],
                },
                {
                    "id": 4,
                    "title": "Login Attempts (Success Rate)",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "rate(scholarlab_login_attempts_total{result='success'}[1h]) / rate(scholarlab_login_attempts_total[1h])",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0.95},
                                    {"color": "green", "value": 0.99},
                                ]
                            },
                        }
                    },
                },
            ],
        }
    }


def export_all_dashboards() -> Dict[str, Any]:
    """Export all dashboards."""
    return {
        "latency": create_latency_dashboard(),
        "security": create_security_dashboard(),
        "analytics": create_analytics_dashboard(),
        "health": create_system_health_dashboard(),
    }


if __name__ == "__main__":
    # Export dashboards to JSON files
    dashboards = export_all_dashboards()
    
    for name, dashboard in dashboards.items():
        filename = f"dashboard_{name}.json"
        with open(filename, "w") as f:
            json.dump(dashboard, f, indent=2)
        print(f"Exported {filename}")
