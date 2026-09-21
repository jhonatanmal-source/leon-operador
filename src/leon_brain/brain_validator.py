from .brain_models import BrainResult, OperationalBrainContext


GUARDS = {
    "execute_true": "BrainResult nunca pode conter execute=true",
    "alter_order_request": "BrainResult nunca pode alterar order_request",
    "alter_risk_request": "BrainResult nunca pode alterar risk_request",
    "alter_sl_tp": "BrainResult nunca pode alterar SL, TP ou lote",
    "alter_pre_operation": "BrainResult nunca pode alterar PRE_OPERATION de bloqueado para liberado",
    "memory_as_confirmation": "Memoria nao pode ser usada como confirmacao estrutural",
}


class BrainValidator:

    @staticmethod
    def validate_result(result: BrainResult) -> list[str]:
        violations = []

        if result.can_execute():
            violations.append(GUARDS["execute_true"])

        if result.can_alter_order():
            violations.append(GUARDS["alter_order_request"])

        if result.can_alter_risk():
            violations.append(GUARDS["alter_risk_request"])

        if result.can_alter_sl_tp():
            violations.append(GUARDS["alter_sl_tp"])

        return violations

    @staticmethod
    def validate_context(context: OperationalBrainContext) -> list[str]:
        warnings = []

        if not context.timestamp:
            warnings.append("Contexto sem timestamp")
        if not context.symbol:
            warnings.append("Contexto sem symbol")
        if context.price <= 0:
            warnings.append("Preco invalido ou nao informado")

        return warnings

    @staticmethod
    def is_safe(result: BrainResult) -> bool:
        return len(BrainValidator.validate_result(result)) == 0
