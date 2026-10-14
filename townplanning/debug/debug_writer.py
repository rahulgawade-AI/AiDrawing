import json
from pathlib import Path
from dataclasses import asdict, is_dataclass


class DebugWriter:
    """
    Writes all intermediate pipeline artifacts.

    debug_output/
        5.10/
            regulation.json
            knowledge.json
            rules.json
            prompt.txt
    """

    def __init__(self, root="debug_output"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _folder(self, regulation_number: str):
        folder = self.root / regulation_number.replace("/", "_")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _dump(self, obj):
        if is_dataclass(obj):
            return asdict(obj)

        if isinstance(obj, list):
            data = []
            for item in obj:
                if is_dataclass(item):
                    data.append(asdict(item))
                elif hasattr(item, "__dict__"):
                    data.append(item.__dict__)
                else:
                    data.append(item)
            return data

        if hasattr(obj, "__dict__"):
            return obj.__dict__

        return obj

    def save_regulation(self, regulation):

        folder = self._folder(regulation.number)

        with open(folder / "regulation.json", "w", encoding="utf8") as f:
            json.dump(
                self._dump(regulation),
                f,
                indent=2,
                ensure_ascii=False,
            )

    def save_knowledge(self, regulation_number, knowledge):

        folder = self._folder(regulation_number)

        with open(folder / "knowledge.json", "w", encoding="utf8") as f:
            json.dump(
                self._dump(knowledge),
                f,
                indent=2,
                ensure_ascii=False,
            )

    def save_rules(self, regulation_number, rules):

        folder = self._folder(regulation_number)

        with open(folder / "rules.json", "w", encoding="utf8") as f:
            json.dump(
                self._dump(rules),
                f,
                indent=2,
                ensure_ascii=False,
            )

    def save_prompt(self, regulation_number, prompt):

        folder = self._folder(regulation_number)

        with open(folder / "prompt.txt", "w", encoding="utf8") as f:
            f.write(prompt)

    def save_split_chunks(self, page_number, chunks):

        page_dir = self.root / "splitter"
        page_dir.mkdir(exist_ok=True)

        with open(
            page_dir / f"page_{page_number}.json",
            "w",
            encoding="utf8",
        ) as f:
            json.dump(
                self._dump(chunks),
                f,
                indent=2,
                ensure_ascii=False,
            )

    def save_summary(self, summary):

        with open(
            self.root / "summary.json",
            "w",
            encoding="utf8",
        ) as f:
            json.dump(summary, f, indent=2)