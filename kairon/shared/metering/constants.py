from enum import Enum


class UpdateMetricType(str, Enum):
    conversation_feedback = "conversation_feedback"


class MetricType(str, Enum):
    test_chat = "test_chat"
    prod_chat = "prod_chat"
    agent_handoff = "agent_handoff"
    user_metrics = "user_metrics"
    user_login = "user_login"
    invalid_login = "invalid_login"
    login = "login"
    login_refresh_token = "login_refresh_token"
    faq_training = "faq_training"
    conversation_feedback = "conversation_feedback"
