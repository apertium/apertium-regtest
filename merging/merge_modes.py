from pathlib import Path

def generate_modes_file(eng_deu_dir, spa_cat_dir, unified_models_dir):
    """
    Combines the modes.xml files of the two systems into one.

    Args:
        eng_deu_dir (str): Path to the eng-deu directory.
        spa_cat_dir (str): Path to the spa-cat directory.
        unified_models_dir (str): Path to the unified models directory.
    """
    from xml.etree.ElementTree import ParseError

    eng_deu_modes = Path(eng_deu_dir) / "modes.xml"
    spa_cat_modes = Path(spa_cat_dir) / "modes.xml"
    output_modes = Path(unified_models_dir) / "modes.xml"

    if not eng_deu_modes.exists() or not spa_cat_modes.exists():
        print("Error: modes.xml not found in one or both systems!")
        return

    try:
        import xml.etree.ElementTree as ET

        eng_deu_tree = ET.parse(eng_deu_modes)
        spa_cat_tree = ET.parse(spa_cat_modes)

        eng_deu_root = eng_deu_tree.getroot()
        spa_cat_root = spa_cat_tree.getroot()

        unified_root = ET.Element("modes")

        for child in eng_deu_root:
            unified_root.append(child)
        for child in spa_cat_root:
            unified_root.append(child)

        unified_tree = ET.ElementTree(unified_root)
        output_modes.parent.mkdir(parents=True, exist_ok=True)
        unified_tree.write(output_modes, encoding="utf-8", xml_declaration=True)

        print(f"Unified modes.xml generated at: {output_modes}")
    except ParseError as e:
        print(f"Error parsing modes.xml: {e}")