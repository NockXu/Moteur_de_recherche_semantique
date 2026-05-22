from typing import Optional
from .weightCalculator import *

expressions = {
    "Equal": {
        "description": "Poids constant indépendant de la similarité et de la position. Sert de baseline neutre.",
        "function": "const"
    },

    "Sum": {
        "description": "Accumulation linéaire de la similarité. Augmente le poids lorsque les vecteurs restent cohérents au fil des étapes.",
        "function": "prev + sim"
    },

    "Mult": {
        "description": "Décroissance multiplicative. Réduit fortement le poids en cas de faible similarité et renforce la cohérence lorsque la similarité est élevée.",
        "function": "prev * sim"
    },

    "Mult + 1": {
        "description": "Multiplication avec décalage positif. Empêche l’effondrement du poids à zéro et stabilise l’évolution.",
        "function": "const + prev * sim"
    },

    "p + prev * sim": {
        "description": "Propagation multiplicative avec biais de position. La profondeur influence directement le poids final.",
        "function": "p + prev * sim"
    },

    "p + prev + sim": {
        "description": "Accumulation additive avec influence de la position. Favorise les éléments profonds dans la structure.",
        "function": "p + prev + sim"
    }
}

weight_functions: List[WeightFunction] = []

for name, data in expressions.items():
    weight_functions.append(
        WeightFunction(
            name,
            data["description"],
            WeightSystem(data["function"])
        )
    )

def get_weight_function_by_expr(expr : WeightSystem) -> Optional[WeightFunction]:
    for weight_fonction in weight_functions:
        if weight_fonction.weight_fn.expr == expr.expr:
            return weight_fonction

    return None