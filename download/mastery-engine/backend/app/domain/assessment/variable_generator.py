"""Variable Generator — deterministic value generation with seeds.

Each generator accepts a seed and produces deterministic output.
Same seed → same output (invariant I3, ADR-0007).

Generators:
- Random Integer
- Random Float
- Variable Name
- Function Name
- List
- Dictionary
- String
- Boolean
- Nested Structure
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GeneratedVariables:
    """Container for all variables generated for a question instance."""

    values: dict[str, Any]

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)


class VariableGenerator:
    """Deterministic variable generator.

    Uses Python's `random` module with a fixed seed to ensure
    reproducibility. Same seed → same variables → same question.

    Usage:
        gen = VariableGenerator(seed=42)
        x = gen.integer("x", min_val=1, max_val=100)
        name = gen.variable_name("var_name")
        lst = gen.list("my_list", size=5, element_type="int", min_val=0, max_val=10)
    """

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._rng = random.Random(seed)
        self._values: dict[str, Any] = {}

    @property
    def values(self) -> dict[str, Any]:
        return dict(self._values)

    def integer(self, name: str, min_val: int = 0, max_val: int = 100) -> int:
        """Generate a random integer."""
        val = self._rng.randint(min_val, max_val)
        self._values[name] = val
        return val

    def float(self, name: str, min_val: float = 0.0, max_val: float = 1.0, precision: int = 2) -> float:
        """Generate a random float."""
        val = round(self._rng.uniform(min_val, max_val), precision)
        self._values[name] = val
        return val

    def variable_name(self, name: str = "var") -> str:
        """Generate a Python variable name."""
        prefixes = ["x", "y", "z", "val", "data", "result", "item", "n", "s", "k"]
        prefix = self._rng.choice(prefixes)
        suffix = self._rng.randint(1, 99)
        val = f"{prefix}{suffix}"
        self._values[name] = val
        return val

    def function_name(self, name: str = "func") -> str:
        """Generate a Python function name."""
        verbs = ["get", "set", "process", "compute", "fetch", "parse", "validate", "transform"]
        nouns = ["data", "value", "result", "item", "list", "config", "status"]
        val = f"{self._rng.choice(verbs)}_{self._rng.choice(nouns)}"
        self._values[name] = val
        return val

    def list(self, name: str, size: int = 5, element_type: str = "int", min_val: int = 0, max_val: int = 100) -> list[Any]:
        """Generate a list of values."""
        result: list[Any] = []
        for _ in range(size):
            if element_type == "int":
                result.append(self._rng.randint(min_val, max_val))
            elif element_type == "float":
                result.append(round(self._rng.uniform(min_val, max_val), 2))
            elif element_type == "str":
                result.append(self._rng.choice(["a", "b", "c", "d", "e"]))
            else:
                result.append(self._rng.randint(min_val, max_val))
        self._values[name] = result
        return result

    def dictionary(self, name: str, size: int = 3, key_type: str = "str", val_type: str = "int") -> dict[str, Any]:
        """Generate a dictionary."""
        result: dict[str, Any] = {}
        keys_used: set[str] = set()
        for _ in range(size):
            if key_type == "str":
                k = self._rng.choice(["name", "age", "id", "type", "value", "key", "data"])
                while k in keys_used:
                    k = self._rng.choice(["name", "age", "id", "type", "value", "key", "data"])
                keys_used.add(k)
            else:
                k = self._rng.randint(1, 100)

            if val_type == "int":
                v = self._rng.randint(0, 1000)
            elif val_type == "str":
                v = self._rng.choice(["alpha", "beta", "gamma", "delta"])
            else:
                v = self._rng.randint(0, 1000)
            result[str(k)] = v
        self._values[name] = result
        return result

    def string(self, name: str, length: int = 10) -> str:
        """Generate a random string."""
        chars = "abcdefghijklmnopqrstuvwxyz_"
        val = "".join(self._rng.choice(chars) for _ in range(length))
        self._values[name] = val
        return val

    def boolean(self, name: str) -> bool:
        """Generate a random boolean."""
        val = self._rng.choice([True, False])
        self._values[name] = val
        return val

    def choice(self, name: str, options: list[Any]) -> Any:
        """Pick a random element from options."""
        val = self._rng.choice(options)
        self._values[name] = val
        return val

    def generate_from_schema(self, schema: dict[str, Any]) -> GeneratedVariables:
        """Generate variables from a schema definition.

        Schema format:
            {
                "x": {"type": "integer", "min": 1, "max": 100},
                "name": {"type": "variable_name"},
                "my_list": {"type": "list", "size": 5, "element_type": "int", "min": 0, "max": 10},
                "my_dict": {"type": "dictionary", "size": 3},
                "flag": {"type": "boolean"},
                "my_choice": {"type": "choice", "options": ["a", "b", "c"]}
            }
        """
        for var_name, spec in schema.items():
            var_type = spec.get("type", "integer")

            if var_type == "integer":
                self.integer(var_name, spec.get("min", 0), spec.get("max", 100))
            elif var_type == "float":
                self.float(var_name, spec.get("min", 0.0), spec.get("max", 1.0), spec.get("precision", 2))
            elif var_type == "variable_name":
                self.variable_name(var_name)
            elif var_type == "function_name":
                self.function_name(var_name)
            elif var_type == "list":
                self.list(var_name, spec.get("size", 5), spec.get("element_type", "int"),
                         spec.get("min", 0), spec.get("max", 100))
            elif var_type == "dictionary":
                self.dictionary(var_name, spec.get("size", 3))
            elif var_type == "string":
                self.string(var_name, spec.get("length", 10))
            elif var_type == "boolean":
                self.boolean(var_name)
            elif var_type == "choice":
                self.choice(var_name, spec.get("options", ["a", "b", "c"]))

        return GeneratedVariables(values=self.values)
