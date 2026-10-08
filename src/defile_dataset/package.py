"""Load the single JSON schema, generate documentation and validate released CSVs."""

from datetime import date, datetime
import json
from pathlib import Path
import shutil

from frictionless import Package
import pandas as pd

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "config/schema/datapackage.json"


def descriptor():
    return json.loads(SCHEMA_FILE.read_text())


def columns(name):
    resource = next(resource for resource in descriptor()["resources"] if resource["name"] == name)
    return [field["name"] for field in resource["schema"]["fields"]]


def dictionary():
    """Render definitions, constraints and links directly from the JSON descriptor."""
    package = descriptor()
    text = "\n## Column dictionary\n\nGenerated from config/schema/datapackage.json; edit that source rather than these tables.\n"
    text += "\n" + package["x-validationNotes"] + "\n"
    for resource in package["resources"]:
        schema = resource["schema"]
        rules = resource.get("x-validationRules", [])
        text += f"\n### {resource['path']}\n\n{resource['description']}\n"
        text += f"\nPrimary key: `{schema['primaryKey']}`. Missing-value tokens: `{json.dumps(schema['missingValues'])}` (an empty string means an empty cell).\n"
        for link in schema.get("foreignKeys", []):
            ref = link["reference"]
            text += f"\nForeign key: `{link['fields']}` → `{ref['resource']}.{ref['fields']}`.\n"
        text += "\n| Column | Type | Required | Constraints | Meaning |\n| --- | --- | --- | --- | --- |\n"
        for field in schema["fields"]:
            constraints = field.get("constraints", {})
            conditional = any(rule["field"] == field["name"] and rule["kind"] == "requiredWhen" for rule in rules)
            required = "Yes" if constraints.get("required") else "Conditional" if conditional else "No"
            details = "; ".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in constraints.items() if key != "required")
            cells = [field["name"], field["type"], required, details or "—", field["description"]]
            text += "| " + " | ".join(cell.replace("|", "&#124;").replace("\n", " ") for cell in cells) + " |\n"
        for field in schema["fields"]:
            definitions = field.get("x-enumDescriptions", {})
            if definitions:
                text += f"\n`{field['name']}` codes (empty cells remain missing):\n\n| Code | Meaning | Evidence / notes |\n| --- | --- | --- |\n"
                for code, definition in definitions.items():
                    evidence = "; ".join(value for value in [definition.get("evidenceStatus", ""), definition.get("note", "")] if value)
                    cells = [code, definition["description"], evidence or "—"]
                    text += "| " + " | ".join(cell.replace("|", "&#124;") for cell in cells) + " |\n"
        if rules:
            text += "\nAdditional rules (declared in the descriptor):\n\n"
            text += "".join(f"- `{rule['field']}`: {rule['description']}\n" for rule in rules)
    return text


def attribute_dictionary():
    """Generate the attribute evidence CSV from the authoritative enum definitions."""
    resource = next(r for r in descriptor()["resources"] if r["name"] == "count")
    rows = []
    for field in resource["schema"]["fields"]:
        if field["name"] not in ("age", "sex", "plumage"):
            continue
        for code in field["constraints"]["enum"]:
            meaning = field["x-enumDescriptions"][code]
            rows.append({"attribute": field["name"], "trektellen_code": code,
                         "meaning": meaning["description"], "evidence_status": meaning["evidenceStatus"],
                         "batumi_code": meaning["batumiCode"], "batumi_match": meaning["batumiMatch"],
                         "source": meaning["source"], "note": meaning["note"], "example_data_id": meaning["exampleDataId"]})
    return pd.DataFrame(rows)


