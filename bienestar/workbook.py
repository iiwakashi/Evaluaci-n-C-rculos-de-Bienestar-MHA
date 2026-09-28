from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import re
import unicodedata

import pandas as pd


SCORE_NAMES = {1: "Rojo", 2: "Amarillo", 3: "Verde"}


@dataclass(frozen=True)
class Indicator:
    number: str
    dimension: str
    label: str
    answers: dict[int, str]
    response_column: str

    @property
    def key(self) -> str:
        return normalize_label(self.label)


@dataclass
class WorkbookData:
    filename: str
    responses_sheet: str | None = None
    setup_sheet: str | None = None
    id_column: str | None = None
    name_column: str | None = None
    city_column: str | None = None
    indicators: list[Indicator] = field(default_factory=list)
    people: pd.DataFrame = field(default_factory=pd.DataFrame)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class ComparisonData:
    people: pd.DataFrame
    indicators: tuple[Indicator, ...]
    only_entry: int
    only_exit: int


def normalize_label(value: object) -> str:
    """Normaliza rótulos para encontrar hojas y columnas sin depender de tildes."""
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("º", "o").replace("°", "o")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def normalize_answer(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def normalize_identifier(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    compact = re.sub(r"[\s.\-]", "", text)
    return compact if compact.isdigit() else text.casefold()


def _find_sheet(sheet_names: list[str], expected: str) -> str | None:
    normalized_expected = normalize_label(expected).replace(" ", "")
    matches = [
        name
        for name in sheet_names
        if normalize_label(name).replace(" ", "") == normalized_expected
    ]
    return matches[0] if len(matches) == 1 else None


def _find_column(columns: list[object], aliases: tuple[str, ...]) -> str | None:
    normalized = {str(column): normalize_label(column) for column in columns}
    alias_keys = [normalize_label(alias) for alias in aliases]
    for alias in alias_keys:
        exact = [column for column, key in normalized.items() if key == alias]
        if len(exact) == 1:
            return exact[0]
    return None


def _read_setup(excel: pd.ExcelFile, sheet_name: str) -> tuple[list[dict], list[str]]:
    raw = pd.read_excel(excel, sheet_name=sheet_name, header=None, dtype=object)
    errors: list[str] = []
    header_row = None
    column_map: dict[str, int] = {}
    required = {
        "indicator": ("indicador", "indicador o"),
        "dimension": ("dimension",),
        "label": ("nombre corto",),
        "red": ("rojo",),
        "yellow": ("amarillo",),
        "green": ("verde",),
    }

    for row_index in range(min(len(raw), 20)):
        values = [normalize_label(value) for value in raw.iloc[row_index].tolist()]
        candidate: dict[str, int] = {}
        for field_name, aliases in required.items():
            alias_keys = {normalize_label(alias) for alias in aliases}
            found = [index for index, value in enumerate(values) if value in alias_keys]
            if found:
                candidate[field_name] = found[0]
        if len(candidate) == len(required):
            header_row = row_index
            column_map = candidate
            break

    if header_row is None:
        return [], ["La hoja SET UP no contiene las columnas Indicador, Dimensión, Nombre corto, ROJO, AMARILLO y VERDE."]

    rows: list[dict] = []
    for row_index in range(header_row + 1, len(raw)):
        row = raw.iloc[row_index]
        label = row.iloc[column_map["label"]]
        if normalize_label(label) == "":
            continue
        answers = {
            1: row.iloc[column_map["red"]],
            2: row.iloc[column_map["yellow"]],
            3: row.iloc[column_map["green"]],
        }
        if any(normalize_answer(answer) == "" for answer in answers.values()):
            errors.append(f"El indicador '{label}' no tiene las tres respuestas de color en SET UP.")
            continue
        rows.append(
            {
                "number": str(row.iloc[column_map["indicator"]]).strip(),
                "dimension": str(row.iloc[column_map["dimension"]]).strip(),
                "label": str(label).strip(),
                "answers": {score: str(answer).strip() for score, answer in answers.items()},
            }
        )

    if not rows:
        errors.append("SET UP no contiene indicadores utilizables.")
    return rows, errors


def _match_response_column(columns: list[object], label: str) -> tuple[str | None, str | None]:
    label_key = normalize_label(label)
    stopwords = {"a", "de", "del", "el", "la", "las", "los", "y"}
    label_terms = {term for term in label_key.split() if term not in stopwords}
    matches = []
    for column in columns:
        column_key = normalize_label(column)
        question_key = normalize_label(str(column).split(":", 1)[0])
        question_terms = {term for term in question_key.split() if term not in stopwords}
        exact_or_prefix = label_key and (
            column_key.startswith(label_key) or label_key.startswith(column_key)
        )
        same_question_terms = label_terms and label_terms == question_terms
        if exact_or_prefix or same_question_terms:
            matches.append(str(column))
    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return None, f"No se encontró en RESPUESTAS la pregunta correspondiente a '{label}'."
    return None, f"La pregunta '{label}' coincide con varias columnas de RESPUESTAS: {', '.join(matches)}."


def load_workbook(filename: str, content: bytes) -> WorkbookData:
    result = WorkbookData(filename=filename)
    try:
        excel = pd.ExcelFile(BytesIO(content), engine="openpyxl")
    except Exception as exc:  # pragma: no cover - depende del motor y del archivo dañado
        result.errors.append(f"No fue posible abrir el archivo como Excel: {exc}")
        return result

    result.responses_sheet = _find_sheet(excel.sheet_names, "RESPUESTAS")
    result.setup_sheet = _find_sheet(excel.sheet_names, "SET UP")
    if result.responses_sheet is None:
        result.errors.append("No se encontró una única hoja llamada RESPUESTAS.")
    if result.setup_sheet is None:
        result.errors.append("No se encontró una única hoja llamada SET UP o SETUP.")
    if result.errors:
        return result

    setup_rows, setup_errors = _read_setup(excel, result.setup_sheet)
    result.errors.extend(setup_errors)

    responses = pd.read_excel(
        excel,
        sheet_name=result.responses_sheet,
        dtype=object,
    ).dropna(how="all")
    columns = responses.columns.tolist()
    result.id_column = _find_column(
        columns,
        ("Número de Cédula", "Numero de Cedula", "Cédula", "Cedula"),
    )
    result.name_column = _find_column(columns, ("Nombre Completo", "Nombre y apellidos", "Nombre"))
    result.city_column = _find_column(columns, ("Ciudad", "Municipio", "Territorio"))
    if result.id_column is None:
        result.errors.append("RESPUESTAS no contiene una columna reconocible de número de cédula.")
    if result.name_column is None:
        result.errors.append("RESPUESTAS no contiene una columna reconocible de nombre completo.")

    indicators: list[Indicator] = []
    for setup_row in setup_rows:
        response_column, error = _match_response_column(columns, setup_row["label"])
        if error:
            result.errors.append(error)
            continue
        indicators.append(
            Indicator(
                number=setup_row["number"],
                dimension=setup_row["dimension"],
                label=setup_row["label"],
                answers=setup_row["answers"],
                response_column=response_column,
            )
        )
    result.indicators = indicators
    if result.errors:
        return result

    answer_columns = [indicator.response_column for indicator in indicators]
    relevant_columns = [result.id_column, result.name_column, *answer_columns]
    if result.city_column:
        relevant_columns.append(result.city_column)
    people = responses[relevant_columns].copy()
    people["_id"] = people[result.id_column].map(normalize_identifier)
    people["_name"] = people[result.name_column].fillna("").astype(str).str.strip()

    empty_rows = people["_id"].eq("") & people[answer_columns].isna().all(axis=1)
    if empty_rows.any():
        result.warnings.append(f"Se ignoraron {int(empty_rows.sum())} filas completamente vacías.")
        people = people.loc[~empty_rows].copy()

    missing_id = people["_id"].eq("")
    if missing_id.any():
        result.errors.append(f"Hay {int(missing_id.sum())} respuestas con datos pero sin número de cédula.")
    missing_name = people["_name"].eq("")
    if missing_name.any():
        result.errors.append(f"Hay {int(missing_name.sum())} personas sin nombre completo.")
    duplicates = people.loc[people["_id"].ne(""), "_id"].duplicated(keep=False)
    if duplicates.any():
        result.errors.append(
            f"Hay {people.loc[duplicates, '_id'].nunique()} cédulas duplicadas; debe existir una fila por persona y momento."
        )

    for indicator in indicators:
        lookup = {
            normalize_answer(answer): score for score, answer in indicator.answers.items()
        }
        normalized_answers = people[indicator.response_column].map(normalize_answer)
        score_column = f"score::{indicator.key}"
        people[score_column] = normalized_answers.map(lookup)
        missing = normalized_answers.eq("")
        unmatched = normalized_answers.ne("") & people[score_column].isna()
        if missing.any():
            result.errors.append(
                f"'{indicator.label}' tiene {int(missing.sum())} respuestas vacías."
            )
        if unmatched.any():
            result.errors.append(
                f"'{indicator.label}' tiene {int(unmatched.sum())} respuestas que no coinciden con SET UP."
            )

    result.people = people.reset_index(drop=True)
    return result


def _setup_signature(workbook: WorkbookData) -> dict[str, tuple]:
    return {
        indicator.key: (
            normalize_label(indicator.dimension),
            tuple(normalize_answer(indicator.answers[score]) for score in (1, 2, 3)),
        )
        for indicator in workbook.indicators
    }


def compare_workbooks(entry: WorkbookData, exit_: WorkbookData) -> tuple[ComparisonData | None, list[str]]:
    errors: list[str] = []
    if not entry.ok or not exit_.ok:
        return None, ["Los dos archivos deben superar sus validaciones antes de compararlos."]
    if _setup_signature(entry) != _setup_signature(exit_):
        errors.append("Los indicadores o las clasificaciones de SET UP difieren entre entrada y salida.")
        return None, errors

    entry_ids = set(entry.people["_id"])
    exit_ids = set(exit_.people["_id"])
    common_ids = entry_ids & exit_ids
    if not common_ids:
        return None, ["No hay personas comunes entre los archivos de entrada y salida."]

    entry_columns = ["_id", "_name"] + [f"score::{indicator.key}" for indicator in entry.indicators]
    exit_columns = ["_id", "_name"] + [f"score::{indicator.key}" for indicator in exit_.indicators]
    merged = entry.people[entry_columns].merge(
        exit_.people[exit_columns],
        on="_id",
        how="inner",
        suffixes=("_entry", "_exit"),
        validate="one_to_one",
    )
    merged["_display_name"] = merged["_name_exit"].where(
        merged["_name_exit"].str.strip().ne(""), merged["_name_entry"]
    )
    return (
        ComparisonData(
            people=merged.sort_values("_display_name", key=lambda series: series.str.casefold()).reset_index(drop=True),
            indicators=tuple(entry.indicators),
            only_entry=len(entry_ids - exit_ids),
            only_exit=len(exit_ids - entry_ids),
        ),
        errors,
    )


def person_evolution(comparison: ComparisonData, person_id: str) -> tuple[list[dict], dict[str, int]]:
    selected = comparison.people.loc[comparison.people["_id"] == person_id]
    if len(selected) != 1:
        raise ValueError("La persona seleccionada no tiene una comparación única.")
    row = selected.iloc[0]
    evolution: list[dict] = []
    improved = worsened = unchanged = 0
    for indicator in comparison.indicators:
        entry_score = int(row[f"score::{indicator.key}_entry"])
        exit_score = int(row[f"score::{indicator.key}_exit"])
        if exit_score > entry_score:
            change = "Mejora"
            improved += 1
        elif exit_score < entry_score:
            change = "Empeora"
            worsened += 1
        else:
            change = "Sin alterar"
            unchanged += 1
        evolution.append(
            {
                "number": indicator.number,
                "dimension": indicator.dimension,
                "label": indicator.label,
                "entry": entry_score,
                "exit": exit_score,
                "change": change,
            }
        )
    metrics = {
        "improved": improved,
        "worsened": worsened,
        "unchanged": unchanged,
        "net": improved - worsened,
    }
    return evolution, metrics
