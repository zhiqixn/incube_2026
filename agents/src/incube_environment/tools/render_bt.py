#!/usr/bin/env python3

import argparse
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from itertools import count
from pathlib import Path


CONTROL_NODES = {
    "Sequence",
    "Fallback",
    "ReactiveSequence",
    "ReactiveFallback",
    "Parallel",
    "Decorator",
    "Timeout",
    "RetryUntilSuccessful",
}


def _preprocess_xml(text: str) -> str:
    """Clean LLM output so ET.fromstring() can parse it.

    Handles:
    - Markdown code fences (```xml ... ```)
    - Surrounding prose before/after the XML
    - Multiple top-level elements (wrap in <root>)
    - Single <BehaviorTree> without <root> wrapper
    - Bare ``&`` that is not a valid entity reference
    """
    # 1. Remove markdown code fences (```xml ... ``` or ``` ... ```)
    fence_pattern = re.compile(
        r"```(?:xml)?\s*\n?(.*?)\n?\s*```", re.DOTALL | re.IGNORECASE
    )
    m = fence_pattern.search(text)
    if m:
        text = m.group(1)

    # 2. Find the first '<' and last '>' to trim surrounding prose
    first_lt = text.find("<")
    last_gt = text.rfind(">")
    if first_lt != -1 and last_gt != -1 and last_gt > first_lt:
        text = text[first_lt : last_gt + 1]

    text = text.strip()

    # 3. Escape bare '&' that are not part of a valid entity reference
    #    (&#NNN; &#xHHH; &name;)
    text = re.sub(
        r"&(?!(?:#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z][a-zA-Z0-9]*;))",
        "&",
        text,
    )

    # 4. Check if the text already has a proper single root element
    try:
        ET.fromstring(text)
        return text  # already well-formed
    except ET.ParseError:
        pass

    # 5. If there are multiple top-level elements or a single
    #    <BehaviorTree> without a <root> wrapper, wrap them.
    #    Extract all top-level elements.
    top_level_tags = re.findall(r"<(\w+)[\s>]", text)
    if not top_level_tags:
        raise ValueError("No XML elements found in the input text")

    # Determine main_tree_to_execute from the first <BehaviorTree ID="...">
    main_tree_id = None
    bt_id_match = re.search(r'<BehaviorTree\s+ID="([^"]+)"', text)
    if bt_id_match:
        main_tree_id = bt_id_match.group(1)

    # Wrap everything in a <root> element
    if main_tree_id:
        text = f'<root main_tree_to_execute="{main_tree_id}">\n{text}\n</root>'
    else:
        text = f"<root>\n{text}\n</root>"

    return text


# ---------------------------------------------------------------------------
# DOT graph builder – extracted from xml_to_dot to keep each method's
# cyclomatic complexity well below the flake8 threshold.
# ---------------------------------------------------------------------------