def generate_docs(dataset_dir, repository_docs=True):
    """Write the package dictionary from the schema and maintained usage guide."""
    root = SCHEMA_FILE.parents[2]
    dataset_dir = Path(dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCHEMA_FILE, dataset_dir / 'datapackage.json')
    usage_file = root / 'docs/dataset.md'
    usage = usage_file.read_text() if usage_file.exists() else '# Dataset\n\n' + descriptor()['description'] + '\n'
    for name in ('pipeline.md', 'table-columns.md', 'survey-coverage.md', 'audit.md', 'bird-attributes.md', 'processing.md', 'taxonomy.md'):
        usage = usage.replace(f'({name})', f'(https://github.com/Rafnuss/defile-dataset/blob/main/docs/{name})')
    (dataset_dir / 'README.md').write_text(usage + dictionary())
    if repository_docs and usage_file.exists():
        attribute_dictionary().to_csv(root / 'docs/bird_attribute_codes.csv', index=False)
        (root / 'docs/table-columns.md').write_text('# Dataset column definitions\n\n' + dictionary())


def valid_iso(value, rule):
    """Interpret the ISO forms and offset/interval requirements declared in a rule."""
    parts = value.split("/")
    form = "interval" if len(parts) == 2 else "datetime" if "T" in value else "date"
    if form not in rule["allow"] or len(parts) > 2:
        return False
    try:
        parsed = []
        for part in parts:
            if "T" in part:
                time = datetime.fromisoformat(part)
                if rule.get("requireOffset") and time.utcoffset() is None:
                    return False
                if rule.get("requireUTC") and time.utcoffset().total_seconds() != 0:
                    return False
            else:
                if form == "interval" and rule.get("requireOffset"):
                    return False
                time = date.fromisoformat(part)
                if part != time.isoformat():
                    return False
            parsed.append(time)
        return form != "interval" or not rule.get("orderedInterval") or parsed[0] < parsed[1]
    except (ValueError, TypeError):
        return False


def validate_package(path):
    """Validate CSV bytes with Frictionless, then evaluate the JSON's conditional rules."""
    path = Path(path)
    package = json.loads(path.read_text())
    report = Package(str(path)).validate().to_descriptor()
    report["x-projectErrors"] = []
    if report["valid"]:
        for resource in package["resources"]:
            rules = resource.get("x-validationRules", [])
            if not rules:
                continue
            data = pd.read_csv(path.parent / resource["path"], dtype=str, keep_default_na=False)
            missing = resource["schema"]["missingValues"]
            for rule in rules:
                field = data[rule["field"]]
                if rule["kind"] == "iso8601":
                    valid = {value: valid_iso(value, rule) for value in field[~field.isin(missing)].unique()}
                    failed = ~field.isin(missing) & field.map(valid).eq(False)
                else:
                    when = rule["when"]
                    other = data[when["field"]]
                    if "missing" in when:
                        matches = other.isin(missing) if when["missing"] else ~other.isin(missing)
                    elif "equals" in when:
                        matches = other.eq(when["equals"])
                    else:
                        matches = other.ne(when["notEquals"])
                    if rule["kind"] == "requiredWhen":
                        failed = matches & field.isin(missing)
                    elif rule["kind"] == "missingWhen":
                        failed = matches & ~field.isin(missing)
                    elif rule["kind"] == "allowedWhen":
                        valid = field.isin(rule["values"]) if "values" in rule else field.str.fullmatch(rule["pattern"])
                        failed = matches & ~valid
                    elif rule["kind"] == "foreignKeyWhen":
                        reference = rule["reference"]
                        target = next(r for r in package["resources"] if r["name"] == reference["resource"])
                        linked = pd.read_csv(path.parent / target["path"], dtype=str, keep_default_na=False)
                        failed = matches & ~field.isin(linked[reference["fields"]])
                    else:
                        raise ValueError(f"Unknown validation rule: {rule['kind']}")
                if failed.any():
                    report["x-projectErrors"].append({
                        "resource": resource["name"], "field": rule["field"],
                        "kind": rule["kind"], "message": rule["description"],
                        "count": int(failed.sum()), "rowNumbers": (data.index[failed][:20] + 2).tolist(),
                    })
    report["valid"] = report["valid"] and not report["x-projectErrors"]
    return report
