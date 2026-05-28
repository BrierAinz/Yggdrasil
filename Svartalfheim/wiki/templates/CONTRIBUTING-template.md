# ⚒️ Contributing to {project_name}

> *Todo guerrero que levanta un martillo fortalece el Yggdrasil.*

Gracias por contribuir. Este documento te guía por el proceso.

---

## 📋 Código de Conducta

- Sé respetuoso y constructivo
- El código sigue la estética dark fantasy del ecosistema
- Toda contribución se rige por las reglas de Yggdrasil

---

## 🔄 Flujo de Contribución

```
1. Fork o crear branch
2. Desarrollar + tests
3. Self-review
4. Formatear (black, isort)
5. Commit con convención
6. Push
7. Documentar cambios en Svartalfheim si son significativos
```

---

## 📏 Convención de Commits

| Prefijo | Uso |
|---------|-----|
| `feat:` | Nueva funcionalidad |
| `fix:` | Bug fix |
| `docs:` | Documentación |
| `refactor:` | Refactor sin cambio funcional |
| `test:` | Tests |
| `chore:` | Mantenimiento |
| `perf:` | Performance |

Ejemplo:
```bash
git commit -m "feat(memory): add keyword extraction to session store"
```

---

## 🎨 Estilo de Código

### Python
- **Formatter**: Black (line length: 88)
- **Imports**: isort con `profile=black`
- **Type hints**: Usar para interfaces públicas
- **Docstrings**: Google style

### Markdown
- Frontmatter YAML siempre presente
- Emojis rúnicos cuando sea apropiado
- Links relativos dentro del ecosistema

---

## 🧪 Testing

```bash
# Todos los tests
pytest -v

# Solo los afectados
pytest tests/test_module.py -v

# Con coverage
pytest --cov --cov-report=term-missing
```

### Requisitos
- Todo PR nuevo debe incluir tests
- No seMerge sin tests pasando
- Coverage target: >80%

---

## 📁 Estructura de Archivos

```
{project_name}/
├── src/
│   └── module/
│       ├── __init__.py
│       ├── core.py
│       └── utils.py
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   └── test_utils.py
├── docs/
│   └── ...
├── README.md
├── requirements.txt
└── pyproject.toml
```

---

## 🔍 Review Checklist

- [ ] Código en el reino correcto
- [ ] Tests pasando
- [ ] Formateado con black + isort
- [ ] Sin `__pycache__` o node_modules commiteados
- [ ] README.md actualizado si hay cambios estructurales
- [ ] ADR si es una decisión arquitectónica

---

*Forjado en Svartalfheim 🔨*
