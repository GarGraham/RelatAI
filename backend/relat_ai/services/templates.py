"""In-memory storage for reusable configuration templates."""

from __future__ import annotations

from threading import RLock

from relat_ai.core.models import ConfigurationTemplate, DatasetConfiguration


class TemplateStore:
    """Thread-safe template store keyed by dataset identifier."""

    def __init__(self) -> None:
        self._templates: dict[str, dict[str, ConfigurationTemplate]] = {}
        self._lock = RLock()

    def create(
        self,
        *,
        dataset_id: str,
        name: str,
        configuration: DatasetConfiguration,
        description: str | None = None,
    ) -> ConfigurationTemplate:
        template = ConfigurationTemplate(
            dataset_id=dataset_id,
            name=name,
            description=description,
            configuration=configuration.model_copy(deep=True),
        )
        with self._lock:
            templates = self._templates.setdefault(dataset_id, {})
            templates[template.template_id] = template
        return template.model_copy(deep=True)

    def list(self, dataset_id: str) -> list[ConfigurationTemplate]:
        with self._lock:
            templates = self._templates.get(dataset_id, {})
            return [template.model_copy(deep=True) for template in templates.values()]

    def get(self, dataset_id: str, template_id: str) -> ConfigurationTemplate | None:
        with self._lock:
            template = self._templates.get(dataset_id, {}).get(template_id)
            if template is None:
                return None
            return template.model_copy(deep=True)

    def delete(self, dataset_id: str, template_id: str) -> None:
        with self._lock:
            templates = self._templates.get(dataset_id)
            if not templates:
                return
            templates.pop(template_id, None)

    def reset(self) -> None:
        with self._lock:
            self._templates.clear()


_STORE = TemplateStore()


def reset_templates() -> None:
    """Reset the global template store (useful for isolated tests)."""

    _STORE.reset()


def create_template(
    *,
    dataset_id: str,
    name: str,
    configuration: DatasetConfiguration,
    description: str | None = None,
) -> ConfigurationTemplate:
    return _STORE.create(
        dataset_id=dataset_id,
        name=name,
        configuration=configuration,
        description=description,
    )


def list_templates(dataset_id: str) -> list[ConfigurationTemplate]:
    return _STORE.list(dataset_id)


def get_template(dataset_id: str, template_id: str) -> ConfigurationTemplate | None:
    return _STORE.get(dataset_id, template_id)


def delete_template(dataset_id: str, template_id: str) -> None:
    _STORE.delete(dataset_id, template_id)

