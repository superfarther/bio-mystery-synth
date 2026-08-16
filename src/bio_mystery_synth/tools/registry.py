from bio_mystery_synth.tools.catalog import ToolDescriptor, tool_descriptors


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}

    def register(self, descriptor: ToolDescriptor) -> None:
        if descriptor.name in self._tools:
            raise ValueError(f"duplicate tool: {descriptor.name}")
        self._tools[descriptor.name] = descriptor

    def get(self, name: str) -> ToolDescriptor:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(f"unknown tool: {name}") from exc

    def descriptors(self) -> dict[str, ToolDescriptor]:
        return dict(self._tools)


def builtin_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for descriptor in tool_descriptors().values():
        registry.register(descriptor)
    return registry
