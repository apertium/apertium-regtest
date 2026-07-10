import re

def extract_ac_init_and_am_init(file_content):
    """
    Extracts AC_INIT and AM_INIT_AUTOMAKE from a file content.
    
    Args:
        file_content (list of str): The content of the configure.ac file.
        
    Returns:
        tuple: Extracted AC_INIT and AM_INIT_AUTOMAKE lines, or None if not found.
    """
    ac_init_line = None
    am_init_automake_line = None
    
    for line in file_content:
        if line.startswith('AC_INIT'):
            ac_init_line = line.strip()
        elif line.startswith('AM_INIT_AUTOMAKE'):
            am_init_automake_line = line.strip()
    
    return ac_init_line, am_init_automake_line

def extract_lang_version_pairs(script_path):
    """
    Extract lang_version_pairs from the script itself.

    Args:
        script_path (str): Path to the configure.ac script.

    Returns:
        list of tuples: Extracted (lang, version) pairs.
    """
    lang_version_pairs = []
    with open(script_path, "r") as script_file:
        script_content = script_file.read()

    pattern = r'\("([^"]+)",\s*"?([^"]*)"?\)'  # Regex pattern to find language-version pairs
    matches = re.findall(pattern, script_content)
    for lang, version in matches:
        lang_version_pairs.append((lang, version if version else None))

    return lang_version_pairs

def generate_ap_check_ling(lang_version_pairs):
    """
    Generate AP_CHECK_LING lines dynamically based on extracted language-version pairs.
    
    Args:
        lang_version_pairs (list of tuples): List of (lang, version) pairs.
    
    Returns:
        list of str: Generated AP_CHECK_LING lines.
    """
    result = []
    result.append("m4_ifdef([AP_CHECK_LING],[],[AC_MSG_ERROR([AP_CHECK_LING not defined, is apertium.m4 in ACLOCAL_PATH? See: https://wiki.apertium.org/wiki/Installation_troubleshooting])])\n\n")
    for i, (lang, version) in enumerate(lang_version_pairs, start=1):
        version_str = f", [{version}]" if version else ""
        result.append(f"AP_CHECK_LING([{i}], [{lang}]{version_str})\n")
    result.append("\n")
    return result


def merge_configure_ac(file1, file2, lang_version_pairs):
    """
    Merge two configure.ac files into one with dynamically generated AP_CHECK_LING lines.
    
    Args:
        file1 (str): Path to the first configure.ac file.
        file2 (str): Path to the second configure.ac file.
        lang_version_pairs (list of tuples): List of (lang, version) pairs for AP_CHECK_LING.
    
    Returns:
        str: Merged configure.ac content.
    """
    with open(file1, "r") as f1, open(file2, "r") as f2:
        content1 = f1.readlines()
        content2 = f2.readlines()
    
    # Extract AC_INIT and AM_INIT_AUTOMAKE from both files
    ac_init_line1, am_init_automake_line1 = extract_ac_init_and_am_init(content1)
    ac_init_line2, am_init_automake_line2 = extract_ac_init_and_am_init(content2)
    
    merged_content = []
    
    # Add AC_INIT lines from both files
    if ac_init_line1:
        merged_content.append(f"{ac_init_line1}\n")
    if ac_init_line2:
        merged_content.append(f"{ac_init_line2}\n")
    
    # Add AM_INIT_AUTOMAKE lines from both files
    if am_init_automake_line1:
        merged_content.append(f"{am_init_automake_line1}\n")
    if am_init_automake_line2:
        merged_content.append(f"{am_init_automake_line2}\n")
    
    # Add other common configuration lines
    merged_content.extend([
        "AC_PREREQ(2.52)\n\n",
        "AC_PROG_AWK\n\n",
        "PKG_CHECK_MODULES(APERTIUM, apertium >= 3.7.2)\n",
        "PKG_CHECK_MODULES(LTTOOLBOX, lttoolbox >= 3.5.4)\n",
        "PKG_CHECK_MODULES(CG3, cg3 >= 1.3.3)\n",
        "PKG_CHECK_MODULES(APERTIUM_LEX_TOOLS, apertium-lex-tools >= 0.4.0)\n",
        "PKG_CHECK_MODULES(APERTIUM_ANAPHORA, apertium-anaphora >= 1.1.0)\n\n",
    ])
    
    # Generate AP_CHECK_LING lines based on language-version pairs
    merged_content.extend(generate_ap_check_ling(lang_version_pairs))

    # Add additional checks
    merged_content.extend([
        "PKG_CHECK_MODULES(REGTEST, apertium-regtest >= 0.0.1, [],\n",
        "                  [AC_MSG_WARN([Running tests requires apertium-regtest])])\n\n",
    ])

    merged_content.append("AP_MKINCLUDE\n\n")
    merged_content.append("AC_OUTPUT([Makefile])\n")

    return "".join(merged_content)