class _BtDotBuilder:
    """Converts a BehaviourTree XML element tree into a Graphviz DOT string."""

    def __init__(self, bt_map: dict[str, ET.Element]) -> None:
        self._bt_map = bt_map
        self._node_id_gen = count()
        self._lines: list[str] = []

    # -- static helpers -------------------------------------------------------

    @staticmethod
    def _esc(text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\\\\n", "\\n")  # undo double-escaped newline
        )

    @staticmethod
    def _short_tag(tag: str) -> str:
        # navigation_NavigateToPose -> NavigateToPose
        # mavros_CommandLand -> CommandLand
        # exploration_GetSearchArea -> GetSearchArea
        if "_" in tag:
            return tag.split("_", 1)[1]
        return tag

    # -- label / style --------------------------------------------------------

    @staticmethod
    def _node_style(elem) -> dict[str, str]:
        tag = elem.tag
        if tag in {"Sequence", "ReactiveSequence"}:
            return {"fill": "palegreen", "shape": "box", "penwidth": "1.7"}
        if tag in {"Fallback", "ReactiveFallback"}:
            return {"fill": "lightsalmon", "shape": "box", "penwidth": "1.7"}
        if tag == "Parallel":
            return {"fill": "plum", "shape": "box", "penwidth": "1.9"}
        if tag == "SubTree":
            return {"fill": "khaki1", "shape": "box", "penwidth": "1.5"}
        if tag in {"Timeout", "RetryUntilSuccessful"}:
            return {
                "fill": "lightgoldenrod1",
                "shape": "box",
                "penwidth": "1.4",
            }
        return {"fill": "lightsteelblue1", "shape": "box", "penwidth": "1.1"}

    def _label(self, elem) -> str:
        tag = elem.tag

        if tag == "SubTree":
            subtree_id = elem.attrib.get("ID", "UNKNOWN")
            name = elem.attrib.get("name")
            return name if name else subtree_id

        name = elem.attrib.get("name")
        if name:
            return name

        if tag == "Parallel":
            sc = elem.attrib.get("success_count", "?")
            fc = elem.attrib.get("failure_count", "?")
            return f"Parallel\nsuccess={sc} fail={fc}"

        if tag == "Timeout":
            msec = elem.attrib.get("msec", "?")
            return f"Timeout\n{msec} ms"

        if tag == "RetryUntilSuccessful":
            n = elem.attrib.get("num_attempts", "?")
            return f"RetryUntilSuccessful\\n{n} attempts"

        return self._label_action(elem)

    def _label_action(self, elem) -> str:
        base = self._short_tag(elem.tag)
        parts: list[str] = [base]

        if "agent_id" in elem.attrib:
            parts.append(elem.attrib["agent_id"])
        elif "vehicle_id" in elem.attrib:
            parts.append(elem.attrib["vehicle_id"])
        elif "source_vehicle" in elem.attrib:
            parts.append(elem.attrib["source_vehicle"])

        if "pose" in elem.attrib:
            parts.append(elem.attrib["pose"])
        elif "target_id" in elem.attrib:
            parts.append(elem.attrib["target_id"])
        elif "task" in elem.attrib:
            parts.append(elem.attrib["task"])

        if "radius_m" in elem.attrib:
            parts.append(f"r={elem.attrib['radius_m']}")

        return " | ".join(parts)

    # -- DOT emission ---------------------------------------------------------

    def _add_node(
        self,
        node_id: str,
        label_text: str,
        fill: str,
        shape: str,
        penwidth: str,
    ) -> None:
        self._lines.append(
            f'  {node_id} [label="{self._esc(label_text)}", '
            f'fillcolor="{fill}", shape="{shape}", penwidth={penwidth}];'
        )

    def _add_rank_same(self, child_ids: list[str]) -> None:
        if len(child_ids) > 1:
            self._lines.append("  { rank=same; " + "; ".join(child_ids) + "; }")

    # -- recursive walk -------------------------------------------------------

    def _visit(self, elem, parent=None, stack=None):
        if stack is None:
            stack = set()

        my_id = f"n{next(self._node_id_gen)}"
        style = self._node_style(elem)
        self._add_node(
            my_id,
            self._label(elem),
            style["fill"],
            style["shape"],
            style["penwidth"],
        )

        if parent is not None:
            self._lines.append(f"  {parent} -> {my_id};")

        if elem.tag == "SubTree":
            return self._visit_subtree(elem, my_id, stack)

        child_ids = [self._visit(child, my_id, stack) for child in elem]
        self._add_rank_same(child_ids)
        return my_id

    def _visit_subtree(self, elem, my_id: str, stack: set) -> str:
        subtree_id = elem.attrib.get("ID")
        if not subtree_id:
            return my_id

        if subtree_id in stack:
            loop_id = f"n{next(self._node_id_gen)}"
            self._add_node(
                loop_id,
                f"RecursiveRef\\n{subtree_id}",
                "mistyrose",
                "box",
                "1.2",
            )
            self._lines.append(f"  {my_id} -> {loop_id};")
            return my_id

        subtree = self._bt_map.get(subtree_id)
        if subtree is None:
            missing_id = f"n{next(self._node_id_gen)}"
            self._add_node(
                missing_id,
                f"MissingTree\\n{subtree_id}",
                "tomato",
                "box",
                "1.2",
            )
            self._lines.append(f"  {my_id} -> {missing_id};")
            return my_id

        new_stack = set(stack)
        new_stack.add(subtree_id)

        child_ids = [self._visit(child, my_id, new_stack) for child in subtree]
        self._add_rank_same(child_ids)
        return my_id

    # -- public entry point ---------------------------------------------------

    def build(self, main_tree_id: str) -> str:
        self._lines = [
            "digraph BT {",
            "  graph [",
            "    rankdir=TB,",
            "    splines=false,",
            "    nodesep=0.9,",
            "    ranksep=1.2,",
            "    pad=0.35,",
            '    bgcolor="white"',
            "  ];",
            "  node [",
            "    shape=box,",
            '    style="rounded,filled",',
            '    fillcolor="lightsteelblue1",',
            '    color="black",',
            '    fontname="Helvetica",',
            "    fontsize=11,",
            '    margin="0.18,0.10"',
            "  ];",
            "  edge [",
            '    color="black",',
            "    penwidth=1.1",
            "  ];",
        ]

        main_bt = self._bt_map[main_tree_id]
        root_id = f"n{next(self._node_id_gen)}"
        self._add_node(root_id, main_tree_id, "gold", "box", "2.0")

        top_children = [
            self._visit(child, root_id, {main_tree_id}) for child in main_bt
        ]
        self._add_rank_same(top_children)

        # Push the main mission branch and recovery branch farther apart
        if len(top_children) == 2:
            self._lines.append(
                f"  {top_children[0]} -> {top_children[1]} " f"[style=invis, minlen=4];"
            )

        self._lines.append("}")
        return "\n".join(self._lines)


