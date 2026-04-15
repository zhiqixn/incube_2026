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
}

DECORATOR_NODES = {
    "Decorator",
    "Timeout",
    "RetryUntilSuccessful",
}


def clean_value(val: str) -> str:
    val = val.strip()
    if val.startswith("{") and val.endswith("}"):
        return f"[{val[1:-1]}]"
    return val


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
        "&amp;",
        text,
    )

    # 4. Check if the text already has a proper single root element
    try:
        tree = ET.fromstring(text)
        # If the top-level element is already <root>, return as-is.
        # Otherwise (e.g. a bare <BehaviorTree>), fall through to wrap it.
        if tree.tag == "root":
            return text
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


def xml_to_dot(xml_text: str) -> str:
    root = ET.fromstring(xml_text)

    main_tree_id = root.attrib.get("main_tree_to_execute")
    bt_map = {
        bt.attrib["ID"]: bt
        for bt in root.findall("BehaviorTree")
        if "ID" in bt.attrib
    }

    if not main_tree_id or main_tree_id not in bt_map:
        raise ValueError("Missing or invalid main_tree_to_execute")

    node_id_gen = count()

    lines = [
        "digraph BT {",
        '  graph [',
        '    rankdir=TB,',
        '    splines=false,',
        '    nodesep=0.95,',
        '    ranksep=1.15,',
        '    pad=0.35,',
        '    bgcolor="white"',
        '  ];',
        '  node [',
        '    shape=box,',
        '    style="rounded,filled",',
        '    fontname="Helvetica",',
        '    fontsize=11,',
        '    color="black"',
        '  ];',
        '  edge [',
        '    color="black",',
        '    penwidth=1.1',
        '  ];',
    ]

    def esc(text: str) -> str:
        return (
            text
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\\\\n", "\\n")
        )

    def short_tag(tag: str) -> str:
        return tag.split("_", 1)[1] if "_" in tag else tag

    def is_condition_node(elem) -> bool:
        if elem.attrib.get("node_type") == "condition":
            return True

        tag = elem.tag.lower()
        return (
            tag.startswith("condition_")
            or tag.startswith("is_")
            or tag.startswith("check_")
            or tag.startswith("has_")
            or tag.startswith("can_")
            or tag.startswith("should_")
        )

    def collect_relevant_attrs(elem) -> list[str]:
        attrs = []

        for key in (
            "agent_id",
            "agent_ids",
            "vehicle_id",
            "vehicle_ids",
            "asset_id",
            "asset_ids",
        ):
            if key in elem.attrib:
                attrs.append(clean_value(elem.attrib[key]))

        for key in (
            "target_id",
            "target_ids",
            "task",
            "goal",
            "area",
            "zone",
            "region",
            "waypoint",
            "waypoints",
            "source_vehicle",
            "target_vehicle",
            "platform",
            "platform_id",
        ):
            if key in elem.attrib:
                attrs.append(f"{key}={clean_value(elem.attrib[key])}")

        if "pose" in elem.attrib:
            attrs.append(f"pose={clean_value(elem.attrib['pose'])}")

        if "radius_m" in elem.attrib:
            attrs.append(f"r={clean_value(elem.attrib['radius_m'])}")

        if "altitude_m" in elem.attrib:
            attrs.append(f"alt={clean_value(elem.attrib['altitude_m'])}")

        if "speed_mps" in elem.attrib:
            attrs.append(f"v={clean_value(elem.attrib['speed_mps'])}")

        if "timeout_s" in elem.attrib:
            attrs.append(f"timeout={clean_value(elem.attrib['timeout_s'])}s")

        if "msec" in elem.attrib:
            attrs.append(f"{clean_value(elem.attrib['msec'])} ms")

        if "num_attempts" in elem.attrib:
            attrs.append(f"{clean_value(elem.attrib['num_attempts'])}x")

        return attrs

    def label(elem) -> str:
        tag = elem.tag
        name = elem.attrib.get("name")

        if tag in CONTROL_NODES:
            parts = ["[CONTROL]"]
            if name:
                parts.append(name)
                parts.append(f"({tag})")
            else:
                parts.append(tag)

            if tag == "Parallel":
                sc = elem.attrib.get("success_count")
                fc = elem.attrib.get("failure_count")
                if sc is not None:
                    parts.append(f"success={clean_value(sc)}")
                if fc is not None:
                    parts.append(f"fail={clean_value(fc)}")

            return "\n".join(parts)

        if tag in DECORATOR_NODES:
            parts = [f"[DECORATOR]\n{tag}"]
            if name:
                parts.append(f"name={clean_value(name)}")

            if tag == "Timeout":
                parts.append(f"msec={clean_value(elem.attrib.get('msec', '?'))}")
            elif tag == "RetryUntilSuccessful":
                parts.append(
                    f"num_attempts={clean_value(elem.attrib.get('num_attempts', '?'))}"
                )

            return "\n".join(parts)

        if tag == "SubTree":
            parts = [f"[SUBTREE]\n{clean_value(elem.attrib.get('ID', 'UNKNOWN'))}"]
            if name:
                parts.append(f"name={clean_value(name)}")
            return "\n".join(parts)

        if is_condition_node(elem):
            parts = [f"[COND]\n{short_tag(tag)}"]
            if name:
                parts.append(f"name={clean_value(name)}")
            parts.extend(collect_relevant_attrs(elem))
            return "\n".join(parts)

        parts = [f"[ACT]\n{short_tag(tag)}"]
        if name:
            parts.append(f"name={clean_value(name)}")
        parts.extend(collect_relevant_attrs(elem))
        return "\n".join(parts)

    def node_style(elem) -> dict[str, str]:
        tag = elem.tag

        if tag in {"Sequence", "ReactiveSequence"}:
            return {"fill": "#C8E6C9", "shape": "box", "penwidth": "1.8"}

        if tag in {"Fallback", "ReactiveFallback"}:
            return {"fill": "#FFCDD2", "shape": "box", "penwidth": "1.8"}

        if tag == "Parallel":
            return {"fill": "#E1BEE7", "shape": "box", "penwidth": "2.0"}

        if tag in DECORATOR_NODES:
            return {"fill": "#FFF9C4", "shape": "diamond", "penwidth": "1.5"}

        if tag == "SubTree":
            return {"fill": "#FFE082", "shape": "folder", "penwidth": "1.5"}

        if is_condition_node(elem):
            return {"fill": "#64B5F6", "shape": "ellipse", "penwidth": "1.6"}

        return {"fill": "#90CAF9", "shape": "box", "penwidth": "1.2"}

    def add_node(node_id: str, label_text: str, style: dict[str, str]) -> None:
        lines.append(
            f'  {node_id} [label="{esc(label_text)}", '
            f'fillcolor="{style["fill"]}", '
            f'shape="{style["shape"]}", '
            f'penwidth={style["penwidth"]}];'
        )

    def visit(elem, parent=None, stack=None):
        if stack is None:
            stack = set()

        my_id = f"n{next(node_id_gen)}"
        add_node(my_id, label(elem), node_style(elem))

        if parent is not None:
            lines.append(f"  {parent} -> {my_id};")

        if elem.tag == "SubTree":
            subtree_id = elem.attrib.get("ID")
            if not subtree_id:
                return my_id

            if subtree_id in stack:
                loop_id = f"n{next(node_id_gen)}"
                add_node(
                    loop_id,
                    f"RecursiveRef\n{clean_value(subtree_id)}",
                    {"fill": "#F8BBD0", "shape": "box", "penwidth": "1.2"},
                )
                lines.append(f"  {my_id} -> {loop_id};")
                return my_id

            subtree = bt_map.get(subtree_id)
            if subtree is None:
                missing_id = f"n{next(node_id_gen)}"
                add_node(
                    missing_id,
                    f"MissingTree\n{clean_value(subtree_id)}",
                    {"fill": "#EF9A9A", "shape": "box", "penwidth": "1.2"},
                )
                lines.append(f"  {my_id} -> {missing_id};")
                return my_id

            new_stack = set(stack)
            new_stack.add(subtree_id)

            child_ids = []
            for child in subtree:
                cid = visit(child, my_id, new_stack)
                child_ids.append(cid)

            if len(child_ids) > 1:
                lines.append("  { rank=same; " + "; ".join(child_ids) + "; }")

            return my_id

        child_ids = []
        for child in elem:
            cid = visit(child, my_id, stack)
            child_ids.append(cid)

        if len(child_ids) > 1:
            lines.append("  { rank=same; " + "; ".join(child_ids) + "; }")

        return my_id

    main_bt = bt_map[main_tree_id]
    root_id = f"n{next(node_id_gen)}"
    add_node(
        root_id,
        f"[ROOT]\n{clean_value(main_tree_id)}",
        {"fill": "#FFD54F", "shape": "box", "penwidth": "2.0"},
    )

    top_children = []
    for child in main_bt:
        cid = visit(child, root_id, {main_tree_id})
        top_children.append(cid)

    if len(top_children) > 1:
        lines.append("  { rank=same; " + "; ".join(top_children) + "; }")

    if len(top_children) == 2:
        lines.append(
            f"  {top_children[0]} -> {top_children[1]} "
            f'[style=invis, minlen=4];'
        )

    lines += [
        "",
        "  subgraph cluster_legend {",
        '    label="Legend";',
        '    fontname="Helvetica";',
        '    fontsize=12;',
        '    color="gray40";',
        '    style="rounded,dashed";',
        '    margin=16;',
        "",
        '    key_root [label="[ROOT]\\nMain tree", fillcolor="#FFD54F", shape="box", style="rounded,filled"];',
        '    key_seq [label="[CONTROL]\\nSequence / ReactiveSequence\\nname=<unique_name>", fillcolor="#C8E6C9", shape="box", style="rounded,filled"];',
        '    key_fb [label="[CONTROL]\\nFallback / ReactiveFallback\\nname=<unique_name>", fillcolor="#FFCDD2", shape="box", style="rounded,filled"];',
        '    key_par [label="[CONTROL]\\nParallel\\nname=<unique_name>", fillcolor="#E1BEE7", shape="box", style="rounded,filled"];',
        '    key_dec [label="[DECORATOR]\\nTimeout / Retry / Decorator", fillcolor="#FFF9C4", shape="diamond", style="filled"];',
        '    key_sub [label="[SUBTREE]\\nReferenced subtree", fillcolor="#FFE082", shape="folder", style="filled"];',
        '    key_act [label="[ACT]\\nAction node\\nrefs in [...]", fillcolor="#90CAF9", shape="box", style="rounded,filled"];',
        '    key_cond [label="[COND]\\nCondition node\\nrefs in [...]", fillcolor="#64B5F6", shape="ellipse", style="filled"];',
        "",
        "  }",
    ]

    lines.append("}")
    return "\n".join(lines)