def xml_to_dot(xml_text: str) -> str:
    xml_text = _preprocess_xml(xml_text)
    root = ET.fromstring(xml_text)

    main_tree_id = root.attrib.get("main_tree_to_execute")
    bt_map = {
        bt.attrib["ID"]: bt for bt in root.findall("BehaviorTree") if "ID" in bt.attrib
    }

    if not main_tree_id or main_tree_id not in bt_map:
        raise ValueError("Missing or invalid main_tree_to_execute")

    builder = _BtDotBuilder(bt_map)
    return builder.build(main_tree_id)


def render_xml_to_image(
    xml_text: str,
    output_path: str | Path = "data/bt_output.png",
    fmt: str = "png",
) -> Path:
    """Convert an XML behaviour-tree string to an image file.

    Parameters
    ----------
    xml_text : str
        The raw XML describing the behaviour tree.
    output_path : str | Path
        Destination file path (including extension).  Defaults to
        ``data/bt_output.png``.
    fmt : str
        Image format passed to Graphviz (``png``, ``svg``, ``pdf``, …).

    Returns
    -------
    Path
        The path the image was written to.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dot = xml_to_dot(xml_text)

    if shutil.which("dot") is None:
        raise FileNotFoundError(
            "Graphviz 'dot' binary not found on PATH. "
            "Install Graphviz (e.g. 'apt-get install -y graphviz') "
            "to render behaviour-tree images."
        )

    with tempfile.TemporaryDirectory() as tmp:
        dot_path = Path(tmp) / "tree.dot"
        tmp_out = Path(tmp) / f"tree.{fmt}"

        dot_path.write_text(dot, encoding="utf-8")

        subprocess.run(
            ["dot", f"-T{fmt}", str(dot_path), "-o", str(tmp_out)],
            check=True,
        )

        output_path.write_bytes(tmp_out.read_bytes())

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_file")
    parser.add_argument("-o", "--output", default="tree.svg")
    args = parser.parse_args()

    xml_text = Path(args.xml_file).read_text(encoding="utf-8")
    dot = xml_to_dot(xml_text)

    with tempfile.TemporaryDirectory() as tmp:
        dot_path = Path(tmp) / "tree.dot"
        out_path = Path(tmp) / args.output

        dot_path.write_text(dot, encoding="utf-8")

        fmt = Path(args.output).suffix.lstrip(".").lower()
        if not fmt:
            raise ValueError("Output file must have an extension, e.g. .svg or .png")

        subprocess.run(
            ["dot", f"-T{fmt}", str(dot_path), "-o", str(out_path)],
            check=True,
        )

        Path(args.output).write_bytes(out_path.read_bytes())

    print(f"✅ Generated: {args.output}")


if __name__ == "__main__":
    main()