def _scale_svg(svg_path: Path, scale: float) -> bytes:
    """Scale an SVG's width/height attributes and return the modified bytes."""
    tree = ET.parse(svg_path)
    svg_root = tree.getroot()

    def _scale_len(val: str) -> str:
        m = re.match(r"([0-9.]+)([a-zA-Z%]*)", val)
        if not m:
            return val
        return f"{float(m.group(1)) * scale}{m.group(2)}"

    if "width" in svg_root.attrib:
        svg_root.attrib["width"] = _scale_len(svg_root.attrib["width"])
    if "height" in svg_root.attrib:
        svg_root.attrib["height"] = _scale_len(svg_root.attrib["height"])

    out = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
    try:
        tree.write(out.name)
        return Path(out.name).read_bytes()
    finally:
        Path(out.name).unlink(missing_ok=True)


def render_xml_to_image(
    xml_text: str,
    output_path: str | Path = "data/bt_output.svg",
    fmt: str = "svg",
    svg_scale: float = 0.25,
) -> Path:
    """Convert an XML behaviour-tree string to an image file.

    Parameters
    ----------
    xml_text : str
        The raw XML describing the behaviour tree.
    output_path : str | Path
        Destination file path (including extension).  Defaults to
        ``data/bt_output.svg``.
    fmt : str
        Image format passed to Graphviz (``png``, ``svg``, ``pdf``, ...).
    svg_scale : float
        When *fmt* is ``svg``, scale the output dimensions by this factor
        to reduce the rendered size.  Ignored for non-SVG formats.

    Returns
    -------
    Path
        The path the image was written to.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dot = xml_to_dot(_preprocess_xml(xml_text))

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

        if fmt == "svg" and svg_scale != 1.0:
            output_path.write_bytes(_scale_svg(tmp_out, svg_scale))
        else:
            output_path.write_bytes(tmp_out.read_bytes())

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_file")
    parser.add_argument("-o", "--output", default="tree.svg")
    parser.add_argument(
        "--scale", type=float, default=0.25,
        help="SVG scale factor (default: 0.25, ignored for non-SVG output)",
    )
    args = parser.parse_args()

    xml_text = Path(args.xml_file).read_text(encoding="utf-8")
    fmt = Path(args.output).suffix.lstrip(".")

    out = render_xml_to_image(
        xml_text,
        output_path=args.output,
        fmt=fmt,
        svg_scale=args.scale,
    )

    print(f"Generated: {out}")


if __name__ == "__main__":
    main()
